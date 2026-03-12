import { Link, useLocation } from 'react-router-dom';
import { 
  Search, 
  CheckCircle, 
  GitCompare, 
  BarChart3,
  Settings,
  Shield
} from 'lucide-react';
import ConnectionStatus from './ConnectionStatus';

const menuItems = [
  { path: '/schema-finder', label: 'Schema Finder', icon: Search },
  { path: '/schema-validate', label: 'Schema Validate', icon: CheckCircle },
  { path: '/version-check', label: 'Version Check', icon: GitCompare },
];

const Sidebar = () => {
  const location = useLocation();

  return (
    <div className="w-64 bg-black border-r border-gray-800 flex flex-col">
      {/* Logo Section */}
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg flex items-center justify-center">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">APISEC</h1>
            <p className="text-xs text-gray-400">Security Scanner</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <div className="space-y-2">
          {menuItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                  isActive
                    ? 'bg-orange-500/20 text-orange-500 border-l-4 border-orange-500'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Bottom Section */}
      <div className="p-4 border-t border-gray-800 space-y-4">
        <div className="glass-card p-4">
          <div className="flex items-center space-x-2 mb-2">
            <BarChart3 className="w-4 h-4 text-green-500" />
            <span className="text-xs text-gray-400">System Status</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-white">Operational</span>
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          </div>
        </div>
        
        <div className="glass-card p-4">
          <div className="flex items-center space-x-2 mb-2">
            <Shield className="w-4 h-4 text-orange-500" />
            <span className="text-xs text-gray-400">Backend</span>
          </div>
          <ConnectionStatus />
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
