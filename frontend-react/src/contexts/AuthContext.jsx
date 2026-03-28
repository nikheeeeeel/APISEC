import React, { createContext, useContext, useState, useEffect } from 'react';
import AuthService from '../services/auth';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check if user is logged in on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        if (AuthService.isLoggedIn()) {
          console.log('Found existing token, getting user info...');
          const userData = await AuthService.getCurrentUser();
          console.log('User data loaded:', userData);
          setUser(userData.user);
        }
      } catch (err) {
        console.error('Failed to get current user:', err);
        setError(err.message);
        AuthService.logout(); // Clear invalid token
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  // Login function
  const login = async (credentials) => {
    try {
      setLoading(true);
      setError(null);
      const response = await AuthService.login(credentials);
      AuthService.setToken(response.access_token);
      setUser(response.user);
      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Register function
  const register = async (userData) => {
    try {
      setLoading(true);
      setError(null);
      const response = await AuthService.register(userData);
      AuthService.setToken(response.access_token);
      setUser(response.user);
      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // OAuth login
  const loginWithOAuth = (provider) => {
    const oauthUrl = provider === 'google' 
      ? AuthService.getGoogleOAuthUrl()
      : AuthService.getGitHubOAuthUrl();
    
    window.location.href = oauthUrl;
  };

  // Handle OAuth callback
  const handleOAuthCallback = async (token) => {
    try {
      console.log('Handling OAuth callback with token:', token.substring(0, 20) + '...');
      AuthService.handleOAuthCallback(token);
      
      // Get user info after OAuth login
      const userData = await AuthService.getCurrentUser();
      console.log('OAuth user data received:', userData);
      
      setUser(userData.user);
      setError(null);
      console.log('OAuth login completed successfully');
    } catch (err) {
      console.error('OAuth callback error:', err);
      setError(err.message);
    }
  };

  // Logout function
  const logout = () => {
    AuthService.logout();
    setUser(null);
    setError(null);
  };

  // Clear error
  const clearError = () => {
    setError(null);
  };

  const value = {
    user,
    loading,
    error,
    login,
    register,
    loginWithOAuth,
    handleOAuthCallback,
    logout,
    clearError,
    isLoggedIn: !!user,
    isAdmin: user?.username === 'admin'
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
