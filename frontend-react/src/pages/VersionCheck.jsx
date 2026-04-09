import { useState, useEffect } from 'react';
import { GitCompare, RefreshCw, Download, ChevronDown, Plus, Minus, FileText, Clock, AlertCircle, CheckCircle, Trash2, Sparkles, Lightbulb, Shield, ChevronRight, Search, Zap, Bot, Edit2, X } from 'lucide-react';
import ApiService from '../services/api';
import { formatAnalysisText } from '../utils/formatAnalysisText';

const buildSemanticChangeDescription = (change) => {
  if (!change || typeof change !== 'object') return null;

  // Prefer explicit backend descriptions if present.
  if (change.details) return change.details;
  if (change.description) return change.description;

  const st = (change.semantic_type || '').toUpperCase();
  const direction = change.direction ? change.direction.toLowerCase() : null;
  const method = change.method ? change.method.toUpperCase() : null;
  const meta = [direction, method].filter(Boolean).join(' ');

  if (st === 'VERSION_BUMP' && change.original_path && change.new_path) {
    return `Endpoint version bump: ${change.original_path} -> ${change.new_path}`;
  }

  // Version bump between normalized endpoints (legacy UI type).
  if (change.type === 'modified' && change.original_path && change.new_path && !change.field) {
    return `Endpoint version bump: ${change.original_path} -> ${change.new_path}`;
  }

  if (change.type === 'added' && change.method) {
    return `Method added: ${change.method.toUpperCase()} ${change.path || ''}`.trim();
  }
  if (change.type === 'removed' && change.method) {
    return `Method removed: ${change.method.toUpperCase()} ${change.path || ''}`.trim();
  }

  // Endpoint added/removed (not method-level).
  if (change.type === 'added' && change.original_path && !change.method) {
    return `Endpoint added: ${change.original_path}`;
  }
  if (change.type === 'removed' && change.original_path && !change.method) {
    return `Endpoint removed: ${change.original_path}`;
  }

  // Schema-level field changes.
  if (change.from && change.to) {
    return `${meta ? `${meta} ` : ''}Field renamed: ${change.from} -> ${change.to}`;
  }

  if (st === 'OPTIONAL_FIELD_ADDED' && change.field) {
    return `${meta ? `${meta} ` : ''}Optional field added: ${change.field}`;
  }

  if (change.required_before !== undefined && change.required_after !== undefined) {
    return `${meta ? `${meta} ` : ''}Required status changed for "${change.field}": ` +
      `${change.required_before} -> ${change.required_after}`;
  }

  if (st === 'PARAMETER_LOCATION_CHANGED' && change.field) {
    const loc = [change.old_in, change.new_in].filter(Boolean).join(' → ');
    return `${meta ? `${meta} ` : ''}Parameter location changed (${loc}): ${change.field}`;
  }

  if (st === 'SENSITIVE_RESPONSE_FIELD_ADDED' && change.field) {
    return `${meta ? `${meta} ` : ''}Critical security: sensitive-like response field added: ${change.field}`;
  }

  if (change.type === 'removed' && change.field) {
    return `${meta ? `${meta} ` : ''}Field removed: ${change.field}`;
  }
  if (change.type === 'added' && change.field) {
    return `${meta ? `${meta} ` : ''}Field added: ${change.field}`;
  }

  if (change.type === 'modified' && change.field) {
    return `${meta ? `${meta} ` : ''}Field changed (likely type/format): ${change.field}`;
  }

  if (change.path) return `Change at ${change.path}`;
  return null;
};

const mapCompareChange = (change) => {
  const description =
    change.details ||
    change.description ||
    buildSemanticChangeDescription(change) ||
    'No description';
  const sev = (change.severity || '').toLowerCase();
  const imp = (change.impact || '').toLowerCase();
  const tierOrder = ['critical', 'high', 'medium', 'low', 'info'];
  let impact = tierOrder.includes(sev)
    ? sev
    : tierOrder.includes(imp)
      ? imp
      : null;
  if (!impact) {
    impact =
      change.breaking_change === 'breaking'
        ? 'high'
        : change.breaking_change === 'non_breaking'
          ? 'low'
          : 'medium';
  }
  return {
    ...change,
    type: change.type || 'unknown',
    path: change.path || change.original_path || '',
    description,
    impact,
  };
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
  const [isEditing, setIsEditing] = useState(false);
  const [editingApi, setEditingApi] = useState(null);
  const [editFormData, setEditFormData] = useState({ name: '', base_url: '', description: '' });

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

  const filteredChanges = comparison?.changes?.filter(change => {
    const q = searchTerm.toLowerCase();
    const matchesSearch =
      !q ||
      (change.path && change.path.toLowerCase().includes(q)) ||
      (change.description && change.description.toLowerCase().includes(q)) ||
      (change.compatibility_rule_name &&
        change.compatibility_rule_name.toLowerCase().includes(q)) ||
      (change.compatibility_rule_id != null &&
        String(change.compatibility_rule_id).includes(q)) ||
      (change.rule_category && change.rule_category.toLowerCase().includes(q));
    return (
      (changeFilter === 'all' || change.type === changeFilter) && matchesSearch
    );
  }) || [];

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

  const handleEditApi = (api) => {
    setEditingApi(api);
    setEditFormData({
      name: api.name,
      base_url: api.base_url,
      description: api.description || ''
    });
    setIsEditing(true);
  };

  const handleUpdateApi = async (e) => {
    e.preventDefault();
    if (!editingApi) return;

    try {
      const response = await ApiService.updateApi(
        editingApi.id,
        editFormData.name,
        editFormData.base_url,
        editFormData.description
      );

      if (response.status === 'success') {
        // Reload APIs
        const apisResponse = await ApiService.getApis();
        if (apisResponse.status === 'success') {
          // Re-apply schema info (reuse logic from useEffect)
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
              } catch (error) { return api; }
            })
          );
          setApis(apisWithSchemas);
        }
        setIsEditing(false);
        setEditingApi(null);
        
        // Success toast
        const successMessage = document.createElement('div');
        successMessage.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
        successMessage.textContent = 'API updated successfully!';
        document.body.appendChild(successMessage);
        setTimeout(() => document.body.removeChild(successMessage), 3000);
      }
    } catch (error) {
      console.error('Update error:', error);
      alert('Failed to update API: ' + error.message);
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
          changes: changes.map((change) =>
            mapCompareChange({
              ...change,
              aiDescription: change.ai_description || null,
              aiImpactAnalysis: change.ai_impact_analysis || null,
              aiFixSuggestion: change.ai_fix_suggestion || null,
            })
          ),
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
            changes: changes.map((change) =>
              mapCompareChange({
                ...change,
                aiDescription: change.ai_description || null,
                aiImpactAnalysis: change.ai_impact_analysis || null,
                aiFixSuggestion: change.ai_fix_suggestion || null,
              })
            ),
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

  const handleExportDiff = async () => {
    if (!comparison) return;
    
    // Create text format of the differences
    let content = `API Diff Export - ${new Date().toLocaleString()}\n`;
    content += `==============================================\n\n`;
    content += `Summary:\n`;
    content += `- Total Changes: ${comparison.summary.total}\n`;
    content += `- Added: ${comparison.summary.added}\n`;
    content += `- Removed: ${comparison.summary.removed}\n`;
    content += `- Modified: ${comparison.summary.modified}\n\n`;
    
    content += `Detailed Changes:\n`;
    content += `----------------------------------------------\n`;
    
    comparison.changes.forEach((change, i) => {
      const label = (change.semantic_type || change.type || '').toString().toUpperCase();
      const pathLine = change.path || change.original_path || '';
      content += `${i + 1}. [${label}] ${pathLine}\n`;
      content += `   ${change.description}\n`;
      if (change.impact) content += `   Impact: ${change.impact}\n`;
      if (change.method) content += `   Method: ${change.method}\n`;
      if (change.direction) content += `   Direction: ${change.direction}\n`;
      if (change.compatibility_rule_id != null) {
        content += `   Rule: #${change.compatibility_rule_id}${change.compatibility_rule_name ? ` (${change.compatibility_rule_name})` : ''}\n`;
      }
      if (change.rule_category) content += `   Category: ${change.rule_category}\n`;
      if (change.security_issue) content += `   Security issue: yes\n`;
      if (change.breaking_change) content += `   Compatibility: ${change.breaking_change}\n`;
      if (change.original_path && change.new_path && change.semantic_type === 'VERSION_BUMP') {
        content += `   Paths: ${change.original_path} -> ${change.new_path}\n`;
      }
      if (change.from && change.to) {
        content += `   Rename: ${change.from} -> ${change.to}\n`;
      }
      if (change.field && change.semantic_type === 'FIELD_TYPE_CHANGED') {
        content += `   Field: ${change.field}\n`;
      }
      if (change.aiDescription) content += `   AI Note: ${change.aiDescription}\n`;
      content += `\n`;
    });
    
    const filename = `api-diff-${new Date().toISOString().slice(0,10)}.txt`;
    
    // Save to backend Reports Registry
    try {
      await ApiService.saveReport(
        'diff',
        filename,
        content,
        'txt',
        selectedApi ? selectedApi.id : null
      );
      
      const successMessage = document.createElement('div');
      successMessage.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
      successMessage.textContent = 'Report saved to your dashboard!';
      document.body.appendChild(successMessage);
      setTimeout(() => document.body.removeChild(successMessage), 3000);
    } catch (err) {
      console.error('Failed to save report to backend:', err);
    }
    
    // Create blob and download link
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
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
    switch ((impact || '').toLowerCase()) {
      case 'critical':
        return 'text-rose-200 bg-rose-500/20 border border-rose-500/40';
      case 'high':
        return 'text-red-300 bg-red-500/15 border border-red-500/35';
      case 'medium':
        return 'text-amber-200 bg-amber-500/15 border border-amber-500/30';
      case 'low':
        return 'text-emerald-300 bg-emerald-500/15 border border-emerald-500/30';
      case 'info':
        return 'text-slate-300 bg-slate-600/20 border border-slate-500/35';
      default:
        return 'text-gray-400 bg-gray-500/10 border border-gray-600/30';
    }
  };

  const formatDirectionBadge = (dir) => {
    if (!dir || typeof dir !== 'string') return null;
    const d = dir.toLowerCase();
    const label =
      d === 'request'
        ? 'Request'
        : d === 'response'
          ? 'Response'
          : d === 'parameter'
            ? 'Parameter'
            : dir.charAt(0).toUpperCase() + dir.slice(1);
    const cls =
      d === 'request'
        ? 'bg-sky-500/15 text-sky-200 border-sky-500/35'
        : d === 'response'
          ? 'bg-violet-500/15 text-violet-200 border-violet-500/35'
          : d === 'parameter'
            ? 'bg-amber-500/15 text-amber-200 border-amber-500/35'
            : 'bg-slate-600/30 text-slate-200 border-slate-500/40';
    return { label, cls };
  };

  const categoryBadgeClass = (category) => {
    if (!category) return 'bg-slate-600/25 text-slate-200 border-slate-500/40';
    const c = category.toLowerCase();
    if (c.includes('security')) return 'bg-rose-950/50 text-rose-200 border-rose-500/40';
    if (c.includes('violation')) return 'bg-orange-950/40 text-orange-200 border-orange-500/35';
    if (c.includes('additive') || c.includes('compatible'))
      return 'bg-teal-950/40 text-teal-200 border-teal-500/35';
    return 'bg-indigo-950/40 text-indigo-200 border-indigo-500/35';
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

  /**
   * Extract a short version label from a schema_url.
   * e.g. http://api.com/v2/openapi.json → "v2"
   *      http://api.com/openapi.json    → "/openapi.json"
   */
  const getVersionLabel = (schemaUrl) => {
    if (!schemaUrl) return null;
    try {
      const path = new URL(schemaUrl).pathname;
      const match = path.match(/\/(v\d+)(?:\/|$)/i);
      if (match) return match[1];
      return path;
    } catch {
      return schemaUrl;
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
                  <span className="text-gray-400">Schemas Found</span>
                  <span className="text-white font-medium">{api.schemas?.length || 0}</span>
                </div>
                {/* Per-snapshot version pills */}
                {api.schemas && api.schemas.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {api.schemas.map((schema) => {
                      const label = getVersionLabel(schema.schema_url);
                      return (
                        <span
                          key={schema.version_number}
                          title={schema.schema_url || `Snapshot #${schema.version_number}`}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
                        >
                          <span className="text-indigo-400">#{schema.version_number}</span>
                          {label && <>
                            <span className="text-gray-500">&middot;</span>
                            <span>{label}</span>
                          </>}
                        </span>
                      );
                    })}
                  </div>
                )}
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
                <button
                  onClick={() => handleEditApi(api)}
                  className="flex-1 min-w-[100px] btn-secondary flex items-center justify-center space-x-2"
                  title="Edit API details (e.g., change v1 to v2)"
                >
                  <Edit2 className="w-4 h-4" />
                  <span>Edit</span>
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
                        v{schema.version_number}{schema.schema_url ? ` — ${getVersionLabel(schema.schema_url)}` : ''}
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
                        v{schema.version_number}{schema.schema_url ? ` — ${getVersionLabel(schema.schema_url)}` : ''}
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
                      const directionBadge = change.direction
                        ? formatDirectionBadge(change.direction)
                        : null;
                      return (
                    <div key={originalIndex} className="bg-slate-900/50 p-4 rounded-lg">
                      <div className="flex items-start space-x-3">
                        <div className="mt-1">
                          {getChangeIcon(change.type)}
                        </div>
                        <div className="flex-1">
                          <div className="flex flex-wrap items-center gap-2 mb-2">
                            <span className={`text-sm font-medium ${getChangeColor(change.type)}`}>
                              {change.semantic_type
                                ? change.semantic_type.replace(/_/g, ' ')
                                : change.type.charAt(0).toUpperCase() + change.type.slice(1)}
                            </span>
                            {directionBadge && (
                              <span
                                className={`text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full border ${directionBadge.cls}`}
                              >
                                {directionBadge.label}
                              </span>
                            )}
                            {change.rule_category && (
                              <span
                                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${categoryBadgeClass(change.rule_category)}`}
                              >
                                {change.rule_category}
                              </span>
                            )}
                            {(change.breaking === true || change.breaking_change === 'breaking') && (
                              <span className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full bg-red-950/60 text-red-200 border border-red-500/50">
                                Breaking
                              </span>
                            )}
                            {change.security_issue && (
                              <span className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full bg-rose-950/70 text-rose-100 border border-rose-400/60">
                                Security
                              </span>
                            )}
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
                          
                          {(change.compatibility_rule_id != null || change.compatibility_rule_name) && (
                            <div className="mt-1 flex flex-wrap items-center gap-2">
                              <span className="text-[10px] uppercase tracking-wide text-slate-500">Rule ID</span>
                              <code className="text-xs text-cyan-300/90 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-800/40">
                                {change.compatibility_rule_id != null ? `#${change.compatibility_rule_id}` : ''}
                                {change.compatibility_rule_name
                                  ? `${change.compatibility_rule_id != null ? ' · ' : ''}${change.compatibility_rule_name}`
                                  : ''}
                              </code>
                            </div>
                          )}
                          {change.impact && (
                            <div className="mt-2">
                              <span className={`text-xs px-2 py-1 rounded-full font-medium capitalize ${getImpactColor(change.impact)}`}>
                                {change.impact} severity
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
                <button onClick={handleExportDiff} className="btn-secondary flex items-center space-x-2">
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

        {/* Edit Modal */}
        {isEditing && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div className="glass-card w-full max-w-lg p-6 relative">
              <button 
                onClick={() => setIsEditing(false)}
                className="absolute top-4 right-4 text-gray-400 hover:text-white"
              >
                <X className="w-6 h-6" />
              </button>
              
              <h2 className="text-2xl font-bold text-white mb-6">Edit API Details</h2>
              <p className="text-sm text-gray-400 mb-6">
                Update the Base URL (e.g., to /v2) to track the evolution of this API as new versions.
              </p>
              
              <form onSubmit={handleUpdateApi} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">API Name</label>
                  <input
                    type="text"
                    required
                    value={editFormData.name}
                    onChange={(e) => setEditFormData({...editFormData, name: e.target.value})}
                    className="input-field"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Base URL</label>
                  <input
                    type="url"
                    required
                    value={editFormData.base_url}
                    onChange={(e) => setEditFormData({...editFormData, base_url: e.target.value})}
                    placeholder="https://api.example.com/v2"
                    className="input-field"
                  />
                  <p className="text-[10px] text-gray-500 mt-1 italic">
                    Change this to point to a new versioned endpoint to trigger a comparative scan.
                  </p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Description (Optional)</label>
                  <textarea
                    value={editFormData.description}
                    onChange={(e) => setEditFormData({...editFormData, description: e.target.value})}
                    className="input-field h-24"
                  />
                </div>
                
                <div className="flex space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setIsEditing(false)}
                    className="flex-1 btn-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 btn-primary"
                  >
                    Save Changes
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VersionCheck;
