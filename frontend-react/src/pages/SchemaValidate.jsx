import { useState, useEffect } from 'react';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Loader2,
  ChevronDown,
  FileText,
  AlertCircle,
  Zap,
  RefreshCw,
  Bot,
} from 'lucide-react';
import ApiService from '../services/api';
import { formatAnalysisText } from '../utils/formatAnalysisText';

const SchemaValidate = () => {
  const [selectedApi, setSelectedApi] = useState('');
  const [apis, setApis] = useState([]);
  const [isValidating, setIsValidating] = useState(false);
  const [validationResults, setValidationResults] = useState(null);
  const [error, setError] = useState('');
  const [analyzingIssueIndex, setAnalyzingIssueIndex] = useState(null);

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
      } catch (err) {
        console.error('Failed to load APIs:', err);
      }
    };

    loadApis();
  }, []);

  const buildIssueFromTest = (test) => {
    const parts = [];
    if (test.error) parts.push(test.error);
    if (test.status_mismatch && test.actual_status != null) {
      parts.push(
        `HTTP ${test.actual_status}` +
          (test.expected_status != null ? ` (spec default ${test.expected_status})` : '')
      );
    }
    if (test.schema_mismatch) parts.push('Response JSON does not match declared schema');
    const message =
      parts.length > 0
        ? parts.join(' · ')
        : `Validation failed for ${test.method} ${test.path}`;
    return {
      severity: test.status_mismatch ? 'error' : 'warning',
      message,
      path: `${test.method} ${test.path}`,
      line: 1,
      rawTest: { ...test },
      detailedAnalysis: null,
    };
  };

  const handleValidate = async () => {
    if (!selectedApi) return;

    setIsValidating(true);
    setValidationResults(null);
    setError('');
    setAnalyzingIssueIndex(null);

    try {
      const schemaResponse = await ApiService.getLatestSchema(parseInt(selectedApi, 10));

      if (schemaResponse.status === 'success') {
        const api = apis.find((a) => a.id.toString() === selectedApi);

        const validationResponse = await ApiService.validateRuntime(
          api.base_url,
          schemaResponse.schema.schema_json
        );

        if (validationResponse.status === 'success') {
          const result = validationResponse.validation_result;
          const tests = result.endpoint_tests || [];
          const passed = tests.filter((t) => t.validation_passed);
          const failed = tests.filter((t) => !t.validation_passed);
          const pct =
            result.tested_endpoints > 0
              ? Math.round((result.passed_endpoints / result.tested_endpoints) * 100)
              : null;

          setValidationResults({
            status: result.overall_status === 'passed' ? 'success' : 'warning',
            overall: pct != null ? `${pct}%` : '—',
            baseUrl: api.base_url,
            issues: failed.map((test) => buildIssueFromTest(test)),
            passedEndpoints: passed.map((test) => ({
              method: test.method,
              path: test.path,
              url: test.url,
              actual_status: test.actual_status,
              response_time_ms: test.response_time_ms,
            })),
            stats: {
              totalChecks: result.tested_endpoints,
              passed: result.passed_endpoints,
              warnings: tests.filter((t) => !t.validation_passed && !t.status_mismatch).length,
              errors: tests.filter((t) => t.status_mismatch).length,
            },
            validatedAt: result.validation_timestamp,
          });
        } else {
          setError(validationResponse.error || 'Runtime validation failed');
        }
      } else {
        setError(schemaResponse.error || 'No schema found for this API');
      }
    } catch (err) {
      setError(err.message || 'Error during validation. Please try again.');
      console.error('Validation error:', err);
    } finally {
      setIsValidating(false);
    }
  };

  const handleAnalyzeIssue = async (issueIndex) => {
    if (!validationResults?.baseUrl) return;
    const issue = validationResults.issues[issueIndex];
    if (!issue?.rawTest) return;

    setAnalyzingIssueIndex(issueIndex);
    try {
      const response = await ApiService.analyzeRuntimeFailure(
        validationResults.baseUrl,
        issue.rawTest
      );
      if (response.status === 'success') {
        setValidationResults((prev) => {
          if (!prev) return prev;
          const nextIssues = prev.issues.map((it, i) =>
            i === issueIndex ? { ...it, detailedAnalysis: response.analysis } : it
          );
          return { ...prev, issues: nextIssues };
        });
      } else {
        throw new Error(response.error || 'Failed to analyze');
      }
    } catch (err) {
      console.error('Runtime analyze error:', err);
      setValidationResults((prev) => {
        if (!prev) return prev;
        const nextIssues = prev.issues.map((it, i) =>
          i === issueIndex ? { ...it, detailedAnalysis: `Error: ${err.message}` } : it
        );
        return { ...prev, issues: nextIssues };
      });
    } finally {
      setAnalyzingIssueIndex(null);
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

  const selectedApiData = apis.find((api) => api.id.toString() === selectedApi);

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Schema Validate</h1>
          <p className="text-gray-400">
            Validate API schemas against industry standards and best practices
          </p>
        </div>

        <div className="glass-card p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Select API to Validate
              </label>
              <div className="relative">
                <select
                  value={selectedApi}
                  onChange={(e) => setSelectedApi(e.target.value)}
                  className="input-field pr-10 appearance-none w-full md:w-96"
                >
                  {apis.map((api) => (
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

        {error && (
          <div className="glass-card p-4 mb-6 border-l-4 border-red-500">
            <div className="flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-red-400" />
              <span className="text-red-400">{error}</span>
            </div>
          </div>
        )}

        {validationResults && (
          <div className="space-y-6">
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

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-slate-900/50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-white mb-1">
                    {validationResults.stats.totalChecks}
                  </div>
                  <div className="text-xs text-gray-400">Total Checks</div>
                </div>
                <div className="bg-slate-900/50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-green-500 mb-1">
                    {validationResults.stats.passed}
                  </div>
                  <div className="text-xs text-gray-400">Passed</div>
                </div>
                <div className="bg-slate-900/50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-yellow-400 mb-1">
                    {validationResults.stats.warnings}
                  </div>
                  <div className="text-xs text-gray-400">Warnings</div>
                </div>
                <div className="bg-slate-900/50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-red-400 mb-1">
                    {validationResults.stats.errors}
                  </div>
                  <div className="text-xs text-gray-400">Errors</div>
                </div>
              </div>

              {validationResults.passedEndpoints.length > 0 && (
                <div className="mb-8">
                  <h3 className="text-lg font-semibold text-white mb-3">Validated endpoints (passed)</h3>
                  <p className="text-xs text-gray-500 mb-3">
                    Operations that matched the declared contract for the checks performed.
                  </p>
                  <ul className="space-y-2 max-h-64 overflow-y-auto pr-1">
                    {validationResults.passedEndpoints.map((ep, idx) => (
                      <li
                        key={`${ep.method}-${ep.path}-${idx}`}
                        className="flex flex-wrap items-center gap-2 bg-slate-900/40 border border-slate-700/50 rounded-lg px-3 py-2 text-sm"
                      >
                        <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                        <code className="text-cyan-200/90 text-xs font-mono">
                          {ep.method} {ep.path}
                        </code>
                        {ep.actual_status != null && (
                          <span className="text-xs text-gray-500">HTTP {ep.actual_status}</span>
                        )}
                        {ep.response_time_ms != null && (
                          <span className="text-xs text-gray-500 ml-auto">
                            {Math.round(ep.response_time_ms)} ms
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div>
                <h3 className="text-lg font-semibold text-white mb-4">Issues found</h3>
                {validationResults.issues.length === 0 ? (
                  <p className="text-sm text-gray-400">
                    No issues — all probed endpoints matched the spec for the checks performed.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {validationResults.issues.map((issue, index) => (
                      <div key={index} className="bg-dark-primary/50 p-4 rounded-lg">
                        <div className="flex items-start space-x-3">
                          <div className="mt-1">{getSeverityIcon(issue.severity)}</div>
                          <div className="flex-1 min-w-0">
                            <div className="flex flex-wrap items-center gap-2 mb-2">
                              <span
                                className={`font-medium capitalize ${
                                  issue.severity === 'error'
                                    ? 'text-red-400'
                                    : issue.severity === 'warning'
                                      ? 'text-yellow-400'
                                      : 'text-blue-400'
                                }`}
                              >
                                {issue.severity}
                              </span>
                              <code className="text-xs text-gray-400 bg-slate-800/50 px-2 py-1 rounded">
                                {issue.path}
                              </code>
                              <div className="ml-auto flex items-center">
                                <button
                                  type="button"
                                  onClick={() => handleAnalyzeIssue(index)}
                                  disabled={analyzingIssueIndex === index}
                                  className="text-xs flex items-center space-x-1.5 bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 px-3 py-1.5 rounded-md border border-purple-500/30 transition-colors disabled:opacity-50 font-medium"
                                >
                                  {analyzingIssueIndex === index ? (
                                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                  ) : (
                                    <Zap className="w-3.5 h-3.5" />
                                  )}
                                  <span>Analyze</span>
                                </button>
                              </div>
                            </div>
                            <p className="text-gray-300 text-sm mb-2">{issue.message}</p>

                            {issue.detailedAnalysis && (
                              <div className="mt-4 bg-slate-950/80 rounded-lg p-5 border border-purple-500/30 shadow-inner">
                                <div className="flex items-center space-x-2 mb-3 border-b border-purple-500/20 pb-2">
                                  <Bot className="w-5 h-5 text-purple-400" />
                                  <h4 className="text-sm font-semibold text-purple-300 tracking-wide">
                                    AI developer analysis
                                  </h4>
                                </div>
                                <div className="text-gray-300">{formatAnalysisText(issue.detailedAnalysis)}</div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="mt-6 pt-4 border-t border-gray-700">
                <div className="flex items-center justify-between text-sm text-gray-400">
                  <span>Validated at: {new Date(validationResults.validatedAt).toLocaleString()}</span>
                  <button type="button" className="text-accent-blue hover:text-blue-400">
                    Export Report
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

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
