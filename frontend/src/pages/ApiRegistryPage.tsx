import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_PATHS, RegisteredApi } from '../lib/api';
import { Plus, Trash2, RefreshCw, ExternalLink, Search, X, Loader2 } from 'lucide-react';

function ApiRegistryPage() {
  const navigate = useNavigate();
  const [apis, setApis] = useState<RegisteredApi[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [scanning, setScanning] = useState<number | null>(null);
  
  const [formData, setFormData] = useState({
    name: '',
    base_url: '',
    description: ''
  });

  const fetchApis = async () => {
    try {
      const response = await fetch(API_PATHS.apis);
      const data = await response.json();
      setApis(data.apis || []);
    } catch (err) {
      setError('Failed to load APIs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApis();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const response = await fetch(API_PATHS.apis, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        throw new Error('Failed to create API');
      }
      
      setFormData({ name: '', base_url: '', description: '' });
      setShowAddForm(false);
      fetchApis();
    } catch (err) {
      setError('Failed to create API');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this API?')) return;
    
    try {
      await fetch(API_PATHS.apiDetail(id), { method: 'DELETE' });
      fetchApis();
    } catch (err) {
      setError('Failed to delete API');
    }
  };

  const handleScan = async (api: RegisteredApi) => {
    setScanning(api.id);
    setError(null);
    
    try {
      const response = await fetch(API_PATHS.scanApi(api.id), {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        setError(data.error || 'Scan failed');
        return;
      }
      
      navigate(`/schema-monitor/${api.id}`);
    } catch (err) {
      setError('Failed to scan API');
    } finally {
      setScanning(null);
    }
  };

  const handleRescan = async (api: RegisteredApi) => {
    setScanning(api.id);
    setError(null);
    
    try {
      const response = await fetch(API_PATHS.rescanApi(api.id), {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        setError(data.error || 'Rescan failed');
        return;
      }
      
      navigate(`/schema-monitor/${api.id}`);
    } catch (err) {
      setError('Failed to rescan API');
    } finally {
      setScanning(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">API Registry</h1>
            <p className="text-gray-600 mt-1">Register and manage APIs for schema monitoring</p>
          </div>
          
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="h-5 w-5" />
            <span>Add API</span>
          </button>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <p className="text-red-700">{error}</p>
              <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>
        )}

        {showAddForm && (
          <div className="mb-6 bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Add New API</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="My API"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
                <input
                  type="url"
                  value={formData.base_url}
                  onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="https://api.example.com"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description (Optional)</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="API description..."
                />
              </div>
              
              <div className="flex space-x-3">
                <button
                  type="submit"
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Add API
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddForm(false);
                    setFormData({ name: '', base_url: '', description: '' });
                  }}
                  className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {apis.length === 0 ? (
          <div className="bg-white rounded-lg shadow-md p-12 text-center">
            <Search className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No APIs Registered</h3>
            <p className="text-gray-600 mb-4">Get started by adding your first API to monitor</p>
            <button
              onClick={() => setShowAddForm(true)}
              className="inline-flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="h-5 w-5" />
              <span>Add API</span>
            </button>
          </div>
        ) : (
          <div className="grid gap-4">
            {apis.map((api) => (
              <div key={api.id} className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <h3 className="text-xl font-semibold text-gray-900">{api.name}</h3>
                      <span className="text-sm text-gray-500">
                        v{api.id}
                      </span>
                    </div>
                    <p className="text-blue-600 mt-1 font-mono">{api.base_url}</p>
                    {api.description && (
                      <p className="text-gray-600 mt-2">{api.description}</p>
                    )}
                    <p className="text-sm text-gray-500 mt-2">
                      Added: {new Date(api.date_added).toLocaleDateString()}
                    </p>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleScan(api)}
                      disabled={scanning === api.id}
                      className="flex items-center space-x-1 bg-green-600 text-white px-3 py-2 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                    >
                      {scanning === api.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Search className="h-4 w-4" />
                      )}
                      <span>Scan</span>
                    </button>
                    
                    <button
                      onClick={() => handleRescan(api)}
                      disabled={scanning === api.id}
                      className="flex items-center space-x-1 bg-purple-600 text-white px-3 py-2 rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
                    >
                      {scanning === api.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                      <span>Rescan</span>
                    </button>
                    
                    <button
                      onClick={() => navigate(`/schema-monitor/${api.id}`)}
                      className="flex items-center space-x-1 bg-gray-600 text-white px-3 py-2 rounded-lg hover:bg-gray-700 transition-colors"
                    >
                      <ExternalLink className="h-4 w-4" />
                      <span>View</span>
                    </button>
                    
                    <button
                      onClick={() => handleDelete(api.id)}
                      className="flex items-center space-x-1 bg-red-600 text-white px-3 py-2 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default ApiRegistryPage;
