import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './index.css';

function App() {
  const [activeTab, setActiveTab] = useState('discover');
  const [requestMethod, setRequestMethod] = useState('GET');
  const [requestUrl, setRequestUrl] = useState('');
  const [sending, setSending] = useState(false);
  const [lastResponse, setLastResponse] = useState(null);

  // Schema Discovery State
  const [discoverUrl, setDiscoverUrl] = useState('');
  const [discovering, setDiscovering] = useState(false);
  const [discoverResult, setDiscoverResult] = useState(null);

  // Runtime Validation State
  const [validateBaseUrl, setValidateBaseUrl] = useState('');
  const [schemaInput, setSchemaInput] = useState('');
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [queryParameters, setQueryParameters] = useState([{ key: '', value: '', description: '' }]);

  // Version History State
  const [versionHistory, setVersionHistory] = useState([]);

  // Schema Monitor State
  const [apis, setApis] = useState([]);
  const [selectedApi, setSelectedApi] = useState(null);
  const [apiSchemas, setApiSchemas] = useState([]);
  const [schemaChanges, setSchemaChanges] = useState([]);
  const [monitoring, setMonitoring] = useState(false);
  const [newApiForm, setNewApiForm] = useState({ name: '', base_url: '', description: '' });
  const [showNewApiForm, setShowNewApiForm] = useState(false);

  const sendRequest = async () => {
    if (!requestUrl) return;
    
    setSending(true);
    try {
      const response = await axios({
        method: requestMethod,
        url: requestUrl,
        timeout: 5000
      });
      
      setLastResponse({
        status: response.status,
        data: response.data,
        headers: response.headers
      });
      
      setActiveTab('body');
    } catch (error) {
      console.error('Request failed:', error);
      setLastResponse({
        status: error.response?.status || 'Error',
        data: error.response?.data || error.message,
        headers: error.response?.headers || {}
      });
    } finally {
      setSending(false);
    }
  };

  const discoverSchema = async () => {
    setDiscovering(true);
    setDiscoverResult(null);
    
    try {
      const response = await axios.post('http://localhost:8000/discover-schema', {
        url: discoverUrl
      });
      
      setDiscoverResult(response.data);
      
      if (response.data.status === 'success' && response.data.schema) {
        setVersionHistory(prev => [...prev, {
          id: Date.now(),
          url: discoverUrl,
          version: prev.length + 1,
          schema: response.data.schema,
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (error) {
      setDiscoverResult({
        error: error.response?.data?.error || 'Failed to discover schema'
      });
    } finally {
      setDiscovering(false);
    }
  };

  const validateRuntime = async () => {
    setValidating(true);
    setValidationResult(null);
    
    try {
      let schemaData;
      try {
        schemaData = JSON.parse(schemaInput);
      } catch (e) {
        setValidationResult({
          error: 'Invalid JSON schema. Please check your input.'
        });
        return;
      }
      
      const response = await axios.post('http://localhost:8000/validate-runtime', {
        base_url: validateBaseUrl,
        schema_info: schemaData
      });
      
      setValidationResult(response.data.validation_result);
    } catch (error) {
      setValidationResult({
        error: error.response?.data?.error || 'Failed to validate runtime'
      });
    } finally {
      setValidating(false);
    }
  };

  const useDiscoveredSchema = () => {
    if (discoverResult && discoverResult.schema) {
      setSchemaInput(JSON.stringify(discoverResult.schema, null, 2));
      if (discoverResult.url) {
        try {
          const url = new URL(discoverResult.url);
          setValidateBaseUrl(`${url.protocol}//${url.host}`);
        } catch (e) {
          setValidateBaseUrl(discoverResult.url);
        }
      }
      setActiveTab('validate');
    }
  };

  const addParam = () => {
    setQueryParameters([...queryParameters, { key: '', value: '', description: '' }]);
  };

  const removeParam = (index) => {
    if (queryParameters.length > 1) {
      setQueryParameters(queryParameters.filter((_, i) => i !== index));
    }
  };

  const updateParam = (index, field, value) => {
    const updated = [...queryParameters];
    updated[index][field] = value;
    setQueryParameters(updated);
  };

  const getResponseType = (data) => {
    if (Array.isArray(data)) {
      return `Array [${data.length} items]`;
    } else if (typeof data === 'object' && data !== null) {
      return `Object [${Object.keys(data).length} keys]`;
    } else if (typeof data === 'string') {
      return `String [${data.length} chars]`;
    } else {
      return typeof data;
    }
  };

  // Schema Monitor Functions
  const loadApis = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/apis');
      setApis(response.data.apis);
    } catch (error) {
      console.error('Failed to load APIs:', error);
    }
  };

  const loadApiSchemas = async (apiId) => {
    try {
      const response = await axios.get(`http://localhost:8000/api/apis/${apiId}/schemas`);
      setApiSchemas(response.data.schemas);
    } catch (error) {
      console.error('Failed to load API schemas:', error);
    }
  };

  const createApi = async () => {
    if (!newApiForm.name || !newApiForm.base_url) return;
    
    try {
      const formData = new FormData();
      formData.append('name', newApiForm.name);
      formData.append('base_url', newApiForm.base_url);
      formData.append('description', newApiForm.description);
      
      const response = await axios.post('http://localhost:8000/api/apis', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      if (response.data.status === 'success') {
        setNewApiForm({ name: '', base_url: '', description: '' });
        setShowNewApiForm(false);
        loadApis();
      }
    } catch (error) {
      console.error('Failed to create API:', error);
    }
  };

  const scanApi = async (apiId) => {
    setMonitoring(true);
    try {
      const response = await axios.post(`http://localhost:8000/api/apis/${apiId}/scan`);
      
      if (response.data.status === 'success') {
        loadApiSchemas(apiId);
        alert('New schema version detected and stored!');
      } else if (response.data.status === 'unchanged') {
        alert('Schema has not changed since last scan.');
      } else {
        alert('No schema found for this API.');
      }
    } catch (error) {
      console.error('Failed to scan API:', error);
      alert('Failed to scan API schema.');
    } finally {
      setMonitoring(false);
    }
  };

  const compareSchemas = async (apiId, version1, version2) => {
    try {
      const response = await axios.get(`http://localhost:8000/api/schemas/${apiId}/compare/${version1}/${version2}`);
      setSchemaChanges(response.data.changes);
    } catch (error) {
      console.error('Failed to compare schemas:', error);
    }
  };

  useEffect(() => {
    if (activeTab === 'monitor') {
      loadApis();
    }
  }, [activeTab]);

  useEffect(() => {
    if (selectedApi) {
      loadApiSchemas(selectedApi.id);
    }
  }, [selectedApi]);

  return (
    <div className="app-container">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">COLLECTIONS</div>
        <div className="collections">
          <div 
            className={`collection-item ${activeTab === 'discover' ? 'active' : ''}`}
            onClick={() => setActiveTab('discover')}
          >
            📄 Discover Schema
          </div>
          <div 
            className={`collection-item ${activeTab === 'validate' ? 'active' : ''}`}
            onClick={() => setActiveTab('validate')}
          >
            ✅ Runtime Validation
          </div>
          <div 
            className={`collection-item ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            📚 Version History
          </div>
          <div 
            className={`collection-item ${activeTab === 'monitor' ? 'active' : ''}`}
            onClick={() => setActiveTab('monitor')}
          >
            🔍 Schema Monitor
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="main-content">
        {/* Request Bar */}
        <div className="request-bar">
          <select 
            className="method-selector" 
            value={requestMethod}
            onChange={(e) => setRequestMethod(e.target.value)}
          >
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
            <option value="DELETE">DELETE</option>
            <option value="PATCH">PATCH</option>
          </select>
          <input 
            className="url-input"
            value={requestUrl}
            onChange={(e) => setRequestUrl(e.target.value)}
            type="text" 
            placeholder="https://api.example.com/endpoint"
            onKeyPress={(e) => e.key === 'Enter' && sendRequest()}
          />
          <button 
            className="send-button" 
            onClick={sendRequest} 
            disabled={!requestUrl || sending}
          >
            {sending ? 'Sending...' : 'Send'}
          </button>
        </div>
        
        {/* Tab Content */}
        <div className="tab-content">
          {/* Schema Discovery Tab */}
          {activeTab === 'discover' && (
            <div>
              <div className="form-group">
                <label>API URL</label>
                <input 
                  value={discoverUrl}
                  onChange={(e) => setDiscoverUrl(e.target.value)}
                  type="url" 
                  placeholder="https://api.example.com"
                  onKeyPress={(e) => e.key === 'Enter' && discoverSchema()}
                />
              </div>
              <button 
                className="btn" 
                onClick={discoverSchema} 
                disabled={!discoverUrl || discovering}
              >
                {discovering ? 'Discovering...' : 'Discover Schema'}
              </button>
              
              {discovering && (
                <div className="loading">
                  <div className="spinner"></div>
                  <p>Discovering API schema...</p>
                </div>
              )}
              
              {discoverResult && (
                <div className="result">
                  <h3>Schema Discovery Result</h3>
                  {discoverResult.schema ? (
                    <div className="schema-info">
                      <h4>✅ Schema Found</h4>
                      <p><strong>URL:</strong> {discoverResult.url}</p>
                      <p><strong>Status:</strong> {discoverResult.status}</p>
                      <details>
                        <summary>View Schema Details</summary>
                        <pre>{JSON.stringify(discoverResult.schema, null, 2)}</pre>
                      </details>
                    </div>
                  ) : (
                    <div className="error">
                      <h4>❌ Discovery Failed</h4>
                      <p>{discoverResult.error}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          
          {/* Runtime Validation Tab */}
          {activeTab === 'validate' && (
            <div>
              <h3>Query Parameters</h3>
              <div className="params-table">
                <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 2fr 40px', gap: '8px', padding: '8px', background: '#252526', borderRadius: '4px', marginBottom: '8px'}}>
                  <strong style={{color: '#cccccc', fontSize: '12px'}}>Key</strong>
                  <strong style={{color: '#cccccc', fontSize: '12px'}}>Value</strong>
                  <strong style={{color: '#cccccc', fontSize: '12px'}}>Description</strong>
                  <span></span>
                </div>
                {queryParameters.map((param, index) => (
                  <div key={index} className="param-row">
                    <div className="params-grid">
                      <input 
                        className="param-input"
                        value={param.key}
                        onChange={(e) => updateParam(index, 'key', e.target.value)}
                        type="text" 
                        placeholder="Key"
                      />
                      <input 
                        className="param-input"
                        value={param.value}
                        onChange={(e) => updateParam(index, 'value', e.target.value)}
                        type="text" 
                        placeholder="Value"
                      />
                      <input 
                        className="param-input"
                        value={param.description}
                        onChange={(e) => updateParam(index, 'description', e.target.value)}
                        type="text" 
                        placeholder="Description"
                      />
                      <button 
                        className="remove-btn"
                        onClick={() => removeParam(index)}
                      >
                        ×
                      </button>
                    </div>
                  </div>
                ))}
                <button 
                  className="btn" 
                  onClick={addParam}
                  style={{marginTop: '8px', padding: '4px 12px', fontSize: '12px'}}
                >
                  + Add Parameter
                </button>
              </div>
              
              <div style={{marginTop: '20px'}}>
                <h4>API Validation</h4>
                <div className="form-group">
                  <label>API Base URL</label>
                  <input 
                    value={validateBaseUrl}
                    onChange={(e) => setValidateBaseUrl(e.target.value)}
                    type="url" 
                    placeholder="https://api.example.com"
                    onKeyPress={(e) => e.key === 'Enter' && validateRuntime()}
                  />
                </div>
                <div className="form-group">
                  <label>Schema JSON</label>
                  <textarea 
                    value={schemaInput}
                    onChange={(e) => setSchemaInput(e.target.value)}
                    placeholder="Paste your OpenAPI/Swagger schema JSON here..."
                    rows="8"
                  />
                </div>
                <div style={{display: 'flex', gap: '8px', marginBottom: '16px'}}>
                  <button 
                    className="btn" 
                    onClick={validateRuntime} 
                    disabled={!validateBaseUrl || !schemaInput || validating}
                  >
                    {validating ? 'Validating...' : 'Validate Runtime'}
                  </button>
                  <button 
                    className="btn btn-secondary" 
                    onClick={useDiscoveredSchema} 
                    disabled={!discoverResult || !discoverResult.schema}
                  >
                    Use Discovered Schema
                  </button>
                </div>
              </div>
              
              {validating && (
                <div className="loading">
                  <div className="spinner"></div>
                  <p>Validating API runtime behavior...</p>
                </div>
              )}
              
              {validationResult && (
                <div className="result">
                  <h3>Runtime Validation Results</h3>
                  <div className="validation-summary">
                    <div className="summary-stats">
                      <div className="stat">
                        <span className="stat-value">{validationResult.total_endpoints}</span>
                        <span className="stat-label">Total Endpoints</span>
                      </div>
                      <div className="stat">
                        <span className="stat-value">{validationResult.passed_endpoints}</span>
                        <span className="stat-label">Passed</span>
                      </div>
                      <div className="stat">
                        <span className="stat-value">{validationResult.failed_endpoints}</span>
                        <span className="stat-label">Failed</span>
                      </div>
                    </div>
                    <p><strong>Summary:</strong> {validationResult.summary}</p>
                  </div>
                  
                  <div style={{marginTop: '20px'}}>
                    <h4>Endpoint Test Results</h4>
                    {validationResult.endpoint_tests?.map((test, index) => (
                      <div key={index} className={`endpoint-test ${!test.validation_passed ? 'failed' : ''}`}>
                        <div className="test-header">
                          <span className="method">{test.method}</span>
                          <span className="path">{test.path}</span>
                          <span className={`status ${test.validation_passed ? 'success' : 'error'}`}>
                            {test.validation_passed ? '✅ PASS' : '❌ FAIL'}
                          </span>
                        </div>
                        <div className="test-details">
                          <p><strong>URL:</strong> {test.url}</p>
                          <p><strong>Status:</strong> {test.actual_status || 'No response'}</p>
                          {test.response_time_ms && (
                            <p><strong>Response Time:</strong> {test.response_time_ms.toFixed(2)}ms</p>
                          )}
                          {test.error && (
                            <p><strong>Error:</strong> {test.error}</p>
                          )}
                          {test.actual_response && (
                            <details>
                              <summary>Response Data ({getResponseType(test.actual_response)})</summary>
                              <pre>{JSON.stringify(test.actual_response, null, 2)}</pre>
                            </details>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {validationResult?.error && (
                <div className="error">
                  <h4>❌ Validation Failed</h4>
                  <p>{validationResult.error}</p>
                </div>
              )}
            </div>
          )}
          
          {/* Version History Tab */}
          {activeTab === 'history' && (
            <div>
              <h3>Schema Version History</h3>
              <p style={{color: '#969696', marginBottom: '20px'}}>
                Version history will be populated as you discover schemas from different APIs.
              </p>
              
              {versionHistory.length === 0 ? (
                <div className="result">
                  <p style={{textAlign: 'center', color: '#969696'}}>No schema versions discovered yet.</p>
                </div>
              ) : (
                versionHistory.map(version => (
                  <div key={version.id} className="result" style={{marginBottom: '12px'}}>
                    <h4>{version.url}</h4>
                    <p style={{fontSize: '12px', color: '#969696', marginBottom: '8px'}}>
                      <strong>Version:</strong> {version.version} | 
                      <strong> Discovered:</strong> {new Date(version.timestamp).toLocaleString()}
                    </p>
                    <details>
                      <summary>View Schema</summary>
                      <pre>{JSON.stringify(version.schema, null, 2)}</pre>
                    </details>
                  </div>
                ))
              )}
            </div>
          )}
          
          {/* Schema Monitor Tab */}
          {activeTab === 'monitor' && (
            <div>
              <h3>Schema Monitor</h3>
              <p style={{color: '#969696', marginBottom: '20px'}}>
                Monitor API schemas for changes over time. Add APIs to track and scan them periodically to detect schema changes.
              </p>
              
              {/* Add New API Button */}
              <div style={{marginBottom: '20px'}}>
                <button 
                  className="btn" 
                  onClick={() => setShowNewApiForm(!showNewApiForm)}
                >
                  + Add New API
                </button>
              </div>
              
              {/* New API Form */}
              {showNewApiForm && (
                <div className="result" style={{marginBottom: '20px'}}>
                  <h4>Add New API to Monitor</h4>
                  <div className="form-group">
                    <label>API Name</label>
                    <input 
                      value={newApiForm.name}
                      onChange={(e) => setNewApiForm({...newApiForm, name: e.target.value})}
                      type="text" 
                      placeholder="My API"
                    />
                  </div>
                  <div className="form-group">
                    <label>Base URL</label>
                    <input 
                      value={newApiForm.base_url}
                      onChange={(e) => setNewApiForm({...newApiForm, base_url: e.target.value})}
                      type="url" 
                      placeholder="https://api.example.com"
                    />
                  </div>
                  <div className="form-group">
                    <label>Description</label>
                    <input 
                      value={newApiForm.description}
                      onChange={(e) => setNewApiForm({...newApiForm, description: e.target.value})}
                      type="text" 
                      placeholder="Optional description"
                    />
                  </div>
                  <div style={{display: 'flex', gap: '8px'}}>
                    <button 
                      className="btn" 
                      onClick={createApi}
                      disabled={!newApiForm.name || !newApiForm.base_url}
                    >
                      Add API
                    </button>
                    <button 
                      className="btn btn-secondary" 
                      onClick={() => setShowNewApiForm(false)}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
              
              {/* APIs List */}
              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px'}}>
                {/* APIs Column */}
                <div>
                  <h4>Monitored APIs</h4>
                  {apis.length === 0 ? (
                    <div className="result">
                      <p style={{textAlign: 'center', color: '#969696'}}>No APIs being monitored yet.</p>
                    </div>
                  ) : (
                    apis.map(api => (
                      <div 
                        key={api.id} 
                        className={`result ${selectedApi?.id === api.id ? 'selected' : ''}`}
                        style={{marginBottom: '12px', cursor: 'pointer'}}
                        onClick={() => setSelectedApi(api)}
                      >
                        <h4>{api.name}</h4>
                        <p style={{fontSize: '12px', color: '#969696', marginBottom: '8px'}}>
                          {api.base_url}
                        </p>
                        {api.description && (
                          <p style={{fontSize: '11px', color: '#cccccc', marginBottom: '8px'}}>
                            {api.description}
                          </p>
                        )}
                        <p style={{fontSize: '11px', color: '#969696'}}>
                          Added: {new Date(api.date_added).toLocaleDateString()}
                        </p>
                      </div>
                    ))
                  )}
                </div>
                
                {/* Schema Versions Column */}
                <div>
                  {selectedApi ? (
                    <>
                      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px'}}>
                        <h4>Schema Versions for {selectedApi.name}</h4>
                        <button 
                          className="btn" 
                          onClick={() => scanApi(selectedApi.id)}
                          disabled={monitoring}
                          style={{padding: '4px 12px', fontSize: '12px'}}
                        >
                          {monitoring ? 'Scanning...' : 'Scan Now'}
                        </button>
                      </div>
                      
                      {apiSchemas.length === 0 ? (
                        <div className="result">
                          <p style={{textAlign: 'center', color: '#969696'}}>No schema versions found. Scan to detect schema.</p>
                        </div>
                      ) : (
                        <div>
                          {apiSchemas.map(schema => (
                            <div key={schema.id} className="result" style={{marginBottom: '12px'}}>
                              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                                <div>
                                  <h5>Version {schema.version_number}</h5>
                                  <p style={{fontSize: '11px', color: '#969696'}}>
                                    {new Date(schema.timestamp).toLocaleString()}
                                  </p>
                                </div>
                                <div style={{display: 'flex', gap: '4px'}}>
                                  {apiSchemas.length > 1 && schema.version_number < apiSchemas[0].version_number && (
                                    <button 
                                      className="btn btn-secondary"
                                      onClick={() => compareSchemas(selectedApi.id, schema.version_number, apiSchemas[0].version_number)}
                                      style={{padding: '2px 8px', fontSize: '10px'}}
                                    >
                                      Compare
                                    </button>
                                  )}
                                  <details>
                                    <summary style={{cursor: 'pointer', fontSize: '10px'}}>View</summary>
                                    <pre style={{maxHeight: '200px', overflow: 'auto', fontSize: '10px'}}>
                                      {JSON.stringify(schema.schema_json, null, 2)}
                                    </pre>
                                  </details>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="result">
                      <p style={{textAlign: 'center', color: '#969696'}}>Select an API to view schema versions.</p>
                    </div>
                  )}
                </div>
              </div>
              
              {/* Schema Changes */}
              {schemaChanges.length > 0 && (
                <div style={{marginTop: '20px'}}>
                  <h4>Schema Changes</h4>
                  <div className="result">
                    {schemaChanges.map((change, index) => (
                      <div key={index} className={`endpoint-test ${change.type === 'removed' || change.severity === 'critical' ? 'failed' : ''}`}>
                        <div className="test-header">
                          <span className={`status ${change.severity === 'critical' ? 'error' : change.severity === 'high' ? 'error' : 'success'}`}>
                            {change.type.toUpperCase()} - {change.severity.toUpperCase()}
                          </span>
                        </div>
                        <div className="test-details">
                          <p>{change.details}</p>
                          <p style={{fontSize: '11px', color: '#969696'}}>
                            Category: {change.category} | Path: {change.path}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          
          {/* Response Tab (Body) */}
          {activeTab === 'body' && (
            <div>
              <h3>Request Body</h3>
              <div className="form-group">
                <textarea placeholder="Enter request body (JSON, XML, etc.)" rows="8"></textarea>
              </div>
              
              {lastResponse && (
                <div className="result">
                  <h3>Response</h3>
                  <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px'}}>
                    <div>
                      <label style={{fontSize: '12px', color: '#cccccc'}}>Status:</label>
                      <div style={{color: lastResponse.status >= 200 && lastResponse.status < 300 ? '#4ec9b0' : '#f48771', fontWeight: 'bold'}}>
                        {lastResponse.status}
                      </div>
                    </div>
                    <div>
                      <label style={{fontSize: '12px', color: '#cccccc'}}>Response Time:</label>
                      <div>{new Date().toLocaleTimeString()}</div>
                    </div>
                  </div>
                  
                  <details open>
                    <summary>Response Body ({getResponseType(lastResponse.data)})</summary>
                    <pre>{JSON.stringify(lastResponse.data, null, 2)}</pre>
                  </details>
                  
                  <details>
                    <summary>Response Headers</summary>
                    <pre>{JSON.stringify(lastResponse.headers, null, 2)}</pre>
                  </details>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
