import React, { useState } from 'react';
import { apiService } from '../services/api';

const ApiForm = ({ onSuccess, onError }) => {
  const [apiUri, setApiUri] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [bearerToken, setBearerToken] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showAuth, setShowAuth] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!apiUri.trim()) {
      onError('Please enter an API URI');
      return;
    }

    setIsLoading(true);
    
    try {
      const result = await apiService.generateDocs(
        apiUri,
        apiKey || null,
        bearerToken || null
      );
      onSuccess(result);
      
      // Reset form
      setApiUri('');
      setApiKey('');
      setBearerToken('');
      setShowAuth(false);
    } catch (error) {
      onError(error.message || 'Failed to generate documentation');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ marginBottom: '24px' }}>
      <div style={{ marginBottom: '16px' }}>
        <label htmlFor="apiUri" style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
          API Base URI *
        </label>
        <input
          id="apiUri"
          type="url"
          value={apiUri}
          onChange={(e) => setApiUri(e.target.value)}
          placeholder="https://api.example.com"
          required
          disabled={isLoading}
          style={{
            width: '100%',
            padding: '10px',
            fontSize: '14px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            boxSizing: 'border-box',
          }}
        />
      </div>

      <div style={{ marginBottom: '16px' }}>
        <button
          type="button"
          onClick={() => setShowAuth(!showAuth)}
          style={{
            background: 'none',
            border: 'none',
            color: '#007bff',
            cursor: 'pointer',
            textDecoration: 'underline',
            fontSize: '14px',
            padding: 0,
          }}
        >
          {showAuth ? 'Hide' : 'Show'} Authorization (Optional)
        </button>
      </div>

      {showAuth && (
        <div style={{ marginBottom: '16px', padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '4px' }}>
          <div style={{ marginBottom: '12px' }}>
            <label htmlFor="apiKey" style={{ display: 'block', marginBottom: '8px' }}>
              API Key
            </label>
            <input
              id="apiKey"
              type="text"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="X-API-Key header value"
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '10px',
                fontSize: '14px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div>
            <label htmlFor="bearerToken" style={{ display: 'block', marginBottom: '8px' }}>
              Bearer Token
            </label>
            <input
              id="bearerToken"
              type="text"
              value={bearerToken}
              onChange={(e) => setBearerToken(e.target.value)}
              placeholder="Bearer token"
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '10px',
                fontSize: '14px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                boxSizing: 'border-box',
              }}
            />
          </div>
        </div>
      )}

      <button
        type="submit"
        disabled={isLoading}
        style={{
          padding: '12px 24px',
          fontSize: '16px',
          fontWeight: 'bold',
          color: 'white',
          backgroundColor: isLoading ? '#6c757d' : '#007bff',
          border: 'none',
          borderRadius: '4px',
          cursor: isLoading ? 'not-allowed' : 'pointer',
          width: '100%',
        }}
      >
        {isLoading ? 'Generating...' : 'Generate Documentation'}
      </button>
    </form>
  );
};

export default ApiForm;
