import { useState } from 'react';
import { Search, Download, Globe, CheckCircle, AlertCircle, Loader2, Plus } from 'lucide-react';
import ApiService from '../services/api';

const SchemaFinder = () => {
  const [uri, setUri] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [schema, setSchema] = useState(null);
  const [error, setError] = useState('');

  const handleScan = async () => {
    if (!uri) return;
    
    setIsScanning(true);
    setError('');
    setSchema(null);
    
    try {
      const response = await ApiService.discoverSchema(uri);
      
      if (response.status === 'success') {
        setSchema({
          id: 'schema_' + Date.now(),
          uri: uri,
          title: response.schema?.info?.title || 'API Schema',
          version: response.schema?.info?.version || '1.0.0',
          endpoints: Object.keys(response.schema?.paths || {}).length,
          methods: ['GET', 'POST', 'PUT', 'DELETE'],
          foundAt: new Date().toISOString(),
          schema: response.schema,
          schema_url: response.schema_url
        });
      } else if (response.status === 'not_found') {
        setError(response.message || 'No schema found for the provided URI');
      } else {
        setError('Failed to discover schema');
      }
    } catch (err) {
      setError('Error connecting to the backend. Please try again.');
      console.error('Schema discovery error:', err);
    } finally {
      setIsScanning(false);
    }
  };

  const handleSaveToDatabase = async () => {
    if (!schema) return;
    
    try {
      const response = await ApiService.createApi(
        schema.title,
        schema.uri,
        `Schema discovered at ${new Date().toLocaleString()}`
      );
      
      if (response.status === 'success') {
        // Show success message
        const successMessage = document.createElement('div');
        successMessage.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
        successMessage.textContent = 'API saved to database successfully!';
        document.body.appendChild(successMessage);
        
        setTimeout(() => {
          document.body.removeChild(successMessage);
        }, 3000);
      } else if (response.status === 'exists') {
        // Show info message for existing API
        const infoMessage = document.createElement('div');
        infoMessage.className = 'fixed top-4 right-4 bg-blue-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
        infoMessage.textContent = 'API with this URL already exists in database';
        document.body.appendChild(infoMessage);
        
        setTimeout(() => {
          document.body.removeChild(infoMessage);
        }, 3000);
      } else {
        throw new Error(response.error || 'Failed to save API');
      }
    } catch (err) {
      // Show error message
      const errorMessage = document.createElement('div');
      errorMessage.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
      errorMessage.textContent = err.message || 'Error saving to database';
      document.body.appendChild(errorMessage);
      
      setTimeout(() => {
        document.body.removeChild(errorMessage);
      }, 3000);
      
      console.error('Save error:', err);
    }
  };

  const handleDownload = () => {
    if (schema) {
      const dataStr = JSON.stringify(schema.schema, null, 2);
      const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
      const exportFileDefaultName = `schema_${schema.id}.json`;
      
      const linkElement = document.createElement('a');
      linkElement.setAttribute('href', dataUri);
      linkElement.setAttribute('download', exportFileDefaultName);
      linkElement.click();
    }
  };

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Schema Finder</h1>
          <p className="text-gray-400">Discover and download API schemas from any URI</p>
        </div>

        {/* Search Section */}
        <div className="glass-card p-6 mb-8">
          <div className="flex space-x-4">
            <div className="flex-1">
              <div className="relative">
                <Globe className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Enter API URI (e.g., https://api.example.com)"
                  value={uri}
                  onChange={(e) => setUri(e.target.value)}
                  className="input-field pl-10 w-full"
                />
              </div>
            </div>
            <button
              onClick={handleScan}
              disabled={!uri || isScanning}
              className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isScanning ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Search className="w-5 h-5" />
              )}
              <span>{isScanning ? 'Scanning...' : 'Find Schema'}</span>
            </button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="glass-card p-4 mb-6 border-l-4 border-red-500">
            <div className="flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-red-400" />
              <span className="text-red-400">{error}</span>
            </div>
          </div>
        )}

        {/* Schema Result */}
        {schema && (
          <div className="space-y-6">
            {/* Schema Card */}
            <div className="glass-card p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="text-xl font-bold text-white mb-2">{schema.title}</h2>
                  <div className="flex items-center space-x-4 text-sm text-gray-400">
                    <span>Version: {schema.version}</span>
                    <span>•</span>
                    <span>{schema.endpoints} endpoints</span>
                    <span>•</span>
                    <span>{schema.methods.length} methods</span>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={handleSaveToDatabase}
                    className="btn-secondary flex items-center space-x-2"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Save to DB</span>
                  </button>
                  <button
                    onClick={handleDownload}
                    className="btn-secondary flex items-center space-x-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download</span>
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-slate-900/50 p-4 rounded-lg">
                  <div className="flex items-center space-x-2 mb-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span className="text-xs text-gray-400">Status</span>
                  </div>
                  <span className="text-sm font-medium text-white">Schema Found</span>
                </div>
                <div className="bg-slate-900/50 p-4 rounded-lg">
                  <div className="flex items-center space-x-2 mb-2">
                    <Globe className="w-4 h-4 text-blue-500" />
                    <span className="text-xs text-gray-400">Source</span>
                  </div>
                  <span className="text-sm font-medium text-white truncate">{schema.uri}</span>
                </div>
                <div className="bg-slate-900/50 p-4 rounded-lg">
                  <div className="flex items-center space-x-2 mb-2">
                    <Search className="w-4 h-4 text-orange-500" />
                    <span className="text-xs text-gray-400">Found At</span>
                  </div>
                  <span className="text-sm font-medium text-white">
                    {new Date(schema.foundAt).toLocaleTimeString()}
                  </span>
                </div>
              </div>

              {/* Schema Preview */}
              <div>
                <h3 className="text-lg font-semibold text-white mb-3">Schema Preview</h3>
                <div className="bg-slate-900/50 p-4 rounded-lg overflow-x-auto">
                  <pre className="text-sm text-gray-300 font-mono">
                    {JSON.stringify(schema.schema, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!schema && !error && !isScanning && (
          <div className="glass-card p-12 text-center">
            <Search className="w-16 h-16 text-gray-500 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No Schema Yet</h3>
            <p className="text-gray-400">Enter a URI above to start searching for API schemas</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SchemaFinder;
