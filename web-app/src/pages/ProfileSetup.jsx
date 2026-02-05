import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

function ProfileSetup() {
  const { user, updateProfile } = useAuth();
  const navigate = useNavigate();
  
  const [formData, setFormData] = useState({
    age: '',
    gender: '',
    uses_glasses: null,
    glasses_power_left: '',
    glasses_power_right: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleGlassesChange = (usesGlasses) => {
    setFormData(prev => ({
      ...prev,
      uses_glasses: usesGlasses,
      glasses_power_left: usesGlasses ? prev.glasses_power_left : '',
      glasses_power_right: usesGlasses ? prev.glasses_power_right : ''
    }));
  };

  const nextStep = () => {
    if (step === 1 && !formData.age) {
      setError('Please enter your age');
      return;
    }
    if (step === 2 && !formData.gender) {
      setError('Please select your gender');
      return;
    }
    if (step === 3 && formData.uses_glasses === null) {
      setError('Please select if you wear glasses');
      return;
    }
    setError('');
    setStep(prev => prev + 1);
  };

  const prevStep = () => {
    setError('');
    setStep(prev => prev - 1);
  };

  const handleSubmit = async () => {
    if (formData.uses_glasses && !formData.glasses_power_left && !formData.glasses_power_right) {
      setError('Please enter at least one eye power');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await updateProfile(formData);
      navigate('/');
    } catch (err) {
      setError(err.message || 'Failed to save profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card profile-setup-card">
        <div className="auth-header">
          <i className="fas fa-user-circle auth-icon"></i>
          <h1>Welcome, {user?.full_name}!</h1>
          <p>Let's set up your profile for better eye health tracking</p>
        </div>

        <div className="progress-bar">
          <div className="progress-track">
            <div 
              className="progress-fill" 
              style={{ width: `${(step / 4) * 100}%` }}
            ></div>
          </div>
          <span className="progress-text">Step {step} of 4</span>
        </div>

        {error && (
          <div className="auth-error">
            <i className="fas fa-exclamation-circle"></i>
            {error}
          </div>
        )}

        <div className="profile-form">
          {/* Step 1: Age */}
          {step === 1 && (
            <div className="form-step">
              <h2><i className="fas fa-birthday-cake"></i> How old are you?</h2>
              <p className="step-description">Age affects eye strain patterns and recommendations</p>
              <div className="age-input-container">
                <input
                  type="number"
                  name="age"
                  value={formData.age}
                  onChange={handleChange}
                  placeholder="Enter your age"
                  min="5"
                  max="120"
                  className="age-input"
                />
                <span className="age-unit">years</span>
              </div>
            </div>
          )}

          {/* Step 2: Gender */}
          {step === 2 && (
            <div className="form-step">
              <h2><i className="fas fa-venus-mars"></i> What's your gender?</h2>
              <p className="step-description">This helps personalize your eye health insights</p>
              <div className="gender-options">
                <button
                  type="button"
                  className={`gender-option ${formData.gender === 'male' ? 'selected' : ''}`}
                  onClick={() => setFormData(prev => ({ ...prev, gender: 'male' }))}
                >
                  <i className="fas fa-mars"></i>
                  <span>Male</span>
                </button>
                <button
                  type="button"
                  className={`gender-option ${formData.gender === 'female' ? 'selected' : ''}`}
                  onClick={() => setFormData(prev => ({ ...prev, gender: 'female' }))}
                >
                  <i className="fas fa-venus"></i>
                  <span>Female</span>
                </button>
                <button
                  type="button"
                  className={`gender-option ${formData.gender === 'other' ? 'selected' : ''}`}
                  onClick={() => setFormData(prev => ({ ...prev, gender: 'other' }))}
                >
                  <i className="fas fa-genderless"></i>
                  <span>Other</span>
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Glasses */}
          {step === 3 && (
            <div className="form-step">
              <h2><i className="fas fa-glasses"></i> Do you wear glasses?</h2>
              <p className="step-description">Vision correction affects blink patterns</p>
              <div className="glasses-options">
                <button
                  type="button"
                  className={`glasses-option ${formData.uses_glasses === true ? 'selected' : ''}`}
                  onClick={() => handleGlassesChange(true)}
                >
                  <i className="fas fa-check-circle"></i>
                  <span>Yes, I wear glasses</span>
                </button>
                <button
                  type="button"
                  className={`glasses-option ${formData.uses_glasses === false ? 'selected' : ''}`}
                  onClick={() => handleGlassesChange(false)}
                >
                  <i className="fas fa-times-circle"></i>
                  <span>No, I don't</span>
                </button>
              </div>
            </div>
          )}

          {/* Step 4: Glasses Power (if applicable) or Summary */}
          {step === 4 && (
            <div className="form-step">
              {formData.uses_glasses ? (
                <>
                  <h2><i className="fas fa-eye"></i> What's your glasses power?</h2>
                  <p className="step-description">Enter your prescription (e.g., -2.5, +1.0)</p>
                  <div className="power-inputs">
                    <div className="power-input-group">
                      <label>Left Eye (OS)</label>
                      <input
                        type="text"
                        name="glasses_power_left"
                        value={formData.glasses_power_left}
                        onChange={handleChange}
                        placeholder="e.g., -2.5"
                      />
                    </div>
                    <div className="power-input-group">
                      <label>Right Eye (OD)</label>
                      <input
                        type="text"
                        name="glasses_power_right"
                        value={formData.glasses_power_right}
                        onChange={handleChange}
                        placeholder="e.g., -2.0"
                      />
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <h2><i className="fas fa-check-double"></i> All set!</h2>
                  <p className="step-description">Here's your profile summary</p>
                  <div className="profile-summary">
                    <div className="summary-item">
                      <i className="fas fa-birthday-cake"></i>
                      <span>Age: {formData.age} years</span>
                    </div>
                    <div className="summary-item">
                      <i className="fas fa-venus-mars"></i>
                      <span>Gender: {formData.gender.charAt(0).toUpperCase() + formData.gender.slice(1)}</span>
                    </div>
                    <div className="summary-item">
                      <i className="fas fa-glasses"></i>
                      <span>Glasses: No</span>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="form-navigation">
            {step > 1 && (
              <button type="button" className="nav-btn prev-btn" onClick={prevStep}>
                <i className="fas fa-arrow-left"></i> Back
              </button>
            )}
            
            {step < 4 ? (
              <button type="button" className="nav-btn next-btn" onClick={nextStep}>
                Next <i className="fas fa-arrow-right"></i>
              </button>
            ) : (
              <button 
                type="button" 
                className="nav-btn submit-btn" 
                onClick={handleSubmit}
                disabled={loading}
              >
                {loading ? (
                  <><i className="fas fa-spinner fa-spin"></i> Saving...</>
                ) : (
                  <><i className="fas fa-check"></i> Complete Setup</>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProfileSetup;
