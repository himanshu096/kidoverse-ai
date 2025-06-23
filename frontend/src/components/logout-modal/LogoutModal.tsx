import React from 'react';
import './LogoutModal.scss';

interface LogoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  userName: string;
}

const LogoutModal: React.FC<LogoutModalProps> = ({ isOpen, onClose, onConfirm, userName }) => {
  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="logout-modal-overlay" onClick={handleBackdropClick}>
      <div className="logout-modal">
        <div className="logout-modal-header">
          <div className="logout-icon">👋</div>
          <h2>Goodbye!</h2>
        </div>
        
        <div className="logout-modal-content">
          <p>
            Are you sure you want to logout, <strong>{userName}</strong>?
          </p>
          <p className="logout-warning">
            Your current lesson progress will be saved, but you'll need to sign in again to continue.
          </p>
        </div>
        
        <div className="logout-modal-actions">
          <button 
            className="logout-modal-button cancel-button" 
            onClick={onClose}
          >
            Stay Here
          </button>
          <button 
            className="logout-modal-button confirm-button" 
            onClick={handleConfirm}
          >
            Yes, Logout
          </button>
        </div>
      </div>
    </div>
  );
};

export default LogoutModal; 