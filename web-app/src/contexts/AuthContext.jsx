import React, { createContext, useContext, useState, useEffect } from 'react';

// Use relative URL in production (same origin), localhost in development
const API_BASE_URL = import.meta.env.PROD ? '' : 'http://localhost:5000';
const API_BASE = `${API_BASE_URL}/api/auth`;
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('access_token'));
  const [refreshToken, setRefreshToken] = useState(localStorage.getItem('refresh_token'));
  const [loading, setLoading] = useState(true);

  // Check if user is authenticated on mount
  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          const response = await fetch(`${API_BASE}/me`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          if (response.ok) {
            const data = await response.json();
            setUser(data.user);
          } else {
            // Token expired, try refresh
            await refreshAccessToken();
          }
        } catch (error) {
          console.error('Auth init error:', error);
          clearAuth();
        }
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const clearAuth = () => {
    setUser(null);
    setToken(null);
    setRefreshToken(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  };

  const saveAuth = (accessToken, refreshTkn, userData) => {
    setToken(accessToken);
    setRefreshToken(refreshTkn);
    setUser(userData);
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshTkn);
  };

  const refreshAccessToken = async () => {
    const storedRefresh = localStorage.getItem('refresh_token');
    if (!storedRefresh) {
      clearAuth();
      return false;
    }

    try {
      const response = await fetch(`${API_BASE}/refresh`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${storedRefresh}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setToken(data.access_token);
        localStorage.setItem('access_token', data.access_token);
        
        // Fetch user data with new token
        const userResponse = await fetch(`${API_BASE}/me`, {
          headers: {
            'Authorization': `Bearer ${data.access_token}`
          }
        });
        if (userResponse.ok) {
          const userData = await userResponse.json();
          setUser(userData.user);
        }
        return true;
      }
    } catch (error) {
      console.error('Token refresh error:', error);
    }
    clearAuth();
    return false;
  };

  const login = async (userId, password) => {
    const response = await fetch(`${API_BASE}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ user_id: userId, password })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Login failed');
    }

    saveAuth(data.access_token, data.refresh_token, data.user);
    return data.user;
  };

  const register = async (userData) => {
    const response = await fetch(`${API_BASE}/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(userData)
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Registration failed');
    }

    saveAuth(data.access_token, data.refresh_token, data.user);
    return data.user;
  };

  const logout = async () => {
    try {
      if (token) {
        await fetch(`${API_BASE}/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    }
    clearAuth();
  };

  const checkUsername = async (username) => {
    try {
      const response = await fetch(`${API_BASE}/check-username/${username}`);
      const data = await response.json();
      return data.available;
    } catch {
      return null;
    }
  };

  const updateProfile = async (profileData) => {
    const response = await fetch(`${API_BASE}/profile`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(profileData)
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to update profile');
    }

    setUser(data.user);
    return data.user;
  };

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!user && !!token,
    profileCompleted: user?.profile_completed || false,
    login,
    logout,
    register,
    checkUsername,
    updateProfile
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
