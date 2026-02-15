import React from 'react';

interface V2ResultsDisplayProps {
  results: any;
}

const V2ResultsDisplay: React.FC<V2ResultsDisplayProps> = ({ results }) => {
  if (!results) return null;

  return (
    <div className="space-y-6">
      {/* Discovery Summary */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">Discovery Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="font-medium text-blue-700">Version:</span>
            <span className="ml-2 text-blue-900">{results.meta?.discovery_version || 'v1'}</span>
          </div>
          <div>
            <span className="font-medium text-blue-700">Parameters:</span>
            <span className="ml-2 text-blue-900">{results.meta?.total_parameters || 0}</span>
          </div>
          <div>
            <span className="font-medium text-blue-700">Execution Time:</span>
            <span className="ml-2 text-blue-900">{results.meta?.execution_time_ms || 0}ms</span>
          </div>
          <div>
            <span className="font-medium text-blue-700">Success Rate:</span>
            <span className="ml-2 text-blue-900">
              {results.parameters ? `${((results.parameters.filter((p: any) => p.confidence > 0.5).length / results.parameters.length) * 100).toFixed(1)}%` : 'N/A'}
            </span>
          </div>
        </div>
      </div>

      {/* V2 Features */}
      {results.meta?.v2_features && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-green-900 mb-3">V2 Enhanced Features</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${results.meta.v2_features.framework_detected ? 'bg-green-500' : 'bg-gray-300'}`} />
              <span className="text-sm text-green-900">Framework Detection</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${results.meta.v2_features.weighted_scoring ? 'bg-green-500' : 'bg-gray-300'}`} />
              <span className="text-sm text-green-900">Weighted Scoring</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${results.meta.v2_features.enhanced_classification ? 'bg-green-500' : 'bg-gray-300'}`} />
              <span className="text-sm text-green-900">Enhanced Classification</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${results.meta.v2_features.differential_candidates > 0 ? 'bg-green-500' : 'bg-gray-300'}`} />
              <span className="text-sm text-green-900">Differential Analysis ({results.meta.v2_features.differential_candidates} candidates)</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${results.meta.v2_features.location_testing > 0 ? 'bg-green-500' : 'bg-gray-300'}`} />
              <span className="text-sm text-green-900">Location Resolution ({results.meta.v2_features.location_testing} tested)</span>
            </div>
          </div>
        </div>
      )}

      {/* Parameters Table */}
      {results.parameters && results.parameters.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Discovered Parameters</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Location
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Required
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Confidence
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Sources
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {results.parameters.map((param: any, index: number) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {param.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                        {param.type || 'unknown'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                        {param.location || 'unknown'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        param.required 
                          ? 'bg-red-100 text-red-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {param.required ? 'Required' : 'Optional'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex items-center">
                        <div className="w-24 bg-gray-200 rounded-full h-2 mr-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${(param.confidence || 0) * 100}%` }}
                          />
                        </div>
                        <span className="text-xs font-medium">{((param.confidence || 0) * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex flex-wrap gap-1">
                        {(param.sources || []).map((source: string, idx: number) => (
                          <span
                            key={idx}
                            className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs"
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

      {/* Endpoint Classification */}
      {results.meta?.endpoint_classification && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-purple-900 mb-3">Endpoint Classification</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <span className="font-medium text-purple-700">Type:</span>
              <span className="ml-2 text-purple-900 capitalize">{results.meta.endpoint_classification.endpoint_type}</span>
            </div>
            <div>
              <span className="font-medium text-purple-700">Confidence:</span>
              <span className="ml-2 text-purple-900">{(results.meta.endpoint_classification.confidence * 100).toFixed(1)}%</span>
            </div>
          </div>
          
          {results.meta.endpoint_classification.signals && (
            <div className="mt-3 pt-3 border-t border-purple-200">
              <h4 className="font-medium text-purple-900 mb-2">Detection Signals</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm">
                {results.meta.endpoint_classification.signals.baseline_status !== undefined && (
                  <div>
                    <span className="text-purple-700">Baseline Status:</span>
                    <span className="ml-2 text-purple-900">{results.meta.endpoint_classification.signals.baseline_status}</span>
                  </div>
                )}
                {results.meta.endpoint_classification.signals.differential_candidates !== undefined && (
                  <div>
                    <span className="text-purple-700">Differential Candidates:</span>
                    <span className="ml-2 text-purple-900">{results.meta.endpoint_classification.signals.differential_candidates}</span>
                  </div>
                )}
                {results.meta.endpoint_classification.signals.framework_signal && (
                  <div>
                    <span className="text-purple-700">Framework Signal:</span>
                    <span className="ml-2 text-purple-900">
                      {results.meta.endpoint_classification.signals.framework_signal.framework_type}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Differential Analysis Details */}
      {results.meta?.differential_analysis && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-orange-900 mb-3">Differential Analysis</h3>
          <div className="space-y-3">
            {results.meta.differential_analysis.candidates.map((candidate: any, index: number) => (
              <div key={index} className="bg-white border border-orange-100 rounded p-3">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-medium text-orange-900">{candidate.name}</h4>
                  <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded text-xs">
                    {(candidate.provisional_score * 100).toFixed(0)}% confidence
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm">
                  <div>
                    <span className="text-orange-700">Status Changed:</span>
                    <span className="ml-2 text-orange-900">{candidate.diffs.some((d: any) => d.status_changed) ? 'Yes' : 'No'}</span>
                  </div>
                  <div>
                    <span className="text-orange-700">Hash Changed:</span>
                    <span className="ml-2 text-orange-900">{candidate.diffs.some((d: any) => d.hash_changed) ? 'Yes' : 'No'}</span>
                  </div>
                  <div>
                    <span className="text-orange-700">Sources:</span>
                    <span className="ml-2 text-orange-900">{candidate.sources.join(', ')}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Location Resolution */}
      {results.meta?.location_resolution && (
        <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-teal-900 mb-3">Location Resolution</h3>
          <div className="space-y-3">
            {Object.entries(results.meta.location_resolution).map(([paramName, resolution]: [string, any]) => (
              <div key={paramName} className="bg-white border border-teal-100 rounded p-3">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-medium text-teal-900">{paramName}</h4>
                  <span className="px-2 py-1 bg-teal-100 text-teal-800 rounded text-xs">
                    {resolution.best_location}
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-teal-700">Location Confidence:</span>
                    <span className="ml-2 text-teal-900">{(resolution.location_confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div>
                    <span className="text-teal-700">Evidence Count:</span>
                    <span className="ml-2 text-teal-900">{Object.keys(resolution.location_evidence).length}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Results */}
      {results.parameters && results.parameters.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-yellow-900 mb-2">No Parameters Detected</h3>
          <p className="text-yellow-800">
            The API endpoint analysis did not detect any parameters. This could indicate:
          </p>
          <ul className="list-disc list-inside text-yellow-800 mt-2 space-y-1">
            <li>The endpoint doesn't require parameters</li>
            <li>The endpoint uses authentication that wasn't provided</li>
            <li>The endpoint has different parameter requirements</li>
            <li>The endpoint may not follow standard REST patterns</li>
          </ul>
        </div>
      )}
    </div>
  );
};

export default V2ResultsDisplay;
