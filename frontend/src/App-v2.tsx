import { useState } from 'react';
import { API_PATHS } from './lib/api';

// Enhanced interfaces for REST Parameter Discovery v2
interface V2InferenceResult {
  url: string;
  method: string;
  parameters: V2Parameter[];
  meta: {
    total_parameters: number;
    execution_time_ms: number;
    discovery_version: string;
    orchestration_phases: string[];
    v2_features: {
      differential_candidates: number;
      location_testing: number;
      framework_detected: boolean;
      weighted_scoring: boolean;
      enhanced_classification: boolean;
    };
    baseline_fingerprint?: {
      status: number;
      body_hash: string;
      body_length: number;
      headers_normalized: Record<string, string>;
      response_time_ms: number;
    };
    endpoint_classification?: {
      endpoint_type: string;
      confidence: number;
      signals: {
        baseline_status?: number;
        differential_candidates?: number;
        framework_signal?: any;
      };
    };
    differential_analysis?: {
      candidates: Array<{
        name: string;
        diffs: Array<{
          status_changed: boolean;
          hash_changed: boolean;
          length_delta_percent: number;
        }>;
        provisional_score: number;
        evidence: Record<string, any>;
        sources: string[];
      }>;
    };
    location_resolution?: Record<string, {
      best_location: string;
      location_confidence: number;
      location_evidence: Record<string, any>;
    }>;
    confidence_scoring?: Record<string, {
      confidence: number;
      location: string;
      evidence: Record<string, any>;
      sources: string[];
    }>;
  };
}

interface V2Parameter {
  name: string;
  type: string;
  location: string;
  required: boolean;
  confidence: number;
  evidence: Record<string, any>;
  sources: string[];
}

interface V2Request {
  url: string;
  method: string;
  auth?: {
    type: 'none' | 'bearer' | 'apikey';
    token?: string;
    api_key?: string;
    header_name?: string;
  };
  headers?: Record<string, string>;
  seed_body?: any;
  content_type_override?: string;
  timeout_seconds: number;
}

function AppV2() {
  const [url, setUrl] = useState('');
  const [method, setMethod] = useState('POST');
  const [timeLimit, setTimeLimit] = useState(30);
  const [results, setResults] = useState<V2InferenceResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showResults, setShowResults] = useState(false);
  
  // V2 specific state
  const [authType, setAuthType] = useState<'none' | 'bearer' | 'apikey'>('none');
  const [authToken, setAuthToken] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [headerName, setHeaderName] = useState('');
  const [customHeaders, setCustomHeaders] = useState('');
  const [seedBody, setSeedBody] = useState('');
  const [contentType, setContentType] = useState('');
  const [enableV2, setEnableV2] = useState(true);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setShowResults(false);

    try {
      // Build V2 request payload
      const requestPayload: V2Request = {
        url,
        method,
        timeout_seconds: timeLimit,
        auth: authType !== 'none' ? {
          type: authType,
          token: authToken || undefined,
          api_key: apiKey || undefined,
          header_name: headerName || undefined
        } : undefined,
        headers: customHeaders ? JSON.parse(customHeaders) : undefined,
        seed_body: seedBody ? JSON.parse(seedBody) : undefined,
        content_type_override: contentType || undefined
      };

      const response = await fetch(API_PATHS.infer, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestPayload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: V2InferenceResult = await response.json();
      setResults(data);
      setShowResults(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSpecGeneration = async () => {
    if (!url) return;
    
    setIsLoading(true);
    setError(null);

    try {
      const requestPayload: V2Request = {
        url,
        method,
        timeout_seconds: timeLimit,
        auth: authType !== 'none' ? {
          type: authType,
          token: authToken || undefined,
          api_key: apiKey || undefined,
          header_name: headerName || undefined
        } : undefined,
        headers: customHeaders ? JSON.parse(customHeaders) : undefined,
        seed_body: seedBody ? JSON.parse(seedBody) : undefined,
        content_type_override: contentType || undefined
      };

      const response = await fetch(API_PATHS.spec, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestPayload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const specData = await response.json();
      
      // Download the OpenAPI spec
      const blob = new Blob([JSON.stringify(specData, null, 2)], { type: 'application/json' });
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = 'openapi-spec.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            REST Parameter Discovery v2
          </h1>
          <p className="text-gray-600 mb-6">
            Enhanced API parameter discovery with differential analysis, location resolution, and weighted confidence scoring
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-1">
                API Endpoint URL
              </label>
              <input
                type="url"
                id="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="https://api.example.com/endpoint"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="method" className="block text-sm font-medium text-gray-700 mb-1">
                  HTTP Method
                </label>
                <select
                  id="method"
                  value={method}
                  onChange={(e) => setMethod(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                  <option value="PUT">PUT</option>
                  <option value="DELETE">DELETE</option>
                  <option value="PATCH">PATCH</option>
                </select>
              </div>

              <div>
                <label htmlFor="timeLimit" className="block text-sm font-medium text-gray-700 mb-1">
                  Time Limit (seconds)
                </label>
                <input
                  type="number"
                  id="timeLimit"
                  value={timeLimit}
                  onChange={(e) => setTimeLimit(Number(e.target.value))}
                  min="1"
                  max="60"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* V2 Enhanced Options */}
            <div className="border-t pt-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Enhanced v2 Options</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={enableV2}
                      onChange={(e) => setEnableV2(e.target.checked)}
                      className="mr-2"
                    />
                    <span className="text-sm font-medium text-gray-700">Enable v2 Discovery</span>
                  </label>
                  <p className="text-xs text-gray-500 mt-1">Use enhanced differential analysis and weighted scoring</p>
                </div>

                <div>
                  <label htmlFor="authType" className="block text-sm font-medium text-gray-700 mb-1">
                    Authentication Type
                  </label>
                  <select
                    id="authType"
                    value={authType}
                    onChange={(e) => setAuthType(e.target.value as 'none' | 'bearer' | 'apikey')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="none">None</option>
                    <option value="bearer">Bearer Token</option>
                    <option value="apikey">API Key</option>
                  </select>
                </div>

                {authType === 'bearer' && (
                  <div>
                    <label htmlFor="authToken" className="block text-sm font-medium text-gray-700 mb-1">
                      Bearer Token
                    </label>
                    <input
                      type="text"
                      id="authToken"
                      value={authToken}
                      onChange={(e) => setAuthToken(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="your-bearer-token"
                    />
                  </div>
                )}

                {authType === 'apikey' && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="apiKey" className="block text-sm font-medium text-gray-700 mb-1">
                        API Key
                      </label>
                      <input
                        type="text"
                        id="apiKey"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="your-api-key"
                      />
                    </div>
                    <div>
                      <label htmlFor="headerName" className="block text-sm font-medium text-gray-700 mb-1">
                        Header Name
                      </label>
                      <input
                        type="text"
                        id="headerName"
                        value={headerName}
                        onChange={(e) => setHeaderName(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="X-API-Key"
                      />
                    </div>
                  </div>
                )}

                <div>
                  <label htmlFor="customHeaders" className="block text-sm font-medium text-gray-700 mb-1">
                    Custom Headers (JSON)
                  </label>
                  <textarea
                    id="customHeaders"
                    value={customHeaders}
                    onChange={(e) => setCustomHeaders(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={2}
                    placeholder='{"Content-Type": "application/json"}'
                  />
                </div>

                <div>
                  <label htmlFor="seedBody" className="block text-sm font-medium text-gray-700 mb-1">
                    Seed Body (JSON)
                  </label>
                  <textarea
                    id="seedBody"
                    value={seedBody}
                    onChange={(e) => setSeedBody(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={2}
                    placeholder='{"example": "data"}'
                  />
                </div>

                <div>
                  <label htmlFor="contentType" className="block text-sm font-medium text-gray-700 mb-1">
                    Content-Type Override
                  </label>
                  <input
                    type="text"
                    id="contentType"
                    value={contentType}
                    onChange={(e) => setContentType(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="application/json"
                  />
                </div>
              </div>
            </div>

            <div className="flex space-x-4">
              <button
                type="submit"
                disabled={isLoading || !url}
                className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Discovering...' : 'Discover Parameters'}
              </button>
              
              <button
                type="button"
                onClick={handleSpecGeneration}
                disabled={isLoading || !url}
                className="flex-1 bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Generating...' : 'Generate OpenAPI Spec'}
              </button>
            </div>
          </form>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-800">{error}</p>
            </div>
          )}

          {showResults && results && (
            <div className="mt-6 border-t pt-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Discovery Results</h2>
              
              {/* V2 Enhanced Results Display */}
              <div className="bg-gray-50 rounded-lg p-4 mb-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Discovery Summary</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="font-medium">Version:</span>
                    <span className="ml-2">{results.meta.discovery_version}</span>
                  </div>
                  <div>
                    <span className="font-medium">Parameters:</span>
                    <span className="ml-2">{results.meta.total_parameters}</span>
                  </div>
                  <div>
                    <span className="font-medium">Execution Time:</span>
                    <span className="ml-2">{results.meta.execution_time_ms}ms</span>
                  </div>
                  <div>
                    <span className="font-medium">V2 Features:</span>
                    <span className="ml-2">
                      {results.meta.v2_features.framework_detected ? '✓' : '✗'} Framework
                      {results.meta.v2_features.weighted_scoring ? '✓' : '✗'} Weighted
                      {results.meta.v2_features.enhanced_classification ? '✓' : '✗'} Enhanced
                    </span>
                  </div>
                </div>
              </div>

              {/* Parameters Table */}
              {results.parameters.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Discovered Parameters</h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full bg-white border border-gray-200 rounded-md">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Name
                          </th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Type
                          </th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Location
                          </th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Required
                          </th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Confidence
                          </th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Sources
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {results.parameters.map((param, index) => (
                          <tr key={index}>
                            <td className="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
                              {param.name}
                            </td>
                            <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                              {param.type}
                            </td>
                            <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                              {param.location}
                            </td>
                            <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                              <span className={`px-2 py-1 rounded-full text-xs ${
                                param.required 
                                  ? 'bg-red-100 text-red-800' 
                                  : 'bg-green-100 text-green-800'
                              }`}>
                                {param.required ? 'Required' : 'Optional'}
                              </span>
                            </td>
                            <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                              <div className="flex items-center">
                                <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                                  <div
                                    className="bg-blue-600 h-2 rounded-full"
                                    style={{ width: `${param.confidence * 100}%` }}
                                  />
                                </div>
                                <span className="text-xs">{(param.confidence * 100).toFixed(0)}%</span>
                              </div>
                            </td>
                            <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                              <div className="flex flex-wrap gap-1">
                                {param.sources.map((source, idx) => (
                                  <span
                                    key={idx}
                                    className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs"
                                  >
                                    {source}
                                  </span>
                                ))}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* V2 Specific Features */}
              {results.meta.v2_features && (
                <div className="mb-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">V2 Enhanced Features</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-white border border-gray-200 rounded-lg p-4">
                      <h4 className="font-medium text-gray-900 mb-2">Differential Analysis</h4>
                      <div className="text-sm text-gray-600">
                        <p>Candidates: {results.meta.v2_features.differential_candidates}</p>
                        <p>Location Testing: {results.meta.v2_features.location_testing}</p>
                      </div>
                    </div>
                    <div className="bg-white border border-gray-200 rounded-lg p-4">
                      <h4 className="font-medium text-gray-900 mb-2">Framework Detection</h4>
                      <div className="text-sm text-gray-600">
                        <p>Detected: {results.meta.v2_features.framework_detected ? 'Yes' : 'No'}</p>
                        <p>Enhanced Classification: {results.meta.v2_features.enhanced_classification ? 'Yes' : 'No'}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Endpoint Classification */}
              {results.meta.endpoint_classification && (
                <div className="mb-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Endpoint Classification</h3>
                  <div className="bg-white border border-gray-200 rounded-lg p-4">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-medium">Type:</span>
                        <span className="ml-2">{results.meta.endpoint_classification.endpoint_type}</span>
                      </div>
                      <div>
                        <span className="font-medium">Confidence:</span>
                        <span className="ml-2">{(results.meta.endpoint_classification.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AppV2;
