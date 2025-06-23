import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import UserProfile from '../user-profile/UserProfile';
import LogoutModal from '../logout-modal/LogoutModal';
import './MainHeader.scss';

export default function MainHeader() {
  const { user, logout } = useAuth();
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  return (
    <>
      <div className="main-header">
        <div className="header-right">
          <UserProfile />
          <button
            onClick={() => setShowLogoutModal(true)}
            className="logout-button"
            title="Logout"
          >
            🚪 Logout
          </button>
        </div>
      </div>

      <LogoutModal
        isOpen={showLogoutModal}
        onClose={() => setShowLogoutModal(false)}
        onConfirm={logout}
        userName={user?.name || ''}
      />
    </>
  );
} 