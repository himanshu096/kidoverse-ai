import React, { useEffect } from 'react';
import './SuccessNotification.scss';

interface SuccessNotificationProps {
  message: string;
  isVisible: boolean;
  onClose: () => void;
  duration?: number;
}

const SuccessNotification: React.FC<SuccessNotificationProps> = ({ 
  message, 
  isVisible, 
  onClose, 
  duration = 3000 
}) => {
  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(() => {
        onClose();
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [isVisible, duration, onClose]);

  if (!isVisible) return null;

  return (
    <div className="success-notification">
      <div className="success-icon">✅</div>
      <span className="success-message">{message}</span>
    </div>
  );
};

export default SuccessNotification; 