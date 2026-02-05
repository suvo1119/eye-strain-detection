import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

function RegisterPage() {
  const [formData, setFormData] = useState({
    fullName: '',
    userId: '',
    password: '',
    confirmPassword: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [userIdStatus, setUserIdStatus] = useState({ checking: false, available: null });
  const { register, checkUsername } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    // Check username availability on change
    if (name === 'userId' && value.length >= 3) {
      checkUserIdAvailability(value);
    } else if (name === 'userId') {
      setUserIdStatus({ checking: false, available: null });
    }
  };

  const checkUserIdAvailability = async (userId) => {
    setUserIdStatus({ checking: true, available: null });
    try {
      const available = await checkUsername(userId);
      setUserIdStatus({ checking: false, available });
    } catch {
      setUserIdStatus({ checking: false, available: null });
    }
  };

  const validateForm = () => {
    if (!formData.fullName.trim()) {
      setError('Full name is required');
      return false;
    }
    if (formData.userId.length < 3 || formData.userId.length > 20) {
      setError('User ID must be 3-20 characters');
      return false;
    }
    if (!/^[a-zA-Z0-9_]+$/.test(formData.userId)) {
      setError('User ID can only contain letters, numbers, and underscores');
      return false;
    }
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters');
      return false;
    }
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!validateForm()) return;

    setLoading(true);
    try {
      await register({
        full_name: formData.fullName,
        user_id: formData.userId,
        password: formData.password,
        confirm_password: formData.confirmPassword
      });
      navigate('/');
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <i className="fas fa-eye auth-icon"></i>
          <h1>Create Account</h1>
          <p>Join Eye Strain Monitor</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && (
            <div className="auth-error">
              <i className="fas fa-exclamation-circle"></i>
              {error}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="fullName">
              <i className="fas fa-user"></i> Full Name
            </label>
            <input
              type="text"
              id="fullName"
              name="fullName"
              value={formData.fullName}
              onChange={handleChange}
              placeholder="Enter your full name"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="userId">
              <i className="fas fa-id-badge"></i> User ID
            </label>
            <div className="input-with-status">
              <input
                type="text"
                id="userId"
                name="userId"
                value={formData.userId}
                onChange={handleChange}
                placeholder="Choose a unique user ID"
                required
                autoComplete="username"
              />
              {userIdStatus.checking && (
                <span className="status-icon checking">
                  <i className="fas fa-spinner fa-spin"></i>
                </span>
              )}
              {!userIdStatus.checking && userIdStatus.available === true && (
                <span className="status-icon available">
                  <i className="fas fa-check-circle"></i>
                </span>
              )}
              {!userIdStatus.checking && userIdStatus.available === false && (
                <span className="status-icon taken">
                  <i className="fas fa-times-circle"></i>
                </span>
              )}
            </div>
            <small className="form-hint">3-20 characters, letters, numbers, underscores only</small>
          </div>

          <div className="form-group">
            <label htmlFor="password">
              <i className="fas fa-lock"></i> Password
            </label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Create a strong password"
              required
              autoComplete="new-password"
            />
            <small className="form-hint">At least 8 characters</small>
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">
              <i className="fas fa-lock"></i> Confirm Password
            </label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="Confirm your password"
              required
              autoComplete="new-password"
            />
          </div>

          <button 
            type="submit" 
            className="auth-btn"
            disabled={loading || userIdStatus.available === false}
          >
            {loading ? (
              <>
                <i className="fas fa-spinner fa-spin"></i> Creating Account...
              </>
            ) : (
              <>
                <i className="fas fa-user-plus"></i> Create Account
              </>
            )}
          </button>
        </form>

        <div className="auth-footer">
          <p>Already have an account?</p>
          <Link to="/login" className="auth-link">
            <i className="fas fa-sign-in-alt"></i> Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}

export default RegisterPage;
