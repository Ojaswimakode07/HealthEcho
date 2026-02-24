import { useState } from "react";
import AuthModal from "./AuthModal";

export default function MedicalLanding({ onStartChat, onLogin, user, onLogout }) {
  const [showAuth, setShowAuth] = useState(false);

  return (
    <div className="medical-landing">
      <div className="landing-background"></div>
      <div className="landing-overlay"></div>
      
      {/* Floating medical icons */}
      <div className="floating-icon icon-1">⚕️</div>
      <div className="floating-icon icon-2">💊</div>
      <div className="floating-icon icon-3">🏥</div>
      <div className="floating-icon icon-4">❤️</div>

      {/* User info if logged in */}
      {user && (
        <div className="landing-user-info">
          <div className="user-info">
            {user.photoURL ? (
              <img 
                src={user.photoURL} 
                alt={user.name} 
                className="user-avatar"
              />
            ) : (
              <div className="user-avatar-placeholder">
                {user.name?.charAt(0) || 'U'}
              </div>
            )}
            <span className="user-name">Hi, {user.name?.split(' ')[0]}</span>
          </div>
          <button className="logout-btn" onClick={onLogout}>
            Logout
          </button>
        </div>
      )}

      {/* Main content */}
      <div className="landing-content">
        <h1 className="landing-title">HealthEcho</h1>
        <p className="landing-subtitle">Your AI Medical Assistant</p>

        <div className="landing-buttons">
          <button 
            className="landing-button button-start"
            onClick={onStartChat}
          >
            START
          </button>

          {!user ? (
            <button 
              className="landing-button button-auth"
              onClick={() => setShowAuth(true)}
            >
              LOGIN / SIGNUP
            </button>
          ) : (
            <button 
              className="landing-button button-auth"
              onClick={onStartChat}
            >
              CONTINUE AS {user.name?.split(' ')[0].toUpperCase()}
            </button>
          )}
        </div>

        <div className="scroll-indicator">
          <span>▼</span>
          <small>Scroll for more</small>
        </div>
      </div>

      {/* Auth Modal */}
      {showAuth && (
        <AuthModal 
          onClose={() => setShowAuth(false)}
          onLogin={onLogin}
        />
      )}
    </div>
  );
}