import { useState, useEffect } from 'react';
import { GitCompare, RefreshCw, Download, ChevronDown, Plus, Minus, FileText, Clock, AlertCircle, CheckCircle, Trash2, Sparkles, Lightbulb, Shield, ChevronRight, Search, Zap, Bot } from 'lucide-react';
import ApiService from '../services/api';

const formatAnalysisText = (text) => {
  if (!text) return null;
  const blocks = text.split('```');
  return blocks.map((block, index) => {
    if (index % 2 === 1) {
      const lines = block.split('\n');
      const code = lines.slice(1).join('\n');
      return (
        <pre key={index} className="bg-slate-900 p-3 rounded-md my-2 overflow-x-auto text-xs font-mono text-gray-300 border border-slate-800">
          <code>{code}</code>
        </pre>
      );
    }
    const paragraphs = block.split('\n\n').filter(p => p.trim());
    return (
      <div key={index} className="space-y-2 mt-2">
        {paragraphs.map((p, pIndex) => {
          const parts = p.split(/(\*\*.*?\*\*)/g);
          return (
            <p key={pIndex} className="text-sm text-gray-300 leading-relaxed">
              {parts.map((part, i) => {
                if (part.startsWith('**') && part.endsWith('**')) {
                  return <strong key={i} className="text-purple-300 font-semibold">{part.slice(2, -2)}</strong>;
                }
                return part;
              })}
            </p>
          );
        })}
      </div>
    );
  });
};

const VersionCheck = () => {
  const [apis, setApis] = useState([]);
  const [selectedApi, setSelectedApi] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [comparison, setComparison] = useState(null);
  const [selectedVersions, setSelectedVersions] = useState({ current: '', new: '' });
  const [searchTerm, setSearchTerm] = useState('');
  const [analyzingIndex, setAnalyzingIndex] = useState(null);
  const [changeFilter, setChangeFilter] = useState('all');

  // Debug logging
  console.log('VersionCheck render - selectedApi:', selectedApi);
  console.log('VersionCheck render - comparison:', comparison);
  console.log('VersionCheck render - selectedVersions:', selectedVersions);

  const handleAnalyzeSpecificChange = async (index, change) => {
    if (!selectedApi) return;
    
    setAnalyzingIndex(index);
    try {
      const response = await ApiService.analyzeChange(
        selectedApi.id,
        parseInt(selectedVersions.current),
        parseInt(selectedVersions.new),
        change
      );
      
      if (response.status === 'success') {
        const newComparison = { ...comparison };
        newComparison.changes[index].detailedAnalysis = response.analysis;
        setComparison(newComparison);
      } else {
        throw new Error(response.error || 'Failed to analyze change');
      }
    } catch (error) {
      console.error('Analysis error:', error);
      const newComparison = { ...comparison };
      newComparison.changes[index].detailedAnalysis = 'Error: ' + error.message;
      setComparison(newComparison);
    } finally {
      setAnalyzingIndex(null);
    }
  };

  const filteredChanges = comparison?.changes?.filter(change => 
    (changeFilter === 'all' || change.type === changeFilter) &&
    ((change.path && change.path.toLowerCase().includes(searchTerm.toLowerCase())) || 
    (change.description && change.description.toLowerCase().includes(searchTerm.toLowerCase())))
  ) || [];

  useEffect(() => {
    const loadApis = async () => {
      try {
        const response = await ApiService.getApis();
        if (response.status === 'success') {
          // Transform API data to include schema information
          const apisWithSchemas = await Promise.all(
            response.apis.map(async (api) => {
              try {
                const schemasResponse = await ApiService.getApiSchemas(api.id);
                const schemas = schemasResponse.status === 'success' ? schemasResponse.schemas : [];
                const latestSchema = schemas.length > 0 ? schemas[0] : null;
                
                return {
                  ...api,
                  lastScanned: latestSchema?.timestamp || api.date_added,
                  version: latestSchema?.version_number?.toString() || '1.0.0',
                  status: schemas.length > 1 ? 'update-available' : 'current',
                  schemas: schemas
                };
              } catch (error) {
                return {
                  ...api,
                  lastScanned: api.date_added,
                  version: '1.0.0',
                  status: 'current',
                  schemas: []
                };
              }
            })
          );
          
          setApis(apisWithSchemas);
        }
      } catch (error) {
        console.error('Failed to load APIs:', error);
      }
    };

    loadApis();
  }, []);

  const handleRescan = async (apiId) => {
    setIsScanning(apiId);
    
    try {
      const response = await ApiService.scanApiSchema(apiId);
      
      if (response.status === 'success') {
        // Reload the APIs to show updated data
        const apisResponse = await ApiService.getApis();
        if (apisResponse.status === 'success') {
          const apisWithSchemas = await Promise.all(
            apisResponse.apis.map(async (api) => {
              try {
                const schemasResponse = await ApiService.getApiSchemas(api.id);
                const schemas = schemasResponse.status === 'success' ? schemasResponse.schemas : [];
                const latestSchema = schemas.length > 0 ? schemas[0] : null;
                
                return {
                  ...api,
                  lastScanned: latestSchema?.timestamp || api.date_added,
                  version: latestSchema?.version_number?.toString() || '1.0.0',
                  status: schemas.length > 1 ? 'update-available' : 'current',
                  schemas: schemas
                };
              } catch (error) {
                return {
                  ...api,
                  lastScanned: api.date_added,
                  version: '1.0.0',
                  status: 'current',
                  schemas: []
                };
              }
            })
          );
          
          setApis(apisWithSchemas);
          
          // Show success message
          const successMessage = document.createElement('div');
          successMessage.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
          successMessage.textContent = 'Schema scanned successfully!';
          document.body.appendChild(successMessage);
          
          setTimeout(() => {
            document.body.removeChild(successMessage);
          }, 3000);
        }
      } else if (response.status === 'unchanged') {
        // Show info message
        const infoMessage = document.createElement('div');
        infoMessage.className = 'fixed top-4 right-4 bg-blue-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
        infoMessage.textContent = 'Schema has not changed since last scan';
        document.body.appendChild(infoMessage);
        
        setTimeout(() => {
          document.body.removeChild(infoMessage);
        }, 3000);
      } else {
        throw new Error(response.error || 'Failed to scan API schema');
      }
    } catch (error) {
      // Show error message
      const errorMessage = document.createElement('div');
      errorMessage.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
      errorMessage.textContent = error.message || 'Error scanning API schema';
      document.body.appendChild(errorMessage);
      
      setTimeout(() => {
        document.body.removeChild(errorMessage);
      }, 3000);
      
      console.error('Scan error:', error);
    } finally {
      setIsScanning(false);
    }
  };

  const handleDeleteApi = async (apiId, apiName) => {
    if (!window.confirm(`Are you sure you want to delete "${apiName}" and all its schema data? This action cannot be undone.`)) {
      return;
    }
    
    try {
      const response = await ApiService.deleteApi(apiId);
      
      if (response.status === 'success' || response.status === 'deleted') {
        // Show success message
        const successMessage = document.createElement('div');
        successMessage.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
        successMessage.textContent = `API "${apiName}" deleted successfully`;
        document.body.appendChild(successMessage);
        
        setTimeout(() => {
          document.body.removeChild(successMessage);
        }, 3000);
        
        // Reload the APIs list
        const loadApis = async () => {
          try {
            const apisResponse = await ApiService.getApis();
            if (apisResponse.status === 'success') {
              const apisWithSchemas = await Promise.all(
                apisResponse.apis.map(async (api) => {
                  try {
                    const schemasResponse = await ApiService.getApiSchemas(api.id);
                    const schemas = schemasResponse.status === 'success' ? schemasResponse.schemas : [];
                    const latestSchema = schemas.length > 0 ? schemas[0] : null;
                    
                    return {
                      ...api,
                      lastScanned: latestSchema?.timestamp || api.date_added,
                      version: latestSchema?.version_number?.toString() || '1.0.0',
                      status: schemas.length > 1 ? 'update-available' : 'current',
                      schemas: schemas
                    };
                  } catch (error) {
                    return {
                      ...api,
                      lastScanned: api.date_added,
                      version: '1.0.0',
                      status: 'current',
                      schemas: []
                    };
                  }
                })
              );
              
              setApis(apisWithSchemas);
            }
          } catch (error) {
            console.error('Failed to reload APIs:', error);
          }
        };
        
        loadApis();
        
        // Clear comparison if deleted API was selected
        if (selectedApi && selectedApi.id === apiId) {
          setSelectedApi(null);
          setComparison(null);
        }
      } else {
        throw new Error(response.error || 'Failed to delete API');
      }
    } catch (error) {
      // Show error message
      const errorMessage = document.createElement('div');
      errorMessage.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
      errorMessage.textContent = error.message || 'Error deleting API';
      document.body.appendChild(errorMessage);
      
      setTimeout(() => {
        document.body.removeChild(errorMessage);
      }, 3000);
      
      console.error('Delete error:', error);
    }
  };

  const handleVersionCompare = async (currentVersion, newVersion) => {
    if (!selectedApi || currentVersion === newVersion) {
      return;
    }
    
    try {
      const response = await ApiService.compareSchemaVersions(
        selectedApi.id,
        parseInt(currentVersion),
        parseInt(newVersion),
        true
      );
      
      if (response.status === 'success') {
        // Parse the actual backend response structure
        const summary = response.summary || {};
        const changes = response.changes || [];
        
        // Count changes by type from the actual changes array
        const addedCount = changes.filter(c => c.type === 'added').length;
        const removedCount = changes.filter(c => c.type === 'removed').length;
        const modifiedCount = changes.filter(c => c.type === 'modified').length;
        
        setComparison({
          summary: {
            added: addedCount,
            removed: removedCount,
            modified: modifiedCount,
            total: changes.length
          },
          aiEnabled: response.ai_enabled || false,
          changes: changes.map(change => ({
            type: change.type || 'unknown',
            path: change.path || '',
            description: change.details || change.description || 'No description',
            impact: change.breaking_change === 'breaking' ? 'high' : 
                   change.breaking_change === 'non_breaking' ? 'low' : 'medium',
            aiDescription: change.ai_description || null,
            aiImpactAnalysis: change.ai_impact_analysis || null,
            aiFixSuggestion: change.ai_fix_suggestion || null
          }))
        });
      } else {
        throw new Error(response.error || 'Failed to compare schema versions');
      }
    } catch (error) {
      const errorMessage = document.createElement('div');
      errorMessage.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
      errorMessage.textContent = error.message || 'Error comparing schemas';
      document.body.appendChild(errorMessage);
      
      setTimeout(() => {
        document.body.removeChild(errorMessage);
      }, 3000);
      
      console.error('Compare error:', error);
    }
  };

  const handleCompare = async (api) => {
    console.log('handleCompare called with:', api);
    setSelectedApi(api);
    
    try {
      if (api.schemas && api.schemas.length >= 2) {
        console.log('API has schemas:', api.schemas.length);
        // Get the two latest versions for comparison
        const latestVersion = api.schemas[0].version_number;
        const previousVersion = api.schemas[1].version_number;
        
        console.log('Comparing versions:', previousVersion, 'vs', latestVersion);
        
        const response = await ApiService.compareSchemaVersions(
          api.id,
          previousVersion,
          latestVersion,
          true
        );
        
        console.log('Comparison response:', response);
        
        if (response.status === 'success') {
          // Parse the actual backend response structure
          const summary = response.summary || {};
          const changes = response.changes || [];
          
          console.log('Parsed summary:', summary);
          console.log('Parsed changes count:', changes.length);
          
          // Count changes by type from the actual changes array
          const addedCount = changes.filter(c => c.type === 'added').length;
          const removedCount = changes.filter(c => c.type === 'removed').length;
          const modifiedCount = changes.filter(c => c.type === 'modified').length;
          
          console.log('Change counts:', { addedCount, removedCount, modifiedCount });
          
          const comparisonData = {
            summary: {
              added: addedCount,
              removed: removedCount,
              modified: modifiedCount,
              total: changes.length
            },
            aiEnabled: response.ai_enabled || false,
            changes: changes.map(change => ({
              type: change.type || 'unknown',
              path: change.path || '',
              description: change.details || change.description || 'No description',
              impact: change.breaking_change === 'breaking' ? 'high' : 
                     change.breaking_change === 'non_breaking' ? 'low' : 'medium',
              aiDescription: change.ai_description || null,
              aiImpactAnalysis: change.ai_impact_analysis || null,
              aiFixSuggestion: change.ai_fix_suggestion || null
            }))
          };
          
          console.log('Setting comparison data:', comparisonData);
          
          setSelectedVersions({
            current: previousVersion.toString(),
            new: latestVersion.toString()
          });
          
          setChangeFilter('all');
          setComparison(comparisonData);
        } else {
          throw new Error(response.error || 'Failed to compare schema versions');
        }
      } else {
        console.log('API does not have enough schemas');
        // Show info message
        const infoMessage = document.createElement('div');
        infoMessage.className = 'fixed top-4 right-4 bg-blue-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
        infoMessage.textContent = 'Need at least 2 schema versions to compare';
        document.body.appendChild(infoMessage);
        
        setTimeout(() => {
          document.body.removeChild(infoMessage);
        }, 3000);
      }
    } catch (error) {
      console.error('Compare error:', error);
      // Show error message
      const errorMessage = document.createElement('div');
      errorMessage.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
      errorMessage.textContent = error.message || 'Error comparing schemas';
      document.body.appendChild(errorMessage);
      
      setTimeout(() => {
        document.body.removeChild(errorMessage);
      }, 3000);
    }
  };

  const getChangeIcon = (type) => {
    switch (type) {
      case 'added':
        return <Plus className="w-4 h-4 text-green-500" />;
      case 'removed':
        return <Minus className="w-4 h-4 text-red-400" />;
      case 'modified':
        return <RefreshCw className="w-4 h-4 text-yellow-400" />;
      default:
        return <RefreshCw className="w-4 h-4 text-gray-400" />;
    }
  };

  const getChangeColor = (type) => {
    switch (type) {
      case 'added':
        return 'text-green-500 bg-green-500/10';
      case 'removed':
        return 'text-red-400 bg-red-400/10';
      case 'modified':
        return 'text-yellow-400 bg-yellow-400/10';
      default:
        return 'text-gray-400 bg-gray-400/10';
    }
  };

  const getImpactColor = (impact) => {
    switch (impact) {
      case 'high':
        return 'text-red-400 bg-red-400/10';
      case 'medium':
        return 'text-yellow-400 bg-yellow-400/10';
      case 'low':
        return 'text-green-500 bg-green-500/10';
      default:
        return 'text-gray-400 bg-gray-400/10';
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'current':
        return <span className="px-2 py-1 text-xs font-medium text-green-500 bg-green-500/10 rounded-full">Current</span>;
      case 'update-available':
        return <span className="px-2 py-1 text-xs font-medium text-yellow-400 bg-yellow-400/10 rounded-full">Update Available</span>;
      case 'outdated':
        return <span className="px-2 py-1 text-xs font-medium text-red-400 bg-red-400/10 rounded-full">Outdated</span>;
      default:
        return null;
    }
  };

  return (
    <div className="p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Version Check</h1>
          <p className="text-gray-400">Monitor API versions and detect schema changes</p>
        </div>

        {/* API Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {apis.map(api => (
            <div key={api.id} className="glass-card p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-1">{api.name}</h3>
                  <div className="flex items-center space-x-2 mb-2">
                    {getStatusBadge(api.status)}
                    {api.newVersion && (
                      <span className="text-sm text-gray-400">
                        v{api.version} → v{api.newVersion}
                      </span>
                    )}
                  </div>
                </div>
                <FileText className="w-5 h-5 text-gray-400" />
              </div>

              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Version</span>
                  <span className="text-white font-medium">v{api.version}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Last Scanned</span>
                  <span className="text-white">
                    {new Date(api.lastScanned).toLocaleDateString()}
                  </span>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => handleRescan(api.id)}
                  disabled={isScanning === api.id}
                  className="flex-1 min-w-[100px] btn-secondary flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  {isScanning === api.id ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                  <span>{isScanning === api.id ? 'Scanning...' : 'Rescan'}</span>
                </button>
                {(api.status === 'update-available' || api.schemas.length > 1) && (
                  <button
                    onClick={() => handleCompare(api)}
                    className="flex-1 min-w-[100px] btn-primary flex items-center justify-center space-x-2"
                  >
                    <GitCompare className="w-4 h-4" />
                    <span>Compare</span>
                  </button>
                )}
                <button
                  onClick={() => handleDeleteApi(api.id, api.name)}
                  className="btn-secondary flex items-center justify-center space-x-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 px-3"
                  title="Delete API and all schema data"
                >
                  <Trash2 className="w-4 h-4" />
                  <span className="hidden sm:inline">Delete</span>
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Comparison Section */}
        {selectedApi && (
          <div className="glass-card p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">Schema Comparison</h2>
              <button
                onClick={() => {
                  setComparison(null);
                  setSelectedApi(null);
                  setChangeFilter('all');
                }}
                className="text-gray-400 hover:text-white"
              >
                ×
              </button>
            </div>

            {/* Debug Info */}
            <div className="bg-slate-800/50 p-3 rounded-lg mb-4 text-xs text-gray-400">
              <div>API: {selectedApi.name} (ID: {selectedApi.id})</div>
              <div>Schemas: {selectedApi.schemas?.length || 0}</div>
              <div>Comparison loaded: {comparison ? 'Yes' : 'No'}</div>
              {comparison && (
                <>
                  <div>Comparison total: {comparison.summary?.total || 'N/A'}</div>
                  <div>Changes count: {comparison.changes?.length || 0}</div>
                </>
              )}
            </div>

            {!comparison && (
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 mb-6">
                <div className="flex items-center space-x-3">
                  <AlertCircle className="w-5 h-5 text-blue-400" />
                  <div>
                    <p className="text-blue-400 font-medium">Loading comparison...</p>
                    <p className="text-blue-300 text-sm mt-1">
                      Please wait while we compare the schema versions
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Version Selector and rest of comparison UI */}
            {comparison && (
              <>
            {/* Version Selector */}
            <div className="flex items-center space-x-4 mb-6">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-300 mb-2">Current Version</label>
                <div className="relative">
                  <select
                    value={selectedVersions.current}
                    onChange={(e) => {
                      const newVersion = e.target.value;
                      setSelectedVersions({...selectedVersions, current: newVersion});
                      handleVersionCompare(newVersion, selectedVersions.new);
                    }}
                    className="input-field pr-10 appearance-none"
                  >
                    {selectedApi.schemas && selectedApi.schemas.map((schema, index) => (
                      <option key={schema.version_number} value={schema.version_number.toString()}>
                        v{schema.version_number}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-3 top-3 w-5 h-5 text-gray-400 pointer-events-none" />
                </div>
              </div>
              <div className="flex items-center justify-center">
                <GitCompare className="w-6 h-6 text-accent-blue" />
              </div>
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-300 mb-2">New Version</label>
                <div className="relative">
                  <select
                    value={selectedVersions.new}
                    onChange={(e) => {
                      const newVersion = e.target.value;
                      setSelectedVersions({...selectedVersions, new: newVersion});
                      handleVersionCompare(selectedVersions.current, newVersion);
                    }}
                    className="input-field pr-10 appearance-none"
                  >
                    {selectedApi.schemas && selectedApi.schemas.map((schema, index) => (
                      <option key={schema.version_number} value={schema.version_number.toString()}>
                        v{schema.version_number}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-3 top-3 w-5 h-5 text-gray-400 pointer-events-none" />
                </div>
              </div>
            </div>

            {/* Single Version Warning */}
            {selectedApi.schemas && selectedApi.schemas.length < 2 && (
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 mb-6">
                <div className="flex items-center space-x-3">
                  <AlertCircle className="w-5 h-5 text-blue-400" />
                  <div>
                    <p className="text-blue-400 font-medium">Only one schema version available</p>
                    <p className="text-blue-300 text-sm mt-1">
                      Scan this API multiple times to create different versions for comparison
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* No Changes Message */}
            {selectedApi.schemas && selectedApi.schemas.length >= 2 && 
             comparison && comparison.summary.total === 0 && (
              <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 mb-6">
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  <div>
                    <p className="text-green-400 font-medium">No changes detected</p>
                    <p className="text-green-300 text-sm mt-1">
                      The selected schema versions are identical
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Summary Stats */}
            {comparison && comparison.summary.total > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div 
                  className={`bg-slate-900/50 p-4 rounded-lg text-center cursor-pointer transition-all ${changeFilter === 'all' ? 'ring-2 ring-purple-500 shadow-[0_0_15px_rgba(168,85,247,0.3)]' : 'hover:bg-slate-800/50 hover:shadow-md'}`}
                  onClick={() => setChangeFilter('all')}
                >
                  <div className="text-2xl font-bold text-white mb-1">{comparison.summary.total}</div>
                  <div className="text-xs text-gray-400">Total Changes</div>
                </div>
                <div 
                  className={`bg-slate-900/50 p-4 rounded-lg text-center cursor-pointer transition-all ${changeFilter === 'added' ? 'ring-2 ring-green-500 shadow-[0_0_15px_rgba(34,197,94,0.3)]' : 'hover:bg-slate-800/50 hover:shadow-md'}`}
                  onClick={() => setChangeFilter('added')}
                >
                  <div className="text-2xl font-bold text-green-500 mb-1">{comparison.summary.added}</div>
                  <div className="text-xs text-gray-400">Added</div>
                </div>
                <div 
                  className={`bg-slate-900/50 p-4 rounded-lg text-center cursor-pointer transition-all ${changeFilter === 'removed' ? 'ring-2 ring-red-400 shadow-[0_0_15px_rgba(248,113,113,0.3)]' : 'hover:bg-slate-800/50 hover:shadow-md'}`}
                  onClick={() => setChangeFilter('removed')}
                >
                  <div className="text-2xl font-bold text-red-400 mb-1">{comparison.summary.removed}</div>
                  <div className="text-xs text-gray-400">Removed</div>
                </div>
                <div 
                  className={`bg-slate-900/50 p-4 rounded-lg text-center cursor-pointer transition-all ${changeFilter === 'modified' ? 'ring-2 ring-yellow-400 shadow-[0_0_15px_rgba(250,204,21,0.3)]' : 'hover:bg-slate-800/50 hover:shadow-md'}`}
                  onClick={() => setChangeFilter('modified')}
                >
                  <div className="text-2xl font-bold text-yellow-400 mb-1">{comparison.summary.modified}</div>
                  <div className="text-xs text-gray-400">Modified</div>
                </div>
              </div>
            )}

            {/* Changes List */}
            {comparison && comparison.summary.total > 0 && (
              <div>
                <div className="flex flex-col md:flex-row md:items-center justify-between mb-4 gap-4">
                  <h3 className="text-lg font-semibold text-white flex items-center space-x-2">
                    <span>Changes Detected</span>
                    {comparison.aiEnabled && (
                      <span className="flex items-center space-x-1 text-xs font-medium text-purple-400 bg-purple-400/10 px-2 py-1 rounded-full">
                        <Sparkles className="w-3 h-3" />
                        <span>AI Analyzed</span>
                      </span>
                    )}
                  </h3>
                  
                  {/* Search input */}
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      placeholder="Search changes..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-9 pr-4 py-2 bg-slate-900/50 border border-slate-700/50 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-purple-500/50 focus:bg-slate-800 transition-all w-full md:w-64"
                    />
                  </div>
                </div>
                <div className="space-y-3">
                  {filteredChanges.length === 0 ? (
                    <div className="text-gray-400 text-center py-8 bg-slate-900/30 rounded-lg border border-slate-800/50 border-dashed flex flex-col items-center">
                      <Search className="w-8 h-8 text-gray-600 mb-3" />
                      <span>No changes match your search.</span>
                    </div>
                  ) : (
                    filteredChanges.map((change) => {
                      const originalIndex = comparison.changes.indexOf(change);
                      return (
                    <div key={originalIndex} className="bg-slate-900/50 p-4 rounded-lg">
                      <div className="flex items-start space-x-3">
                        <div className="mt-1">
                          {getChangeIcon(change.type)}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-2">
                            <span className={`text-sm font-medium ${getChangeColor(change.type)}`}>
                              {change.type.charAt(0).toUpperCase() + change.type.slice(1)}
                            </span>
                            <code className="text-xs text-gray-400 bg-slate-800/50 px-2 py-1 rounded">
                              {change.path}
                            </code>
                            <div className="ml-auto flex items-center">
                                <button
                                  onClick={() => handleAnalyzeSpecificChange(originalIndex, change)}
                                  disabled={analyzingIndex === originalIndex}
                                  className="text-xs flex items-center space-x-1.5 bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 px-3 py-1.5 rounded-md border border-purple-500/30 transition-colors disabled:opacity-50 font-medium"
                                >
                                  {analyzingIndex === originalIndex ? (
                                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                  ) : (
                                    <Zap className="w-3.5 h-3.5" />
                                  )}
                                  <span>Analyze</span>
                                </button>
                            </div>
                          </div>
                          <p className="text-sm text-gray-300">{change.description}</p>
                          
                          {/* Deep Analysis Expandable Block */}
                          {change.detailedAnalysis && (
                            <div className="mt-4 bg-slate-950/80 rounded-lg p-5 border border-purple-500/30 shadow-inner">
                              <div className="flex items-center space-x-2 mb-3 border-b border-purple-500/20 pb-2">
                                <Bot className="w-5 h-5 text-purple-400" />
                                <h4 className="text-sm font-semibold text-purple-300 tracking-wide">AI Developer Analysis</h4>
                              </div>
                              <div className="text-gray-300">
                                {formatAnalysisText(change.detailedAnalysis)}
                              </div>
                            </div>
                          )}
                          
                          {/* AI Description */}
                          {change.aiDescription && (
                            <div className="mt-3 bg-slate-800/60 rounded-lg p-3 border border-slate-700/50">
                              <div className="flex items-start space-x-2">
                                <Sparkles className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
                                <div>
                                  <p className="text-xs font-medium text-purple-400 mb-1">AI Analysis</p>
                                  <p className="text-sm text-gray-300 leading-relaxed">{change.aiDescription}</p>
                                </div>
                              </div>
                            </div>
                          )}
                          
                          {/* AI Impact Analysis */}
                          {change.aiImpactAnalysis && (
                            <div className="mt-2 flex items-start space-x-2 bg-slate-800/40 rounded-md p-2">
                              <Shield className="w-3.5 h-3.5 text-blue-400 mt-0.5 flex-shrink-0" />
                              <p className="text-xs text-blue-300">
                                <span className="font-medium text-blue-400">Impact: </span>
                                {change.aiImpactAnalysis}
                              </p>
                            </div>
                          )}
                          
                          {/* AI Fix Suggestion (only for breaking changes) */}
                          {change.aiFixSuggestion && (
                            <div className="mt-2 bg-amber-500/5 border border-amber-500/20 rounded-lg p-3">
                              <div className="flex items-start space-x-2">
                                <Lightbulb className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                                <div>
                                  <p className="text-xs font-medium text-amber-400 mb-1">How to Fix</p>
                                  <p className="text-sm text-amber-200/80 leading-relaxed">{change.aiFixSuggestion}</p>
                                </div>
                              </div>
                            </div>
                          )}
                          
                          {change.impact && (
                            <div className="mt-2">
                              <span className={`text-xs px-2 py-1 rounded-full ${getImpactColor(change.impact)}`}>
                                {change.impact} impact
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                      );
                    })
                  )}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="mt-6 pt-4 border-t border-gray-700 flex items-center justify-between">
              <div className="flex items-center space-x-2 text-sm text-gray-400">
                <Clock className="w-4 h-4" />
                <span>Comparison generated at {new Date().toLocaleString()}</span>
              </div>
              <div className="flex space-x-2">
                <button className="btn-secondary flex items-center space-x-2">
                  <Download className="w-4 h-4" />
                  <span>Export Diff</span>
                </button>
                <button className="btn-primary">Accept Changes</button>
              </div>
            </div>
            </>
          )}
        </div>
      )}
      </div>
    </div>
  );
};

export default VersionCheck;
