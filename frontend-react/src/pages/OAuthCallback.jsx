import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const OAuthCallback = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { handleOAuthCallback } = useAuth();
  const [processing, setProcessing] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const processCallback = async () => {
      try {
        const token = searchParams.get('token');
        const errorParam = searchParams.get('error');
        
        console.log('OAuth callback processing:', { token, errorParam });
        
        if (token) {
          console.log('Setting token and getting user info...');
          await handleOAuthCallback(token);
          console.log('OAuth callback successful, redirecting to main app...');
          navigate('/', { replace: true });
        } else if (errorParam) {
          console.error('OAuth error:', errorParam);
          setError('OAuth login failed');
          setTimeout(() => {
            navigate('/login?error=oauth_failed', { replace: true });
          }, 2000);
        } else {
          console.log('No token or error in callback, redirecting to login');
          navigate('/login', { replace: true });
        }
      } catch (err) {
        console.error('Callback processing error:', err);
        setError('Failed to process login');
        setTimeout(() => {
          navigate('/login?error=callback_failed', { replace: true });
        }, 2000);
      } finally {
        setProcessing(false);
      }
    };

    processCallback();
  }, [searchParams, navigate, handleOAuthCallback]);

  if (processing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black">
        <div className="text-white text-lg">Processing login...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black">
        <div className="text-red-400 text-lg text-center">
          <div>{error}</div>
          <div className="mt-4 text-sm text-gray-400">Redirecting to login page...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-black">
      <div className="text-white text-lg">Processing login...</div>
    </div>
  );
};

export default OAuthCallback;
