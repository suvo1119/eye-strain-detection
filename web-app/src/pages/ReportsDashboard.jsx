import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

// Use relative URL in production (same origin), localhost in development
const API_URL = import.meta.env.PROD ? '' : 'http://localhost:5000';

function ReportsDashboard() {
    const { token, user } = useAuth();
    const [dashboardData, setDashboardData] = useState(null);
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [selectedDate, setSelectedDate] = useState('');

    useEffect(() => {
        if (token) {
            fetchDashboardData();
            fetchSessions();
        }
    }, [token]);

    useEffect(() => {
        if (token) {
            fetchSessions(1, selectedDate);
        }
    }, [selectedDate]);

    const fetchDashboardData = async () => {
        if (!token) return;
        try {
            const response = await fetch(`${API_URL}/api/reports/dashboard`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                setDashboardData(data);
            }
        } catch (err) {
            console.error('Failed to fetch dashboard:', err);
        }
    };

    const fetchSessions = async (page = 1, date = '') => {
        if (!token) return;
        try {
            setLoading(true);
            let url = `${API_URL}/api/reports/sessions?page=${page}&per_page=10`;
            if (date) {
                url += `&date=${date}`;
            }
            const response = await fetch(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                setSessions(data.sessions);
                setTotalPages(data.pages);
                setCurrentPage(data.current_page);
            }
        } catch (err) {
            setError('Failed to load sessions');
        } finally {
            setLoading(false);
        }
    };

    const formatDuration = (seconds) => {
        if (!seconds) return '0m';
        const mins = Math.floor(seconds / 60);
        const hrs = Math.floor(mins / 60);
        if (hrs > 0) {
            return `${hrs}h ${mins % 60}m`;
        }
        return `${mins}m`;
    };

    const getStrainColor = (level) => {
        switch (level) {
            case 'Low': return '#00FF00';
            case 'Mild': return '#FFFF00';
            case 'High': return '#FF0000';
            default: return '#00A5FF';
        }
    };

    if (loading && !dashboardData) {
        return (
            <div className="reports-container">
                <div className="loading-spinner"></div>
                <p>Loading your reports...</p>
            </div>
        );
    }

    return (
        <div className="reports-container">
            <header className="reports-header">
                <Link to="/" className="nav-link">
                    <i className="fas fa-arrow-left"></i> Back to Monitoring
                </Link>
                <h1><i className="fas fa-chart-line"></i> {user?.full_name}'s Eye Health Dashboard</h1>
                <p>Track your eye strain patterns over time</p>
            </header>

            {dashboardData && (
                <>
                    {/* Stats Cards */}
                    <section className="stats-grid">
                        <div className="stat-card">
                            <div className="stat-icon"><i className="fas fa-calendar-week"></i></div>
                            <div className="stat-content">
                                <span className="stat-value">{dashboardData.weekly.total_sessions}</span>
                                <span className="stat-label">Sessions This Week</span>
                            </div>
                        </div>

                        <div className="stat-card">
                            <div className="stat-icon"><i className="fas fa-clock"></i></div>
                            <div className="stat-content">
                                <span className="stat-value">{formatDuration(dashboardData.weekly.total_time_seconds)}</span>
                                <span className="stat-label">Total Screen Time</span>
                            </div>
                        </div>

                        <div className="stat-card">
                            <div className="stat-icon"><i className="fas fa-eye"></i></div>
                            <div className="stat-content">
                                <span className="stat-value">{dashboardData.weekly.avg_blinks_per_min}</span>
                                <span className="stat-label">Avg Blinks/Min</span>
                            </div>
                        </div>

                        <div className="stat-card">
                            <div className="stat-icon"><i className="fas fa-percentage"></i></div>
                            <div className="stat-content">
                                <span className="stat-value">{dashboardData.weekly.avg_perclos}%</span>
                                <span className="stat-label">Avg PERCLOS</span>
                            </div>
                        </div>
                    </section>

                    {/* Strain Distribution */}
                    <section className="strain-distribution">
                        <h2><i className="fas fa-chart-pie"></i> Weekly Strain Distribution</h2>
                        <div className="strain-bars">
                            <div className="strain-bar">
                                <div className="bar-label">
                                    <span className="strain-dot" style={{ backgroundColor: '#00FF00' }}></span>
                                    Low
                                </div>
                                <div className="bar-track">
                                    <div
                                        className="bar-fill low"
                                        style={{
                                            width: `${(dashboardData.weekly.strain_distribution.Low / Math.max(dashboardData.weekly.total_sessions, 1)) * 100}%`
                                        }}
                                    ></div>
                                </div>
                                <span className="bar-value">{dashboardData.weekly.strain_distribution.Low}</span>
                            </div>

                            <div className="strain-bar">
                                <div className="bar-label">
                                    <span className="strain-dot" style={{ backgroundColor: '#FFFF00' }}></span>
                                    Mild
                                </div>
                                <div className="bar-track">
                                    <div
                                        className="bar-fill mild"
                                        style={{
                                            width: `${(dashboardData.weekly.strain_distribution.Mild / Math.max(dashboardData.weekly.total_sessions, 1)) * 100}%`
                                        }}
                                    ></div>
                                </div>
                                <span className="bar-value">{dashboardData.weekly.strain_distribution.Mild}</span>
                            </div>

                            <div className="strain-bar">
                                <div className="bar-label">
                                    <span className="strain-dot" style={{ backgroundColor: '#FF0000' }}></span>
                                    High
                                </div>
                                <div className="bar-track">
                                    <div
                                        className="bar-fill high"
                                        style={{
                                            width: `${(dashboardData.weekly.strain_distribution.High / Math.max(dashboardData.weekly.total_sessions, 1)) * 100}%`
                                        }}
                                    ></div>
                                </div>
                                <span className="bar-value">{dashboardData.weekly.strain_distribution.High}</span>
                            </div>
                        </div>
                    </section>

                    {/* Daily Breakdown */}
                    <section className="daily-breakdown">
                        <h2><i className="fas fa-calendar-alt"></i> Daily Activity (Last 7 Days)</h2>
                        <div className="daily-grid">
                            {dashboardData.daily_data.map((day, index) => (
                                <div key={index} className="day-card">
                                    <div className="day-name">{day.day}</div>
                                    <div className="day-date">{day.date}</div>
                                    <div className="day-stats">
                                        <span><i className="fas fa-desktop"></i> {day.sessions} sessions</span>
                                        <span><i className="fas fa-clock"></i> {day.total_time_minutes}m</span>
                                        <span><i className="fas fa-eye"></i> {day.avg_blinks_per_min} bpm</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                </>
            )}

            {/* Recent Reports Table */}
            <section className="reports-table-section">
                <div className="section-header">
                    <h2><i className="fas fa-history"></i> Your Sessions</h2>
                    <div className="date-filter">
                        <label htmlFor="dateFilter">
                            <i className="fas fa-calendar"></i> Filter by date:
                        </label>
                        <input
                            type="date"
                            id="dateFilter"
                            value={selectedDate}
                            onChange={(e) => setSelectedDate(e.target.value)}
                            className="date-input"
                        />
                        {selectedDate && (
                            <button 
                                className="clear-filter-btn"
                                onClick={() => setSelectedDate('')}
                            >
                                <i className="fas fa-times"></i> Clear
                            </button>
                        )}
                    </div>
                </div>

                {error && <div className="error-message">{error}</div>}

                {sessions.length === 0 ? (
                    <div className="no-reports">
                        <i className="fas fa-file-alt"></i>
                        <p>{selectedDate ? 'No sessions found for this date.' : 'No sessions yet. Start monitoring to track your eye health!'}</p>
                    </div>
                ) : (
                    <>
                        <div className="sessions-list">
                            {sessions.map((session) => (
                                <div key={session.session_id} className="session-card">
                                    <div className="session-header">
                                        <div className="session-time">
                                            <i className="fas fa-clock"></i>
                                            <span>{new Date(session.start_time).toLocaleDateString()} </span>
                                            <span className="time-range">
                                                {new Date(session.start_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                                {' - '}
                                                {new Date(session.end_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                            </span>
                                        </div>
                                        <span
                                            className="strain-badge"
                                            style={{ backgroundColor: getStrainColor(session.dominant_strain) }}
                                        >
                                            {session.dominant_strain}
                                        </span>
                                    </div>
                                    <div className="session-metrics">
                                        <div className="session-metric">
                                            <i className="fas fa-stopwatch"></i>
                                            <span className="metric-value">{formatDuration(session.total_duration_seconds)}</span>
                                            <span className="metric-label">Duration</span>
                                        </div>
                                        <div className="session-metric">
                                            <i className="fas fa-eye"></i>
                                            <span className="metric-value">{session.avg_blinks_per_min}</span>
                                            <span className="metric-label">Blinks/Min</span>
                                        </div>
                                        <div className="session-metric">
                                            <i className="fas fa-percentage"></i>
                                            <span className="metric-value">{session.avg_perclos}%</span>
                                            <span className="metric-label">PERCLOS</span>
                                        </div>
                                        <div className="session-metric">
                                            <i className="fas fa-hand-pointer"></i>
                                            <span className="metric-value">{session.total_blinks}</span>
                                            <span className="metric-label">Total Blinks</span>
                                        </div>
                                    </div>
                                    <div className="session-strain-bar">
                                        {session.strain_distribution.Low > 0 && (
                                            <div 
                                                className="strain-segment low"
                                                style={{width: `${(session.strain_distribution.Low / session.data_points) * 100}%`}}
                                                title={`Low: ${session.strain_distribution.Low}`}
                                            ></div>
                                        )}
                                        {session.strain_distribution.Mild > 0 && (
                                            <div 
                                                className="strain-segment mild"
                                                style={{width: `${(session.strain_distribution.Mild / session.data_points) * 100}%`}}
                                                title={`Mild: ${session.strain_distribution.Mild}`}
                                            ></div>
                                        )}
                                        {session.strain_distribution.High > 0 && (
                                            <div 
                                                className="strain-segment high"
                                                style={{width: `${(session.strain_distribution.High / session.data_points) * 100}%`}}
                                                title={`High: ${session.strain_distribution.High}`}
                                            ></div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="pagination">
                                <button
                                    onClick={() => fetchSessions(currentPage - 1, selectedDate)}
                                    disabled={currentPage === 1}
                                >
                                    <i className="fas fa-chevron-left"></i> Previous
                                </button>
                                <span>Page {currentPage} of {totalPages}</span>
                                <button
                                    onClick={() => fetchSessions(currentPage + 1, selectedDate)}
                                    disabled={currentPage === totalPages}
                                >
                                    Next <i className="fas fa-chevron-right"></i>
                                </button>
                            </div>
                        )}
                    </>
                )}
            </section>
        </div>
    );
}

export default ReportsDashboard;
