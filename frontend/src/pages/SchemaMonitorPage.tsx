import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { API_PATHS, RegisteredApi, SchemaSnapshot, SchemaChange, SchemaComparison } from '../lib/api';
import { 
  ArrowLeft, FileJson, FileText, RefreshCw, GitCompare, ChevronDown, ChevronRight,
  Plus, Minus, AlertTriangle, AlertCircle, Info, Loader2, History, X, Ban
} from 'lucide-react';

interface ScanProgress {
  status: string;
  path: string;
  progress: number;
  total: number;
}

const severityColors = {
  critical: 'bg-red-100 text-red-800 border-red-300',
  high: 'bg-orange-100 text-orange-800 border-orange-300',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  low: 'bg-blue-100 text-blue-800 border-blue-300',
};

const severityIcons = {
  critical: AlertCircle,
  high: AlertTriangle,
  medium: Info,
  low: Info,
};

function SeverityBadge({ severity }: { severity: string }) {
  const colorClass = severityColors[severity as keyof typeof severityColors] || 'bg-gray-100 text-gray-800';
  const Icon = severityIcons[severity as keyof typeof severityIcons] || Info;
  
  return (
    <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-medium border ${colorClass}`}>
      <Icon className="h-3 w-3" />
      <span className="capitalize">{severity}</span>
    </span>
  );
}

function ChangeItem({ change }: { change: SchemaChange }) {
  const [expanded, setExpanded] = useState(false);
  
  const typeColor = change.type === 'added' ? 'text-green-600' : change.type === 'removed' ? 'text-red-600' : 'text-yellow-600';
  
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div 
        className="flex items-center justify-between p-3 bg-gray-50 cursor-pointer hover:bg-gray-100"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center space-x-3">
          <span className={typeColor}>
            {change.type === 'added' && <Plus className="h-4 w-4" />}
            {change.type === 'removed' && <Minus className="h-4 w-4" />}
            {change.type === 'modified' && <RefreshCw className="h-4 w-4" />}
          </span>
          <span className="text-sm font-medium text-gray-900">{change.details}</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500 capitalize">{change.category}</span>
          <SeverityBadge severity={change.severity} />
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </div>
      </div>
      {expanded && change.path && (
        <div className="px-3 py-2 bg-white border-t border-gray-200">
          <code className="text-xs text-gray-600 font-mono">{change.path}</code>
        </div>
      )}
    </div>
  );
}

function SchemaMonitorPage() {
  const { apiId } = useParams<{ apiId: string }>();
  const navigate = useNavigate();
  const [api, setApi] = useState<RegisteredApi | null>(null);
  const [snapshots, setSnapshots] = useState<SchemaSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState<ScanProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersions, setSelectedVersions] = useState<[number, number] | null>(null);
  const [comparison, setComparison] = useState<SchemaComparison | null>(null);
  const [comparing, setComparing] = useState(false);
  const [latestChanges, setLatestChanges] = useState<SchemaChange[]>([]);
  const [, setShowChangesAlert] = useState(false);
  const abortController = useRef<AbortController | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    endpoint: true,
    parameter: true,
    response: true,
    authentication: true,
  });

  useEffect(() => {
    if (apiId) {
      fetchData();
    }
  }, [apiId]);

  const fetchData = async () => {
    if (!apiId) return;
    
    setLoading(true);
    try {
      const response = await fetch(API_PATHS.schemaVersions(Number(apiId)));
      const data = await response.json();
      setApi(data.api);
      setSnapshots(data.snapshots || []);
    } catch (err) {
      setError('Failed to load schema data');
    } finally {
      setLoading(false);
    }
  };

  const handleRescan = async () => {
    if (!apiId) return;
    
    setScanning(true);
    setError(null);
    setScanProgress({ status: 'starting', path: 'Initializing...', progress: 0, total: 1 });
    setLatestChanges([]);
    setShowChangesAlert(false);
    
    abortController.current = new AbortController();
    
    try {
      const response = await fetch(API_PATHS.rescanApi(Number(apiId)), {
        method: 'POST',
        signal: abortController.current.signal
      });
      
      if (!response.ok) {
        const data = await response.json();
        setError(data.error || 'Rescan failed');
        setScanning(false);
        setScanProgress(null);
        return;
      }
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      
      if (!reader) {
        setError('Failed to read response');
        setScanning(false);
        return;
      }
      
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.progress !== undefined) {
                setScanProgress({
                  status: data.status || 'checking',
                  path: data.path || '',
                  progress: data.progress,
                  total: data.total
                });
              }
            } catch {
              continue;
            }
          }
        }
      }
      
      await fetchData();
      
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        setError('Rescan cancelled');
      } else {
        setError('Failed to rescan API');
      }
    } finally {
      setScanning(false);
      setScanProgress(null);
      abortController.current = null;
    }
  };
  
  const handleCancelScan = () => {
    if (abortController.current) {
      abortController.current.abort();
    }
  };

  const handleCompare = async () => {
    if (!apiId || !selectedVersions) return;
    
    setComparing(true);
    setComparison(null);
    
    try {
      const [fromVersion, toVersion] = selectedVersions;
      const response = await fetch(
        `${API_PATHS.compareSchemas(Number(apiId))}?from_version=${fromVersion}&to_version=${toVersion}`
      );
      
      const data = await response.json();
      
      if (!response.ok) {
        setError(data.error || 'Comparison failed');
        return;
      }
      
      setComparison(data);
    } catch (err) {
      setError('Failed to compare schemas');
    } finally {
      setComparing(false);
    }
  };

  const handleDownloadJson = async (version: number) => {
    if (!apiId) return;
    
    try {
      const response = await fetch(API_PATHS.downloadSchema(Number(apiId), version));
      const blob = await response.blob();
      
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `schema_v${version}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download schema');
    }
  };

  const handleDownloadPdf = async (version: number) => {
    if (!apiId) return;
    
    try {
      const response = await fetch(API_PATHS.downloadPdf(Number(apiId), version));
      
      if (!response.ok) {
        setError('PDF not available for this version');
        return;
      }
      
      const blob = await response.blob();
      
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `schema_v${version}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download PDF');
    }
  };

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const getSeveritySummary = (changes: SchemaChange[]) => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    changes.forEach(c => {
      if (counts[c.severity as keyof typeof counts] !== undefined) {
        counts[c.severity as keyof typeof counts]++;
      }
    });
    return counts;
  };

  const groupedChanges = comparison?.changes?.reduce((acc, change) => {
    if (!acc[change.category]) acc[change.category] = [];
    acc[change.category].push(change);
    return acc;
  }, {} as Record<string, SchemaChange[]>) || {};

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!api) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-6xl mx-auto px-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-700">API not found</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex items-center space-x-4 mb-8">
          <button
            onClick={() => navigate('/registry')}
            className="flex items-center space-x-2 text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="h-5 w-5" />
            <span>Back to Registry</span>
          </button>
        </div>

        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Schema Monitor</h1>
            <p className="text-blue-600 font-mono mt-1">{api.base_url}</p>
            <p className="text-gray-600 mt-1">{api.name}</p>
          </div>
          
          <button
            onClick={handleRescan}
            disabled={scanning}
            className="flex items-center space-x-2 bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
          >
            {scanning ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <RefreshCw className="h-5 w-5" />
            )}
            <span>Rescan Schema</span>
          </button>
        </div>

        {error && (
          <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <p className="text-yellow-800">{error}</p>
              <button onClick={() => setError(null)} className="text-yellow-600 hover:text-yellow-800">
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>
        )}

        {scanning && scanProgress && (
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                <span className="font-medium text-blue-800">Scanning: {scanProgress.path}</span>
              </div>
              <button
                onClick={handleCancelScan}
                className="flex items-center space-x-1 text-sm text-red-600 hover:text-red-800"
              >
                <Ban className="h-4 w-4" />
                <span>Cancel</span>
              </button>
            </div>
            <div className="w-full bg-blue-200 rounded-full h-3">
              <div
                className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                style={{ width: `${(scanProgress.progress / scanProgress.total) * 100}%` }}
              />
            </div>
            <p className="text-sm text-blue-600 mt-2">
              Checking path {scanProgress.progress} of {scanProgress.total}
            </p>
          </div>
        )}

        {latestChanges.length > 0 && (
          <div className="mb-6 bg-orange-50 border border-orange-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-orange-800">Changes Since Last Scan</h3>
              <button onClick={() => { setShowChangesAlert(false); setComparison({ from_version: snapshots[0]?.version_number || 1, to_version: snapshots[0]?.version_number || 1, changes: latestChanges, identical: false }); }}>
                <X className="h-5 w-5 text-orange-600" />
              </button>
            </div>
            <div className="flex items-center space-x-4 text-sm">
              {(() => {
                const summary = getSeveritySummary(latestChanges);
                return (
                  <>
                    {summary.critical > 0 && (
                      <span className="flex items-center space-x-1 text-red-700 font-medium">
                        <AlertCircle className="h-4 w-4" />
                        <span>{summary.critical} Critical</span>
                      </span>
                    )}
                    {summary.high > 0 && (
                      <span className="flex items-center space-x-1 text-orange-700 font-medium">
                        <AlertTriangle className="h-4 w-4" />
                        <span>{summary.high} High</span>
                      </span>
                    )}
                    {summary.medium > 0 && (
                      <span className="flex items-center space-x-1 text-yellow-700 font-medium">
                        <Info className="h-4 w-4" />
                        <span>{summary.medium} Medium</span>
                      </span>
                    )}
                    {summary.low > 0 && (
                      <span className="flex items-center space-x-1 text-blue-700 font-medium">
                        <Info className="h-4 w-4" />
                        <span>{summary.low} Low</span>
                      </span>
                    )}
                  </>
                );
              })()}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center space-x-2">
                <History className="h-5 w-5" />
                <span>Schema Versions</span>
              </h2>
              
              {snapshots.length === 0 ? (
                <p className="text-gray-500 text-sm">No schemas scanned yet. Click "Scan" or "Rescan" to discover schemas.</p>
              ) : (
                <div className="space-y-3">
                  {snapshots.map((snapshot) => (
                    <div key={snapshot.id} className="border border-gray-200 rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">Version {snapshot.version_number}</span>
                        <span className="text-xs text-gray-500">
                          {new Date(snapshot.timestamp).toLocaleString()}
                        </span>
                      </div>
                      
                      <div className="flex items-center space-x-2 mt-2">
                        <button
                          onClick={() => handleDownloadJson(snapshot.version_number)}
                          className="flex items-center space-x-1 text-xs text-blue-600 hover:text-blue-800"
                        >
                          <FileJson className="h-3 w-3" />
                          <span>JSON</span>
                        </button>
                        <button
                          onClick={() => handleDownloadPdf(snapshot.version_number)}
                          className="flex items-center space-x-1 text-xs text-green-600 hover:text-green-800"
                        >
                          <FileText className="h-3 w-3" />
                          <span>PDF</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {snapshots.length >= 2 && (
              <div className="bg-white rounded-lg shadow-md p-6 mt-4">
                <h2 className="text-lg font-semibold mb-4 flex items-center space-x-2">
                  <GitCompare className="h-5 w-5" />
                  <span>Compare Versions</span>
                </h2>
                
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">From Version</label>
                    <select
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                      onChange={(e) => setSelectedVersions(prev => prev ? [Number(e.target.value), prev[1]] : [Number(e.target.value), snapshots[0]?.version_number || 1])}
                    >
                      {snapshots.map(s => (
                        <option key={s.version_number} value={s.version_number}>Version {s.version_number}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">To Version</label>
                    <select
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                      onChange={(e) => setSelectedVersions(prev => prev ? [prev[0], Number(e.target.value)] : [snapshots[0]?.version_number || 1, Number(e.target.value)])}
                    >
                      {snapshots.map(s => (
                        <option key={s.version_number} value={s.version_number}>Version {s.version_number}</option>
                      ))}
                    </select>
                  </div>
                  
                  <button
                    onClick={handleCompare}
                    disabled={comparing || !selectedVersions}
                    className="w-full flex items-center justify-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                  >
                    {comparing ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <GitCompare className="h-4 w-4" />
                    )}
                    <span>Compare</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="lg:col-span-2">
            {comparison ? (
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold">
                    Version {comparison.from_version} → {comparison.to_version} Changes
                  </h2>
                  {comparison.identical && (
                    <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                      No Changes
                    </span>
                  )}
                </div>

                {!comparison.identical && comparison.changes && (
                  <div className="space-y-4">
                    {Object.entries(groupedChanges).map(([category, changes]) => (
                      <div key={category} className="border border-gray-200 rounded-lg overflow-hidden">
                        <div
                          className="flex items-center justify-between p-3 bg-gray-50 cursor-pointer hover:bg-gray-100"
                          onClick={() => toggleSection(category)}
                        >
                          <div className="flex items-center space-x-2">
                            {expandedSections[category] ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                            <span className="font-medium capitalize">{category} Changes</span>
                          </div>
                          <span className="text-sm text-gray-500">{changes.length} change(s)</span>
                        </div>
                        
                        {expandedSections[category] && (
                          <div className="p-3 space-y-2">
                            {changes.map((change, idx) => (
                              <ChangeItem key={idx} change={change} />
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-md p-12 text-center">
                <GitCompare className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">Schema Comparison</h3>
                <p className="text-gray-600">
                  Select two versions from the sidebar to compare schema changes
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default SchemaMonitorPage;
