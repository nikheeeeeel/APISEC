import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import SchemaFinder from './pages/SchemaFinder';
import SchemaValidate from './pages/SchemaValidate';
import VersionCheck from './pages/VersionCheck';
import Login from './components/Login';
import ApiService from './services/api';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(ApiService.isAuthenticated());

  useEffect(() => {
    // A simple event listener to catch unauth events from ApiService or login changes
    const handleHashChange = () => {
      if (window.location.hash === '#/login') {
        setIsAuthenticated(false);
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  if (!isAuthenticated) {
    return <Login onLogin={() => setIsAuthenticated(true)} />;
  }

  return (
    <Router>
      <div className="flex h-screen bg-black text-white">
        <Sidebar onLogout={() => {
          ApiService.logout();
          setIsAuthenticated(false);
        }} />
        <div className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<SchemaFinder />} />
            <Route path="/schema-finder" element={<SchemaFinder />} />
            <Route path="/schema-validate" element={<SchemaValidate />} />
            <Route path="/version-check" element={<VersionCheck />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
