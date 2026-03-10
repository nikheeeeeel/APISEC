import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import LoadingSpinner from './components/LoadingSpinner';
import ResultCard from './components/ResultCard';
import ParameterTable from './components/ParameterTable';
import LandingPage from './components/LandingPage';
import './index.css';

function App() {
  const [showLanding, setShowLanding] = useState(true);
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

  // Version History State - Enhanced for Schema Monitor
  const [versionHistory, setVersionHistory] = useState([]);
  const [apis, setApis] = useState([]);
  const [apiSchemas, setApiSchemas] = useState({});
  const [expandedApis, setExpandedApis] = useState({});
  const [schemaChanges, setSchemaChanges] = useState([]);
  const [monitoring, setMonitoring] = useState(false);
  const [newApiForm, setNewApiForm] = useState({ name: '', base_url: '', description: '' });
  const [showNewApiForm, setShowNewApiForm] = useState(false);

  const handleGetStarted = useCallback(() => {
    setShowLanding(false);
  }, []);

  // Memoized handlers for better performance
  const sendRequest = useCallback(async () => {
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
        headers: response.headers,
        timestamp: new Date().toISOString()
      });
      
      setActiveTab('body');
    } catch (error) {
      console.error('Request failed:', error);
      setLastResponse({
        status: error.response?.status || 'Error',
        data: error.response?.data || error.message,
        headers: error.response?.headers || {},
        error: true,
        timestamp: new Date().toISOString()
      });
    } finally {
      setSending(false);
    }
  }, [requestUrl, requestMethod]);

  const discoverSchema = useCallback(async () => {
    setDiscovering(true);
    setDiscoverResult(null);
    
    try {
      const response = await axios.post('http://localhost:8001/discover-schema', {
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
        
        // Also add to schema monitor if not already there
        const apiName = new URL(discoverUrl).hostname || 'Unknown API';
        const existingApi = apis.find(api => api.base_url === discoverUrl);
        
        if (!existingApi) {
          // Create new API entry in monitor with proper backend registration
          const newApi = {
            name: apiName,
            base_url: discoverUrl,
            description: `Discovered from ${new URL(discoverUrl).hostname}`
          };
          
          // Register API in backend using direct API call
          try {
            const formData = new FormData();
            formData.append('name', newApi.name);
            formData.append('base_url', newApi.base_url);
            formData.append('description', newApi.description);
            
            const response = await axios.post('http://localhost:8001/api/apis', formData, {
              headers: { 'Content-Type': 'multipart/form-data' }
            });
            
            if (response.data.status === 'success') {
              // Reload APIs to get the newly added one with proper ID
              loadApis();
            }
          } catch (error) {
            console.error('Failed to auto-add API:', error);
          }
        } else {
          // If API already exists, just load its schemas
          loadApiSchemas(existingApi.id);
        }
      }
    } catch (error) {
      setDiscoverResult({
        error: error.response?.data?.error || 'Failed to discover schema'
      });
    } finally {
      setDiscovering(false);
    }
  }, [discoverUrl]);

  const validateRuntime = useCallback(async () => {
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
      
      const response = await axios.post('http://localhost:8001/validate-runtime', {
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
  }, [validateBaseUrl, schemaInput]);

  const useDiscoveredSchema = useCallback(() => {
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
  }, [discoverResult]);

  const addParam = useCallback(() => {
    setQueryParameters(prev => [...prev, { key: '', value: '', description: '' }]);
  }, []);

  const removeParam = useCallback((index) => {
    setQueryParameters(prev => prev.length > 1 ? prev.filter((_, i) => i !== index) : prev);
  }, []);

  const getResponseType = useCallback((data) => {
    if (Array.isArray(data)) {
      return `Array [${data.length} items]`;
    } else if (typeof data === 'object' && data !== null) {
      return `Object [${Object.keys(data).length} keys]`;
    } else if (typeof data === 'string') {
      return `String [${data.length} chars]`;
    } else {
      return typeof data;
    }
  }, []);

  const formatTimestamp = useCallback((timestamp) => {
    return new Date(timestamp).toLocaleString();
  }, []);

  // Schema Monitor Functions - Enhanced
  const loadApis = useCallback(async () => {
    try {
      const response = await axios.get('http://localhost:8001/api/apis');
      setApis(response.data.apis);
      
      // Load schemas for all APIs
      const schemasPromises = response.data.apis.map(api => 
        axios.get(`http://localhost:8001/api/apis/${api.id}/schemas`)
          .then(res => ({ apiId: api.id, schemas: res.data.schemas }))
          .catch(() => ({ apiId: api.id, schemas: [] }))
      );
      
      const schemasResults = await Promise.all(schemasPromises);
      const schemasMap = {};
      schemasResults.forEach(({ apiId, schemas }) => {
        schemasMap[apiId] = schemas;
      });
      setApiSchemas(schemasMap);
    } catch (error) {
      console.error('Failed to load APIs:', error);
    }
  }, []);

  const loadApiSchemas = useCallback(async (apiId) => {
    try {
      const response = await axios.get(`http://localhost:8001/api/apis/${apiId}/schemas`);
      setApiSchemas(prev => ({ ...prev, [apiId]: response.data.schemas }));
    } catch (error) {
      console.error('Failed to load API schemas:', error);
    }
  }, []);

  const createApi = useCallback(async () => {
    if (!newApiForm.name || !newApiForm.base_url) return;
    
    try {
      const formData = new FormData();
      formData.append('name', newApiForm.name);
      formData.append('base_url', newApiForm.base_url);
      formData.append('description', newApiForm.description);
      
      const response = await axios.post('http://localhost:8001/api/apis', formData, {
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
  }, [newApiForm, loadApis]);

  const scanApi = useCallback(async (apiId) => {
    setMonitoring(true);
    try {
      const response = await axios.post(`http://localhost:8001/api/apis/${apiId}/scan`);
      
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
  }, [loadApiSchemas]);

  const rescanApi = useCallback(async (api) => {
    setMonitoring(true);
    try {
      // Use discover-schema endpoint for rescan
      const response = await axios.post('http://localhost:8001/discover-schema', {
        url: api.base_url
      });
      
      if (response.data.status === 'success' && response.data.schema) {
        // Add as new version to this API
        const newSchema = {
          id: Date.now(),
          api_id: api.id,
          version_number: (apiSchemas[api.id]?.length || 0) + 1,
          schema_json: response.data.schema,
          timestamp: new Date().toISOString()
        };
        
        setApiSchemas(prev => ({
          ...prev,
          [api.id]: [...(prev[api.id] || []), newSchema]
        }));
        
        alert('Schema rescanned and new version added!');
      } else {
        alert('No schema found during rescan.');
      }
    } catch (error) {
      console.error('Failed to rescan API:', error);
      alert('Failed to rescan API schema.');
    } finally {
      setMonitoring(false);
    }
  }, [apiSchemas]);

  const deleteApi = useCallback(async (apiId) => {
    if (!confirm('Are you sure you want to delete this API and all its schema versions?')) return;
    
    try {
      await axios.delete(`http://localhost:8001/api/apis/${apiId}`);
      loadApis(); // Reload the list
    } catch (error) {
      console.error('Failed to delete API:', error);
      alert('Failed to delete API.');
    }
  }, [loadApis]);

  const compareSchemas = useCallback(async (apiId, version1, version2) => {
    try {
      const response = await axios.get(`http://localhost:8001/api/schemas/${apiId}/compare/${version1}/${version2}`);
      setSchemaChanges(response.data.changes);
      
      // Scroll to the changes section
      setTimeout(() => {
        const changesElement = document.querySelector('[data-changes-section="true"]');
        if (changesElement) {
          changesElement.scrollIntoView({ behavior: 'smooth' });
        }
      }, 100);
      
      // Show a success message
      if (response.data.changes.length === 0) {
        alert('No changes found between these versions.');
      } else {
        alert(`Found ${response.data.changes.length} changes between versions ${version1} and ${version2}.`);
      }
    } catch (error) {
      console.error('Failed to compare schemas:', error);
      if (error.response?.status === 404) {
        alert('One or both schema versions not found. Please scan the API first to create more versions.');
      } else {
        alert('Failed to compare schemas. Please try again.');
      }
    }
  }, []);

  const toggleApiExpansion = useCallback((apiId) => {
    setExpandedApis(prev => ({ ...prev, [apiId]: !prev[apiId] }));
  }, []);

  useEffect(() => {
    if (activeTab === 'history' || activeTab === 'monitor') {
      loadApis();
    }
  }, [activeTab, loadApis]);

  return (
    <div className="app-container">
      {showLanding ? (
        <LandingPage onGetStarted={handleGetStarted} />
      ) : (
        <>
          {/* Sidebar */}
          <div className="sidebar">
            <div className="sidebar-header">TOOLS</div>
            <div className="collections">
              {[
                { id: 'discover', label: 'Discover Schema' },
                { id: 'validate', label: 'Runtime Validation' },
                { id: 'history', label: 'Schema Monitor' }
              ].map(tab => (
                <div 
                  key={tab.id}
                  className={`collection-item ${activeTab === tab.id ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.label}
                </div>
              ))}
            </div>
          </div>
          
          {/* Main Content */}
          <div className="main-content">
            {/* Request Bar */}
            <div className="request-bar">
              <select 
                className="method-selector focus-ring" 
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
                className="url-input focus-ring"
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
                      className="focus-ring"
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
                  
                  {discovering && <LoadingSpinner />}
                  
                  {discoverResult && (
                    <ResultCard title="Schema Discovery Result">
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
                    </ResultCard>
                  )}
                </div>
              )}
              
              {/* Runtime Validation Tab */}
              {activeTab === 'validate' && (
                <div>
                  <h3 style={{marginBottom: '20px', color: 'var(--text-primary)'}}>Query Parameters</h3>
                  <ParameterTable 
                    parameters={queryParameters}
                    onChange={setQueryParameters}
                    onAdd={addParam}
                    onRemove={removeParam}
                  />
                  
                  <div style={{marginTop: '24px'}}>
                    <h4 style={{marginBottom: '16px', color: 'var(--text-primary)'}}>API Validation</h4>
                    <div className="form-group">
                      <label>API Base URL</label>
                      <input 
                        className="focus-ring"
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
                        className="focus-ring"
                        value={schemaInput}
                        onChange={(e) => setSchemaInput(e.target.value)}
                        placeholder="Paste your OpenAPI/Swagger schema JSON here..."
                        rows="8"
                      />
                    </div>
                    <div style={{display: 'flex', gap: '12px', marginBottom: '20px'}}>
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
                  
                  {validating && <LoadingSpinner />}
                  
                  {validationResult && (
                    <ResultCard title="Runtime Validation Results">
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
                        <h4 style={{marginBottom: '16px', color: 'var(--text-primary)'}}>Endpoint Test Results</h4>
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
                    </ResultCard>
                  )}
                  
                  {validationResult?.error && (
                    <ResultCard type="error">
                      <h4>❌ Validation Failed</h4>
                      <p>{validationResult.error}</p>
                    </ResultCard>
                  )}
                </div>
              )}
              
              {/* Version History Tab - Enhanced with Schema Monitor */}
              {activeTab === 'history' && (
                <div>
                  <h3 style={{marginBottom: '20px', color: 'var(--text-primary)'}}>Schema Version History</h3>
                  <p style={{color: 'var(--text-secondary)', marginBottom: '20px'}}>
                    Monitor API schemas for changes over time. Each API shows its version history with the ability to compare versions.
                  </p>
                  
                  {/* Add New API Button */}
                  <div style={{marginBottom: '20px'}}>
                    <button 
                      className="btn" 
                      onClick={() => setShowNewApiForm(!showNewApiForm)}
                    >
                      + Add API to Monitor
                    </button>
                  </div>
                  
                  {/* New API Form */}
                  {showNewApiForm && (
                    <ResultCard title="Add New API to Monitor" style={{marginBottom: '20px'}}>
                      <div className="form-group">
                        <label>API Name</label>
                        <input 
                          className="focus-ring"
                          value={newApiForm.name}
                          onChange={(e) => setNewApiForm({...newApiForm, name: e.target.value})}
                          type="text" 
                          placeholder="My API"
                        />
                      </div>
                      <div className="form-group">
                        <label>Base URL</label>
                        <input 
                          className="focus-ring"
                          value={newApiForm.base_url}
                          onChange={(e) => setNewApiForm({...newApiForm, base_url: e.target.value})}
                          type="url" 
                          placeholder="https://api.example.com"
                        />
                      </div>
                      <div className="form-group">
                        <label>Description</label>
                        <input 
                          className="focus-ring"
                          value={newApiForm.description}
                          onChange={(e) => setNewApiForm({...newApiForm, description: e.target.value})}
                          type="text" 
                          placeholder="Optional description"
                        />
                      </div>
                      <div style={{display: 'flex', gap: '12px'}}>
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
                    </ResultCard>
                  )}
                  
                  {/* API Cards */}
                  {apis.length === 0 ? (
                    <ResultCard>
                      <p style={{textAlign: 'center', color: 'var(--text-secondary)'}}>No APIs being monitored yet. Add an API to get started.</p>
                    </ResultCard>
                  ) : (
                    <div style={{display: 'flex', flexDirection: 'column', gap: '16px'}}>
                      {apis.map(api => {
                        const schemas = apiSchemas[api.id] || [];
                        const isExpanded = expandedApis[api.id];
                        
                        return (
                          <ResultCard key={api.id} style={{position: 'relative'}}>
                            {/* Delete Button */}
                            <button
                              onClick={() => deleteApi(api.id)}
                              style={{
                                position: 'absolute',
                                top: '8px',
                                right: '8px',
                                width: '28px',
                                height: '28px',
                                padding: '0',
                                borderRadius: '50%',
                                fontSize: '16px',
                                fontWeight: 'bold',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                background: '#dc3545',
                                color: 'white',
                                border: 'none',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                              }}
                              onMouseEnter={(e) => {
                                e.target.style.background = '#c82333';
                                e.target.style.transform = 'scale(1.1)';
                              }}
                              onMouseLeave={(e) => {
                                e.target.style.background = '#dc3545';
                                e.target.style.transform = 'scale(1)';
                              }}
                              title="Delete API and all versions"
                            >
                              ×
                            </button>
                            
                            {/* API Header */}
                            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginRight: '40px'}}>
                              <div style={{flex: 1}}>
                                <div style={{display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px'}}>
                                  <h4 style={{margin: '0', color: 'var(--text-primary)'}}>{api.name}</h4>
                                  {api.description?.includes('Discovered from') && (
                                    <span style={{
                                      background: 'var(--success)',
                                      color: 'white',
                                      fontSize: '10px',
                                      padding: '2px 6px',
                                      borderRadius: '12px',
                                      fontWeight: 'bold'
                                    }}>
                                      AUTO-DISCOVERED
                                    </span>
                                  )}
                                </div>
                                <p style={{fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '8px'}}>
                                  {api.base_url}
                                </p>
                                {api.description && (
                                  <p style={{fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px'}}>
                                    {api.description}
                                  </p>
                                )}
                                <p style={{fontSize: '12px', color: 'var(--text-secondary)'}}>
                                  Added: {new Date(api.date_added).toLocaleDateString()} | 
                                  {schemas.length} version{schemas.length !== 1 ? 's' : ''}
                                </p>
                              </div>
                              
                              <div style={{display: 'flex', gap: '8px', alignItems: 'center'}}>
                                {/* Scan Button for registered APIs */}
                                {api.id.toString().length < 10 && schemas.length > 0 && (
                                  <button 
                                    className="btn btn-secondary"
                                    onClick={() => scanApi(api.id)}
                                    disabled={monitoring}
                                    style={{padding: '6px 12px', fontSize: '12px'}}
                                  >
                                    {monitoring ? 'Scanning...' : 'Scan'}
                                  </button>
                                )}
                                
                                {/* Rescan Button for all APIs */}
                                <button 
                                  className="btn btn-secondary"
                                  onClick={() => rescanApi(api)}
                                  disabled={monitoring}
                                  style={{padding: '6px 12px', fontSize: '12px'}}
                                  title="Rescan API schema and add new version"
                                >
                                  {monitoring ? 'Rescanning...' : 'Rescan'}
                                </button>
                                <button
                                  className="btn btn-secondary"
                                  onClick={() => toggleApiExpansion(api.id)}
                                  style={{padding: '6px 12px', fontSize: '12px'}}
                                >
                                  {isExpanded ? '▼' : '▶'} {schemas.length} Version{schemas.length !== 1 ? 's' : ''}
                                </button>
                              </div>
                            </div>
                            
                            {/* Version Dropdown */}
                            {isExpanded && schemas.length > 0 && (
                              <div style={{marginTop: '16px', borderTop: '1px solid var(--border)', paddingTop: '16px'}}>
                                <h5 style={{marginBottom: '12px', color: 'var(--text-primary)'}}>Schema Versions</h5>
                                <div style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
                                  {schemas.map((schema, index) => {
                                    const isLatest = index === 0;
                                    const canCompare = !isLatest && schemas.length > 1;
                                    
                                    return (
                                      <div 
                                        key={schema.id} 
                                        style={{
                                          padding: '12px',
                                          background: isLatest ? 'var(--success-bg)' : 'var(--background-secondary)',
                                          borderRadius: '6px',
                                          border: isLatest ? '1px solid var(--success)' : '1px solid var(--border)'
                                        }}
                                      >
                                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                                          <div>
                                            <h6 style={{margin: '0 0 4px 0', color: 'var(--text-primary)'}}>
                                              Version {schema.version_number} {isLatest && '(Latest)'}
                                            </h6>
                                            <p style={{fontSize: '11px', color: 'var(--text-secondary)', margin: '0'}}>
                                              {formatTimestamp(schema.timestamp)}
                                            </p>
                                          </div>
                                          
                                          <div style={{display: 'flex', gap: '8px'}}>
                                            {canCompare && (
                                              <button 
                                                className="btn btn-secondary"
                                                onClick={() => compareSchemas(api.id, schema.version_number, schemas[0].version_number)}
                                                style={{padding: '4px 8px', fontSize: '10px'}}
                                              >
                                                Compare with Latest
                                              </button>
                                            )}
                                            <details>
                                              <summary style={{cursor: 'pointer', fontSize: '10px'}}>View Schema</summary>
                                              <pre style={{maxHeight: '200px', overflow: 'auto', fontSize: '10px', marginTop: '8px'}}>
                                                {JSON.stringify(schema.schema_json, null, 2)}
                                              </pre>
                                            </details>
                                          </div>
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}
                            
                            {/* Empty State for No Versions */}
                            {isExpanded && schemas.length === 0 && (
                              <div style={{marginTop: '16px', borderTop: '1px solid var(--border)', paddingTop: '16px'}}>
                                <p style={{textAlign: 'center', color: 'var(--text-secondary)', fontSize: '13px'}}>
                                  No schema versions yet. Click "Rescan" to discover the API schema.
                                </p>
                              </div>
                            )}
                            
                            {/* Single Version State */}
                            {isExpanded && schemas.length === 1 && (
                              <div style={{marginTop: '16px', borderTop: '1px solid var(--border)', paddingTop: '16px'}}>
                                <p style={{textAlign: 'center', color: 'var(--text-secondary)', fontSize: '13px'}}>
                                  Only one schema version exists. <strong>Rescan</strong> the API to create more versions for comparison.
                                </p>
                              </div>
                            )}
                          </ResultCard>
                        );
                      })}
                    </div>
                  )}
                  
                  {/* Schema Changes */}
                  {schemaChanges.length > 0 && (
                    <div style={{marginTop: '24px'}} data-changes-section="true">
                      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px'}}>
                        <h4 style={{margin: '0', color: 'var(--text-primary)'}}>
                          Schema Changes ({schemaChanges.length})
                        </h4>
                        <button 
                          className="btn btn-secondary"
                          onClick={() => setSchemaChanges([])}
                          style={{padding: '4px 12px', fontSize: '12px'}}
                        >
                          Clear
                        </button>
                      </div>
                      <ResultCard>
                        {/* Group changes by category */}
                        {['endpoint', 'parameter', 'response', 'authentication', 'schema'].map(category => {
                          const categoryChanges = schemaChanges.filter(change => change.category === category);
                          if (categoryChanges.length === 0) return null;
                          
                          return (
                            <div key={category} style={{marginBottom: '20px'}}>
                              <h5 style={{margin: '0 0 12px 0', color: 'var(--text-primary)', textTransform: 'capitalize'}}>
                                {category} Changes ({categoryChanges.length})
                              </h5>
                              <div style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
                                {categoryChanges.map((change, index) => (
                                  <div 
                                    key={index}
                                    className={`endpoint-test ${change.type === 'removed' || change.severity === 'critical' ? 'failed' : ''}`}
                                    style={{padding: '12px', border: '1px solid var(--border)', borderRadius: '6px'}}
                                  >
                                    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px'}}>
                                      <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                                        <span className={`status ${
                                          change.severity === 'critical' ? 'error' : 
                                          change.severity === 'high' ? 'error' : 
                                          change.severity === 'medium' ? 'warning' : 
                                          'success'
                                        }`}>
                                          {change.type.toUpperCase()} - {change.severity.toUpperCase()}
                                        </span>
                                        <span style={{
                                          background: change.severity === 'critical' ? '#dc3545' : 
                                                     change.severity === 'high' ? '#fd7e14' : 
                                                     change.severity === 'medium' ? '#ffc107' : 
                                                     '#28a745',
                                          color: 'white',
                                          fontSize: '10px',
                                          padding: '2px 6px',
                                          borderRadius: '4px',
                                          fontWeight: 'bold'
                                        }}>
                                          {change.severity.toUpperCase()}
                                        </span>
                                      </div>
                                    </div>
                                    <div className="test-details">
                                      <p style={{margin: '0 0 8px 0', fontWeight: 'bold', color: 'var(--text-primary)'}}>
                                        {change.details}
                                      </p>
                                      <p style={{margin: '0', fontSize: '12px', color: 'var(--text-secondary)'}}>
                                        <strong>Path:</strong> {change.path} | 
                                        <strong>Category:</strong> {change.category}
                                      </p>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          );
                        }).filter(Boolean)}
                      </ResultCard>
                    </div>
                  )}
                </div>
              )}
              
              {/* Response Tab (Body) */}
              {activeTab === 'body' && (
                <div>
                  <h3 style={{marginBottom: '20px', color: 'var(--text-primary)'}}>Request Body</h3>
                  <div className="form-group">
                    <textarea 
                      className="focus-ring"
                      placeholder="Enter request body (JSON, XML, etc.)" 
                      rows="8"
                    />
                  </div>
                  
                  {lastResponse && (
                    <ResultCard title="API Response">
                      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px'}}>
                        <div>
                          <label style={{fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '8px'}}>Status</label>
                          <div style={{
                            color: lastResponse.status >= 200 && lastResponse.status < 300 ? 'var(--success)' : 'var(--error)', 
                            fontWeight: 'bold',
                            fontSize: '16px'
                          }}>
                            {lastResponse.status}
                          </div>
                        </div>
                        <div>
                          <label style={{fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '8px'}}>Response Time</label>
                          <div style={{fontSize: '14px', color: 'var(--text-primary)'}}>
                            {formatTimestamp(lastResponse.timestamp)}
                          </div>
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
                    </ResultCard>
                  )}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default App;
