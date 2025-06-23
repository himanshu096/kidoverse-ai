import React from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../../contexts/AuthContext';
import './Login.scss';

const Login: React.FC = () => {
  const { login } = useAuth();

  const handleLoginSuccess = (credentialResponse: any) => {
    console.log("Login success:", credentialResponse);
    login(credentialResponse);
  };

  const handleLoginError = (error: any) => {
    console.error("Login failed:", error);
    alert(`Login failed: ${error.error || 'Unknown error'}`);
  };

  return (
    <div className="login-container">
      {/* Animated background elements */}
      <div className="background-shapes">
        <div className="shape shape-1"></div>
        <div className="shape shape-2"></div>
        <div className="shape shape-3"></div>
        <div className="shape shape-4"></div>
        <div className="shape shape-5"></div>
        <div className="shape shape-6"></div>
        <div className="shape shape-7"></div>
        <div className="shape shape-8"></div>
        <div className="shape shape-9"></div>
        <div className="shape shape-10"></div>
      </div>

      <div className="login-card">
        <div className="login-header">
          <h1>Welcome to Kido</h1>
          <p>Your AI Learning Companion</p>
        </div>
        
        <div className="login-content">
          <div className="login-description">
            <h2>Start Your Learning Journey</h2>
            <p>
              Sign in with your Google account to access personalized educational lessons, 
              interactive learning experiences, and track your progress.
            </p>
          </div>
          
          <div className="login-actions">
            <GoogleLogin
              onSuccess={handleLoginSuccess}
              onError={() => {
                console.error("Login failed");
                alert("Login failed. Please try again.");
              }}
              useOneTap
              theme="filled_blue"
              size="large"
              text="signin_with"
              shape="rectangular"
            />
          </div>
          
          <div className="login-features">
            <div className="feature">
              <span className="feature-icon">🎓</span>
              <span>Personalized Lessons</span>
            </div>
            <div className="feature">
              <span className="feature-icon">🤖</span>
              <span>AI-Powered Learning</span>
            </div>
            <div className="feature">
              <span className="feature-icon">📊</span>
              <span>Progress Tracking</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login; 