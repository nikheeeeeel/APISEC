import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Sidebar from './components/Sidebar';
import SchemaFinder from './pages/SchemaFinder';
import SchemaValidate from './pages/SchemaValidate';
import VersionCheck from './pages/VersionCheck';
import Login from './pages/Login';
import Register from './pages/Register';
import OAuthCallback from './pages/OAuthCallback';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/auth/callback" element={<OAuthCallback />} />
          
          {/* Protected routes */}
          <Route path="/" element={
            <ProtectedRoute>
              <div className="flex h-screen bg-black">
                <Sidebar />
                <div className="flex-1 overflow-auto">
                  <SchemaFinder />
                </div>
              </div>
            </ProtectedRoute>
          } />
          
          <Route path="/schema-finder" element={
            <ProtectedRoute>
              <div className="flex h-screen bg-black">
                <Sidebar />
                <div className="flex-1 overflow-auto">
                  <SchemaFinder />
                </div>
              </div>
            </ProtectedRoute>
          } />
          
          <Route path="/schema-validate" element={
            <ProtectedRoute>
              <div className="flex h-screen bg-black">
                <Sidebar />
                <div className="flex-1 overflow-auto">
                  <SchemaValidate />
                </div>
              </div>
            </ProtectedRoute>
          } />
          
          <Route path="/version-check" element={
            <ProtectedRoute>
              <div className="flex h-screen bg-black">
                <Sidebar />
                <div className="flex-1 overflow-auto">
                  <VersionCheck />
                </div>
              </div>
            </ProtectedRoute>
          } />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
