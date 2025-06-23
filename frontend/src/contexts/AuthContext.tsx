import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { GoogleOAuthProvider, GoogleLogin, CredentialResponse } from '@react-oauth/google';
import { jwtDecode } from 'jwt-decode';

interface User {
  id: string;
  email: string;
  name: string;
  picture: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (credentialResponse: CredentialResponse) => void;
  logout: () => void;
  loading: boolean;
  showSuccessMessage: (message: string) => void;
  successMessage: string | null;
  clearSuccessMessage: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    // Check for existing user in localStorage on app start
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (error) {
        console.error('Error parsing saved user:', error);
        localStorage.removeItem('user');
      }
    }
    setLoading(false);
  }, []);

  const login = (credentialResponse: CredentialResponse) => {
    if (credentialResponse.credential) {
      try {
        const decoded: any = jwtDecode(credentialResponse.credential);
        
        const userData: User = {
          id: decoded.sub, // Google's unique user ID
          email: decoded.email,
          name: decoded.name,
          picture: decoded.picture,
        };
        
        console.log("User data extracted:", userData);
        console.log("Google User ID:", userData.id);
        
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
        setSuccessMessage(`Welcome back, ${userData.name}!`);
      } catch (error) {
        console.error('Error decoding credential:', error);
      }
    }
  };

  const logout = () => {
    console.log("Logging out user:", user?.name);
    setUser(null);
    localStorage.removeItem('user');
    console.log("User logged out successfully");
    setSuccessMessage("User logged out successfully");
  };

  const showSuccessMessage = (message: string) => {
    setSuccessMessage(message);
  };

  const clearSuccessMessage = () => {
    setSuccessMessage(null);
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    login,
    logout,
    loading,
    showSuccessMessage,
    successMessage,
    clearSuccessMessage,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext; 