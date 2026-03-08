import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Shield, Home, List, FileSearch } from 'lucide-react';
import HomePage from './pages/HomePage';
import ApiRegistryPage from './pages/ApiRegistryPage';
import SchemaMonitorPage from './pages/SchemaMonitorPage';

function Navbar() {
  const location = useLocation();
  
  const isActive = (path: string) => location.pathname === path;
  
  return (
    <nav className="bg-slate-900 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center space-x-2">
            <Shield className="h-8 w-8 text-blue-400" />
            <span className="text-xl font-bold">APISec</span>
          </Link>
          
          <div className="flex space-x-1">
            <Link
              to="/"
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                isActive('/') 
                  ? 'bg-blue-600 text-white' 
                  : 'text-gray-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <Home className="h-4 w-4" />
              <span>Home</span>
            </Link>
            
            <Link
              to="/registry"
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                isActive('/registry') 
                  ? 'bg-blue-600 text-white' 
                  : 'text-gray-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <List className="h-4 w-4" />
              <span>API Registry</span>
            </Link>
            
            <Link
              to="/schema-monitor"
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                isActive('/schema-monitor') 
                  ? 'bg-blue-600 text-white' 
                  : 'text-gray-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <FileSearch className="h-4 w-4" />
              <span>Schema Monitor</span>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/registry" element={<ApiRegistryPage />} />
          <Route path="/schema-monitor" element={<SchemaMonitorPage />} />
          <Route path="/schema-monitor/:apiId" element={<SchemaMonitorPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
