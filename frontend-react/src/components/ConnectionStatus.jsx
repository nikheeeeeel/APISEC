import { useState, useEffect } from 'react';
import { Wifi, WifiOff, AlertCircle } from 'lucide-react';
import ApiService from '../services/api';

const ConnectionStatus = () => {
  const [isConnected, setIsConnected] = useState(null);
  const [isChecking, setIsChecking] = useState(false);

  useEffect(() => {
    const checkConnection = async () => {
      setIsChecking(true);
      try {
        await ApiService.getApis();
        setIsConnected(true);
      } catch (error) {
        setIsConnected(false);
      } finally {
        setIsChecking(false);
      }
    };

    // Check connection on mount
    checkConnection();

    // Check connection every 30 seconds
    const interval = setInterval(checkConnection, 30000);

    return () => clearInterval(interval);
  }, []);

  if (isConnected === null) {
    return (
      <div className="flex items-center space-x-2 text-gray-400">
        <AlertCircle className="w-4 h-4 animate-pulse" />
        <span className="text-xs">Checking connection...</span>
      </div>
    );
  }

  if (isChecking) {
    return (
      <div className="flex items-center space-x-2 text-gray-400">
        <AlertCircle className="w-4 h-4 animate-pulse" />
        <span className="text-xs">Checking...</span>
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-2">
      {isConnected ? (
        <>
          <Wifi className="w-4 h-4 text-green-500" />
          <span className="text-xs text-green-500">Connected</span>
        </>
      ) : (
        <>
          <WifiOff className="w-4 h-4 text-red-400" />
          <span className="text-xs text-red-400">Backend Offline</span>
        </>
      )}
    </div>
  );
};

export default ConnectionStatus;
