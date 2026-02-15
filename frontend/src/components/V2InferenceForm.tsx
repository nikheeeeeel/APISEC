import React, { useState } from 'react';

interface V2InferenceFormProps {
  onSubmit: (data: any) => void;
  onSpecGeneration: (data: any) => void;
  isLoading: boolean;
}

const V2InferenceForm: React.FC<V2InferenceFormProps> = ({ onSubmit, onSpecGeneration, isLoading }) => {
  const [url, setUrl] = useState('');
  const [method, setMethod] = useState('POST');
  const [timeLimit, setTimeLimit] = useState(30);
  
  // V2 Enhanced state
  const [authType, setAuthType] = useState<'none' | 'bearer' | 'apikey'>('none');
  const [authToken, setAuthToken] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [headerName, setHeaderName] = useState('');
  const [customHeaders, setCustomHeaders] = useState('');
  const [seedBody, setSeedBody] = useState('');
  const [contentType, setContentType] = useState('');
  const [enableV2, setEnableV2] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Build V2 request payload
    const requestPayload = {
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

    onSubmit(requestPayload);
  };

  const handleSpecGeneration = () => {
    if (!url) return;
    
    const requestPayload = {
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

    onSpecGeneration(requestPayload);
  };

  const validateForm = () => {
    if (!url.trim()) return false;
    if (authType === 'bearer' && !authToken.trim()) return false;
    if (authType === 'apikey' && (!apiKey.trim() || !headerName.trim())) return false;
    if (customHeaders && customHeaders.trim()) {
      try {
        JSON.parse(customHeaders);
      } catch {
        return false;
      }
    }
    if (seedBody && seedBody.trim()) {
      try {
        JSON.parse(seedBody);
      } catch {
        return false;
      }
    }
    return true;
  };

  const isValid = validateForm();

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          REST Parameter Discovery v2
        </h1>
        <p className="text-gray-600">
          Enhanced API parameter discovery with differential analysis, location resolution, and weighted confidence scoring
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Configuration */}
        <div className="space-y-4">
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
        </div>

        {/* V2 Toggle */}
        <div className="border-t pt-4">
          <div className="flex items-center justify-between">
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
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              {showAdvanced ? 'Hide' : 'Show'} Advanced Options
            </button>
          </div>
        </div>

        {/* Advanced Options */}
        {showAdvanced && (
          <div className="border-t pt-4 space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">Advanced v2 Options</h3>
            
            {/* Authentication */}
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

            {/* Custom Headers */}
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
                placeholder='{"Content-Type": "application/json", "Accept": "application/json"}'
              />
              {customHeaders && customHeaders.trim() && (() => {
                try {
                  JSON.parse(customHeaders);
                  return null;
                } catch {
                  return <p className="text-xs text-red-500 mt-1">Invalid JSON format</p>;
                }
              })()}
            </div>

            {/* Seed Body */}
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
                placeholder='{"example": "data", "type": "test"}'
              />
              {seedBody && seedBody.trim() && (() => {
                try {
                  JSON.parse(seedBody);
                  return null;
                } catch {
                  return <p className="text-xs text-red-500 mt-1">Invalid JSON format</p>;
                }
              })()}
            </div>

            {/* Content Type Override */}
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
              <p className="text-xs text-gray-500 mt-1">Override the default content-type for the request</p>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex space-x-4">
          <button
            type="submit"
            disabled={isLoading || !isValid}
            className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Discovering...' : 'Discover Parameters'}
          </button>
          
          <button
            type="button"
            onClick={handleSpecGeneration}
            disabled={isLoading || !url.trim()}
            className="flex-1 bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Generating...' : 'Generate OpenAPI Spec'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default V2InferenceForm;
