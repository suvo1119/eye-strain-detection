import React, { useEffect, useState, useRef } from 'react';
import { Routes, Route, Link, Navigate } from 'react-router-dom';
import io from 'socket.io-client';
import { useAuth } from './contexts/AuthContext';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProfileSetup from './pages/ProfileSetup';

// Use relative URL in production (same origin), localhost in development
const SOCKET_SERVER = import.meta.env.PROD ? '' : 'http://localhost:5000';
const API_BASE = import.meta.env.PROD ? '' : 'http://localhost:5000';

// Protected Route wrapper - requires profile completion
function ProtectedRoute({ children }) {
  const { isAuthenticated, loading, profileCompleted } = useAuth();

  if (loading) {
    return (
      <div className="loading-container">
        <i className="fas fa-spinner fa-spin"></i>
        <p>Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Redirect to profile setup if not completed
  if (!profileCompleted) {
    return <Navigate to="/profile-setup" replace />;
  }

  return children;
}

// Profile Setup Route - requires auth but no profile
function ProfileRoute({ children }) {
  const { isAuthenticated, loading, profileCompleted } = useAuth();

  if (loading) {
    return (
      <div className="loading-container">
        <i className="fas fa-spinner fa-spin"></i>
        <p>Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // If profile is already completed, go to dashboard
  if (profileCompleted) {
    return <Navigate to="/" replace />;
  }

  return children;
}

// Public Route wrapper (redirects to home if already authenticated)
function PublicRoute({ children }) {
  const { isAuthenticated, loading, profileCompleted } = useAuth();

  if (loading) {
    return (
      <div className="loading-container">
        <i className="fas fa-spinner fa-spin"></i>
        <p>Loading...</p>
      </div>
    );
  }

  if (isAuthenticated) {
    // If profile not completed, go to profile setup
    if (!profileCompleted) {
      return <Navigate to="/profile-setup" replace />;
    }
    return <Navigate to="/" replace />;
  }

  return children;
}

function MonitoringDashboard() {
  const { user, logout, token } = useAuth();
  const [socket, setSocket] = useState(null);
  const [monitoring, setMonitoring] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const frameIntervalRef = useRef(null);
  const [metrics, setMetrics] = useState({
    blinks_per_min: 0,
    perclos: 0,
    avg_ear: 0,
    avg_blink_duration_ms: 0,
    blinks_in_window: 0,
    strain_level: 'Waiting',
    strain_color: '#00FF00',
    faces_detected: 0,
    image_quality: 'Initializing',
    total_blinks: 0,
  });

  useEffect(() => {
    // Connect to Socket.IO server
    const newSocket = io(SOCKET_SERVER);

    newSocket.on('connect', () => {
      console.log('Connected to server');
      setConnected(true);
      setError(null);
    });

    newSocket.on('metrics_update', (data) => {
      setMetrics(data);
    });

    newSocket.on('monitoring_started', () => {
      setMonitoring(true);
      setError(null);
    });

    newSocket.on('monitoring_stopped', () => {
      setMonitoring(false);
    });

    newSocket.on('error', (data) => {
      console.error('Server error:', data.message);
      setError(data.message);
      setMonitoring(false);
    });

    newSocket.on('disconnect', () => {
      console.log('Disconnected from server');
      setConnected(false);
      setMonitoring(false);
    });

    newSocket.on('connect_error', (error) => {
      console.error('Connection error:', error);
      setError('Cannot connect to server. Make sure Flask server is running.');
      setConnected(false);
    });

    setSocket(newSocket);

    return () => {
      newSocket.disconnect();
    };
  }, []);

  // Start browser camera and send frames to server
  const startMonitoring = async () => {
    if (!socket) return;
    
    try {
      // Request camera access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480, facingMode: 'user' } 
      });
      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      
      // Tell server we're starting
      socket.emit('start_monitoring', { 
        user_id: user?.id,
        token: token,
        browser_camera: true  // Flag that we're using browser camera
      });
      
      setMonitoring(true);
      setError(null);
      
      // Send frames to server every 100ms (10 FPS)
      frameIntervalRef.current = setInterval(() => {
        if (videoRef.current && canvasRef.current && socket) {
          const canvas = canvasRef.current;
          const video = videoRef.current;
          const ctx = canvas.getContext('2d');
          
          canvas.width = 640;
          canvas.height = 480;
          ctx.drawImage(video, 0, 0, 640, 480);
          
          // Convert to base64 and send
          const frameData = canvas.toDataURL('image/jpeg', 0.7);
          socket.emit('process_frame', { frame: frameData });
        }
      }, 100);
      
    } catch (err) {
      console.error('Camera access error:', err);
      setError('Cannot access camera. Please allow camera permissions.');
    }
  };

  const stopMonitoring = () => {
    // Stop frame sending
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
    
    // Stop camera stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    
    if (socket) {
      socket.emit('stop_monitoring');
    }
    
    setMonitoring(false);
  };
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const getStrainColor = () => {
    if (metrics.strain_level === 'Low') return '#00FF00';
    if (metrics.strain_level === 'Mild') return '#00FFFF';
    if (metrics.strain_level === 'High') return '#FF0000';
    return '#00A5FF';
  };

  const getStatusIcon = () => {
    if (metrics.strain_level === 'Low') return <i className="fas fa-check-circle"></i>;
    if (metrics.strain_level === 'Mild') return <i className="fas fa-exclamation-circle"></i>;
    if (metrics.strain_level === 'High') return <i className="fas fa-times-circle"></i>;
    return <i className="fas fa-circle-notch"></i>;
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-left">
          <h1><i className="fas fa-eye"></i> Eye Strain Monitor</h1>
          <p>Real-time eye strain detection using AI</p>
        </div>
        <div className="header-right">
          <span className="user-greeting">
            <i className="fas fa-user-circle"></i> {user?.full_name || 'User'}
          </span>
          <Link to="/reports" className="nav-link">
            <i className="fas fa-chart-line"></i> Reports
          </Link>
          <button onClick={logout} className="nav-link logout-btn">
            <i className="fas fa-sign-out-alt"></i> Logout
          </button>
        </div>
      </header>

      <div className="main-content">
        {/* Connection Status */}
        <div className={`connection-status ${connected ? 'connected' : 'disconnected'} ${monitoring ? 'mobile-hidden' : ''}`}>
          <span className={`status-dot ${connected ? 'active' : ''}`}></span>
          {connected ? <><i className="fas fa-check"></i> Connected to Server</> : <><i className="fas fa-times"></i> Disconnected from Server</>}
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            <i className="fas fa-exclamation-triangle"></i> {error}
          </div>
        )}

        {/* Control Panel */}
        <section className="control-panel">
          <button
            className={`btn btn-start ${monitoring ? 'active' : ''}`}
            onClick={startMonitoring}
            disabled={monitoring}
          >
            {monitoring ? <><i className="fas fa-check"></i> Monitoring Active</> : <><i className="fas fa-play"></i> Start Monitoring</>}
          </button>
          <button
            className={`btn btn-stop ${!monitoring ? 'disabled' : ''}`}
            onClick={stopMonitoring}
            disabled={!monitoring}
          >
            <i className="fas fa-stop"></i> Stop Monitoring
          </button>
        </section>

        {/* Main Content - Two Column Layout */}
        <div className="content-wrapper">
          {/* Left Section - Camera Feed */}
          <section className="camera-section">
            <div className="camera-container">
              {/* Hidden canvas for frame capture */}
              <canvas ref={canvasRef} style={{ display: 'none' }} />
              
              {monitoring ? (
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="camera-feed"
                  style={{ transform: 'scaleX(-1)' }}
                />
              ) : (
                <div className="camera-placeholder-box">
                  <div className="placeholder-content">
                    <i className="fas fa-camera"></i>
                    <p>Camera Feed</p>
                  </div>
                </div>
              )}
              <div className="camera-overlay">
                {!monitoring && (
                  <div className="camera-hint">
                    <i className="fas fa-play-circle"></i>
                    <span>Click Start Monitoring</span>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* Right Section - Metrics and Status */}
          <section className="metrics-section">
            {/* Main Status Display */}
            <div className="status-card">
              <div className="status-center">
                <div className="status-emoji" style={{ color: getStrainColor() }}>
                  {getStatusIcon()}
                </div>
                <div className="status-level" style={{ color: getStrainColor() }}>
                  {metrics.strain_level}
                </div>
                <div className="status-description">
                  {metrics.strain_level === 'Low' && 'Your eyes are doing great!'}
                  {metrics.strain_level === 'Mild' && 'Some eye strain detected. Take a break soon.'}
                  {metrics.strain_level === 'High' && 'High eye strain! Take a break now!'}
                  {metrics.strain_level === 'Waiting' && 'Initializing...'}
                  {metrics.strain_level === 'No Face' && 'Please position your face in front of camera'}
                  {metrics.strain_level === 'Multiple Faces' && 'Only one person allowed in frame'}
                </div>
              </div>
            </div>

            {/* Metrics Grid */}
            <section className="metrics-grid">
              <div className="metric-card">
                <div className="metric-icon"><i className="fas fa-eye"></i></div>
                <div className="metric-label">Blinks/Min</div>
                <div className="metric-value">{metrics.blinks_per_min.toFixed(1)}</div>
                <div className="metric-range">Healthy: 12-20</div>
              </div>

              <div className="metric-card">
                <div className="metric-icon"><i className="fas fa-stopwatch"></i></div>
                <div className="metric-label">Blink Duration</div>
                <div className="metric-value">{metrics.avg_blink_duration_ms.toFixed(0)} ms</div>
                <div className="metric-range">Normal: 100-200</div>
              </div>

              <div className="metric-card">
                <div className="metric-icon"><i className="fas fa-chart-bar"></i></div>
                <div className="metric-label">PERCLOS</div>
                <div className="metric-value">{metrics.perclos.toFixed(1)}%</div>
                <div className="metric-range">Closed time %</div>
              </div>

              <div className="metric-card">
                <div className="metric-icon"><i className="fas fa-search"></i></div>
                <div className="metric-label">Eye Aspect Ratio</div>
                <div className="metric-value">{metrics.avg_ear.toFixed(3)}</div>
                <div className="metric-range">Health indicator</div>
              </div>

              <div className="metric-card">
                <div className="metric-icon"><i className="fas fa-chart-line"></i></div>
                <div className="metric-label">Total Blinks</div>
                <div className="metric-value">{metrics.total_blinks || 0}</div>
                <div className="metric-range">Session count</div>
              </div>

              <div className="metric-card">
                <div className="metric-icon"><i className="fas fa-user"></i></div>
                <div className="metric-label">Faces Detected</div>
                <div className="metric-value">{metrics.faces_detected}</div>
                <div className="metric-range">Should be 1</div>
              </div>
            </section>

            {/* Quality Indicator */}
            <div className="quality-card">
              <div className="quality-label"><i className="fas fa-camera"></i> Image Quality</div>
              <div className="quality-value">{metrics.image_quality}</div>
              {metrics.image_quality !== 'Good' && (
                <div className="quality-warning">
                  <i className="fas fa-lightbulb"></i> Improve lighting for better results
                </div>
              )}
            </div>
          </section>
        </div>

        {/* Recommendations */}
        {metrics.strain_level === 'High' && (
          <section className="recommendations-card">
            <div className="rec-title"><i className="fas fa-triangle-exclamation"></i> Eye Strain Alert!</div>
            <ul className="rec-list">
              <li><i className="fas fa-eye"></i> Look away from screen (20-20-20 rule)</li>
              <li><i className="fas fa-bullseye"></i> Look at something 20 feet away</li>
              <li><i className="fas fa-clock"></i> For 20 seconds, every 20 minutes</li>
              <li><i className="fas fa-droplet"></i> Blink more to moisturize eyes</li>
              <li><i className="fas fa-sun"></i> Adjust screen brightness</li>
            </ul>
          </section>
        )}
      </div>

      <footer className="app-footer">
        <p>Connected to server at {SOCKET_SERVER}</p>
      </footer>
    </div>
  );
}

// Simple dummy replacement for ReportsDashboard if it relied heavily on auth
import ReportsDashboard from './pages/ReportsDashboard';

function App() {
  return (
    <Routes>
      <Route path="/login" element={
        <PublicRoute>
          <LoginPage />
        </PublicRoute>
      } />
      <Route path="/register" element={
        <PublicRoute>
          <RegisterPage />
        </PublicRoute>
      } />
      <Route path="/profile-setup" element={
        <ProfileRoute>
          <ProfileSetup />
        </ProfileRoute>
      } />
      <Route path="/" element={
        <ProtectedRoute>
          <MonitoringDashboard />
        </ProtectedRoute>
      } />
      <Route path="/reports" element={
        <ProtectedRoute>
          <ReportsDashboard />
        </ProtectedRoute>
      } />
    </Routes>
  );
}

export default App;
