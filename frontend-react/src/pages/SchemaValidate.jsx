import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Loader2, ChevronDown, FileText } from 'lucide-react';
import ApiService from '../services/api';

const SchemaValidate = () => {
  const [selectedApi, setSelectedApi] = useState('');
  const [apis, setApis] = useState([]);
  const [isValidating, setIsValidating] = useState(false);
  const [validationResults, setValidationResults] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadApis = async () => {
      try {
        const response = await ApiService.getApis();
        if (response.status === 'success') {
          setApis(response.apis);
          if (response.apis.length > 0) {
            setSelectedApi(response.apis[0].id.toString());
          }
        }
      } catch (error) {
        console.error('Failed to load APIs:', error);
      }
    };

    loadApis();
  }, []);

  const handleValidate = async () => {
    if (!selectedApi) return;
    
    setIsValidating(true);
    setValidationResults(null);
    setError('');
    
    try {
      // Get the latest schema for the selected API
      const schemaResponse = await ApiService.getLatestSchema(parseInt(selectedApi));
      
      if (schemaResponse.status === 'success') {
        const api = apis.find(a => a.id.toString() === selectedApi);
        
        // Perform runtime validation
        const validationResponse = await ApiService.validateRuntime(
          api.base_url,
          schemaResponse.schema.schema_json
        );
        
        if (validationResponse.status === 'success') {
          const result = validationResponse.validation_result;
          
          // Transform the runtime validation result to match our UI format
          setValidationResults({
            status: result.overall_status === 'passed' ? 'success' : 'warning',
            overall: `${Math.round((result.passed_endpoints / result.tested_endpoints) * 100)}%`,
            issues: result.endpoint_tests
              .filter(test => !test.validation_passed)
              .map(test => ({
                severity: test.status_mismatch ? 'error' : 'warning',
                message: test.error || `Validation failed for ${test.method} ${test.path}`,
                path: test.path,
                line: 1
              })),
            stats: {
              totalChecks: result.tested_endpoints,
              passed: result.passed_endpoints,
              warnings: result.endpoint_tests.filter(t => !t.validation_passed && !t.status_mismatch).length,
              errors: result.endpoint_tests.filter(t => t.status_mismatch).length
            },
            validatedAt: result.validation_timestamp
          });
        } else {
          setError(validationResponse.error || 'Runtime validation failed');
        }
      } else {
        setError(schemaResponse.error || 'No schema found for this API');
      }
    } catch (error) {
      setError(error.message || 'Error during validation. Please try again.');
      console.error('Validation error:', error);
    } finally {
      setIsValidating(false);
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'error':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
      case 'info':
        return <CheckCircle className="w-4 h-4 text-blue-400" />;
      default:
        return <CheckCircle className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'success':
        return 'text-accent-green';
      case 'warning':
        return 'text-yellow-400';
      case 'error':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  const selectedApiData = apis.find(api => api.id === selectedApi);

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Schema Validate</h1>
          <p className="text-gray-400">Validate API schemas against industry standards and best practices</p>
        </div>

        {/* API Selection */}
        <div className="glass-card p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Select API to Validate</label>
              <div className="relative">
                <select
                  value={selectedApi}
                  onChange={(e) => setSelectedApi(e.target.value)}
                  className="input-field pr-10 appearance-none w-full md:w-96"
                >
                  {apis.map(api => (
                    <option key={api.id} value={api.id}>
                      {api.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-3 w-5 h-5 text-gray-400 pointer-events-none" />
              </div>
            </div>
            <button
              onClick={handleValidate}
              disabled={!selectedApi || isValidating}
              className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isValidating ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <CheckCircle className="w-5 h-5" />
              )}
              <span>{isValidating ? 'Validating...' : 'Validate Schema'}</span>
            </button>
          </div>

          {selectedApiData && (
            <div className="flex items-center space-x-4 text-sm text-gray-400">
              <span className="flex items-center space-x-1">
                <FileText className="w-4 h-4" />
                <span>{selectedApiData.base_url}</span>
              </span>
              <span>•</span>
              <span>Added: {new Date(selectedApiData.date_added).toLocaleDateString()}</span>
            </div>
          )}
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

        {/* Validation Results */}
        {validationResults && (
          <div className="space-y-6">
            {/* Overall Score */}
            <div className="glass-card p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white">Validation Results</h2>
                <div className="flex items-center space-x-2">
                  <span className={`text-2xl font-bold ${getStatusColor(validationResults.status)}`}>
                    {validationResults.overall}
                  </span>
                  <span className="text-gray-400">Score</span>
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-slate-900/50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-white mb-1">{validationResults.stats.totalChecks}</div>
                  <div className="text-xs text-gray-400">Total Checks</div>
                </div>
                <div className="bg-slate-900/50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-green-500 mb-1">{validationResults.stats.passed}</div>
                  <div className="text-xs text-gray-400">Passed</div>
                </div>
                <div className="bg-slate-900/50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-yellow-400 mb-1">{validationResults.stats.warnings}</div>
                  <div className="text-xs text-gray-400">Warnings</div>
                </div>
                <div className="bg-slate-900/50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-red-400 mb-1">{validationResults.stats.errors}</div>
                  <div className="text-xs text-gray-400">Errors</div>
                </div>
              </div>

              {/* Issues List */}
              <div>
                <h3 className="text-lg font-semibold text-white mb-4">Issues Found</h3>
                <div className="space-y-3">
                  {validationResults.issues.map((issue, index) => (
                    <div key={index} className="bg-dark-primary/50 p-4 rounded-lg">
                      <div className="flex items-start space-x-3">
                        <div className="mt-1">
                          {getSeverityIcon(issue.severity)}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between mb-2">
                            <span className={`font-medium capitalize ${
                              issue.severity === 'error' ? 'text-red-400' :
                              issue.severity === 'warning' ? 'text-yellow-400' :
                              'text-blue-400'
                            }`}>
                              {issue.severity}
                            </span>
                            <span className="text-xs text-gray-400">Line {issue.line}</span>
                          </div>
                          <p className="text-gray-300 text-sm mb-2">{issue.message}</p>
                          <code className="text-xs text-gray-400 bg-slate-800/50 px-2 py-1 rounded">
                            {issue.path}
                          </code>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Validation Timestamp */}
              <div className="mt-6 pt-4 border-t border-gray-700">
                <div className="flex items-center justify-between text-sm text-gray-400">
                  <span>Validated at: {new Date(validationResults.validatedAt).toLocaleString()}</span>
                  <button className="text-accent-blue hover:text-blue-400">
                    Export Report
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!validationResults && !isValidating && (
          <div className="glass-card p-12 text-center">
            <CheckCircle className="w-16 h-16 text-gray-500 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Ready to Validate</h3>
            <p className="text-gray-400">Select an API and click validate to check schema compliance</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SchemaValidate;
