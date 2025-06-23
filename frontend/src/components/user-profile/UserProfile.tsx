import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import LogoutModal from '../logout-modal/LogoutModal';
import './UserProfile.scss';

const UserProfile: React.FC = () => {
  const { user, logout } = useAuth();
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  if (!user) return null;

  const handleLogoutConfirm = () => {
    logout();
  };

  const handleLogoutCancel = () => {
    setShowLogoutModal(false);
  };

  return (
    <>
      <div className="user-profile">
        <div className="user-info">
          <img 
            src={user.picture} 
            alt={user.name} 
            className="user-avatar"
            referrerPolicy="no-referrer"
          />
          <div className="user-details">
            <span className="user-name">{user.name}</span>
            <span className="user-email">{user.email}</span>
          </div>
        </div>
      </div>
      
      <LogoutModal
        isOpen={showLogoutModal}
        onClose={handleLogoutCancel}
        onConfirm={handleLogoutConfirm}
        userName={user.name}
      />
    </>
  );
};

export default UserProfile; 