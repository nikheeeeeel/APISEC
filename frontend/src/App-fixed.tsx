import { useState } from 'react';
import { API_PATHS } from './lib/api';

interface InferenceResult {
  url: string;
  method: string;
  parameters: Parameter[];
  meta: {
    total_parameters: number;
    partial_failures: number;
    execution_time_ms: number;
    adaptive_inference?: {
      endpoint_classification?: {
        endpoint_type: string;
        strategy: any;
      };
      content_type_detection?: {
        preferred_strategy: string;
        detected_types: string[];
      };
    };
  };
}

interface Parameter {
  name: string;
  location: string;
  required: boolean;
  type: string;
  nullable: boolean;
  confidence: number;
  evidence: Evidence[];
}

interface Evidence {
  error_text?: string;
  status_code?: number;
  pattern?: string;
  content_type?: string;
  tested_value?: string;
}

function App() {
  const [url, setUrl] = useState('');
  const [method, setMethod] = useState('POST');
  const [timeLimit, setTimeLimit] = useState(30);
  const [results, setResults] = useState<InferenceResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showResults, setShowResults] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!url.trim()) {
      setError('Please enter a valid URL');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(API_PATHS.infer, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: url.trim(),
          method: method,
          time: timeLimit,
        }),
      });

      if (!response.ok) {
        throw new Error(`Inference failed: ${response.statusText}`);
      }

      const result = await response.json();
      setResults(result);
      setShowResults(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const downloadJSON = (data: any, filename: string) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const isValidUrl = (urlString: string) => {
    try {
      const url = new URL(urlString);
      return url.protocol === 'http:' || url.protocol === 'https:';
    } catch {
      return false;
    }
  };

  const isFormValid = url.trim() && isValidUrl(url);

  const handleNewInference = () => {
    setResults(null);
    setShowResults(false);
    setError(null);
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#0f172a', color: '#ffffff', fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1 style={{ color: '#ffffff', marginBottom: '1rem', fontSize: '2rem', fontWeight: 'bold' }}>🚀 APISec</h1>
          <p style={{ color: '#e2e8f0', marginBottom: '2rem', fontSize: '1.1rem' }}>Advanced API Parameter Discovery with Enhanced Architecture</p>
        </div>
        
        {/* Form Section */}
        <div style={{ marginBottom: '2rem', backgroundColor: '#2d3748', padding: '1.5rem', borderRadius: '8px' }}>
          <h2 style={{ color: '#ffffff', marginBottom: '1rem' }}>🔍 Parameter Inference</h2>
          
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ color: '#ffffff', marginBottom: '0.5rem', fontSize: '0.9rem', fontWeight: '500' }}>Target URL</label>
              <input
                type="url"
                placeholder="https://api.example.com/endpoint"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  backgroundColor: '#1e293b',
                  border: '1px solid #374151',
                  borderRadius: '4px',
                  color: '#ffffff',
                  fontSize: '0.9rem'
                }}
                required
              />
              {url && !isValidUrl(url) && (
                <p style={{ color: '#ef4444', fontSize: '0.8rem', marginTop: '0.5rem' }}>
                  Please enter a valid URL with http:// or https://
                </p>
              )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ color: '#ffffff', marginBottom: '0.5rem', fontSize: '0.9rem', fontWeight: '500' }}>HTTP Method</label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  backgroundColor: '#1e293b',
                  border: '1px solid #374151',
                  borderRadius: '4px',
                  color: '#ffffff',
                  fontSize: '0.9rem'
                }}
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="DELETE">DELETE</option>
                <option value="PATCH">PATCH</option>
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ color: '#ffffff', marginBottom: '0.5rem', fontSize: '0.9rem', fontWeight: '500' }}>Time Limit (seconds)</label>
              <input
                type="number"
                min="1"
                max="120"
                value={timeLimit}
                onChange={(e) => setTimeLimit(Number(e.target.value))}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  backgroundColor: '#1e293b',
                  border: '1px solid #374151',
                  borderRadius: '4px',
                  color: '#ffffff',
                  fontSize: '0.9rem'
                }}
                required
              />
            </div>
          </form>

          {error && (
            <div style={{ padding: '1rem', backgroundColor: '#7f1d1d', border: '1px solid #dc2626', borderRadius: '4px', marginBottom: '1rem' }}>
              <p style={{ color: '#fca5a5', fontSize: '0.9rem' }}>Error: {error}</p>
            </div>
          )}

          <button
            type="submit"
            onClick={handleSubmit}
            disabled={!isFormValid || isLoading}
            style={{
              width: '100%',
              padding: '0.75rem',
              backgroundColor: isLoading ? '#6b7280' : '#10b981',
              border: '1px solid #374151',
              borderRadius: '4px',
              color: '#ffffff',
              fontSize: '1rem',
              fontWeight: '500',
              cursor: isLoading ? 'not-allowed' : 'pointer'
            }}
          >
            {isLoading ? 'Running Inference...' : 'Run Inference'}
          </button>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div style={{ textAlign: 'center', padding: '2rem', backgroundColor: '#2d3748', borderRadius: '8px', marginTop: '2rem' }}>
            <div style={{ display: 'inline-block', width: '40px', height: '40px', border: '4px solid #374151', borderRadius: '50%', animation: 'spin 1s linear infinite' }}>
              <div style={{ width: '20px', height: '20px', border: '2px solid #ffffff', borderRadius: '50%', borderTop: '2px solid #374151' }}></div>
            </div>
            <p style={{ color: '#ffffff', marginTop: '1rem' }}>Running adaptive inference...</p>
          </div>
        )}

        {/* Results Section */}
        {showResults && results && (
          <div style={{ marginBottom: '2rem', backgroundColor: '#2d3748', padding: '1.5rem', borderRadius: '8px' }}>
            <h2 style={{ color: '#ffffff', marginBottom: '1rem' }}>🎯 Inference Results</h2>
            
            <div style={{ marginBottom: '1rem', backgroundColor: '#1e293b', padding: '1rem', borderRadius: '8px' }}>
              <h3 style={{ color: '#ffffff', marginBottom: '0.5rem' }}>Discovered {results.parameters?.length || 0} parameters</h3>
              <p style={{ color: '#e2e8f0', fontSize: '0.9rem' }}>Execution time: {results.meta?.execution_time_ms || 0}ms</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
              {results.parameters?.map((param, index) => (
                <div key={index} style={{ 
                  backgroundColor: '#1e293b', 
                  padding: '1rem', 
                  borderRadius: '8px',
                  border: '1px solid #374151'
                }}>
                  <div style={{ marginBottom: '0.5rem' }}>
                    <strong style={{ color: '#ffffff' }}>{param.name}</strong>
                    <div style={{ fontSize: '0.8rem', color: '#a5b4fc' }}>
                      {param.location} • {param.type} • {param.required ? 'Required' : 'Optional'} • {(param.confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                  {param.evidence && param.evidence.length > 0 && (
                    <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#666' }}>
                      <strong>Evidence:</strong>
                      <div style={{ maxHeight: '100px', overflow: 'auto', backgroundColor: '#0f172a', padding: '0.5rem', borderRadius: '4px', fontSize: '0.7rem' }}>
                        {param.evidence.slice(0, 2).map((evidence, i) => (
                          <div key={i} style={{ marginBottom: '0.25rem', padding: '0.5rem', backgroundColor: '#0f172a', borderRadius: '4px' }}>
                            <strong>Status {evidence.status_code}:</strong> {evidence.error_text?.substring(0, 100)}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between' }}>
              <button
                onClick={() => downloadJSON(results, 'inference-results.json')}
                style={{
                  padding: '0.75rem 1.5rem',
                  backgroundColor: '#10b981',
                  border: '1px solid #374151',
                  borderRadius: '4px',
                  color: '#ffffff',
                  fontSize: '0.9rem',
                  cursor: 'pointer'
                }}
              >
                📥 Download Results
              </button>
              <button
                onClick={() => downloadJSON(results, 'openapi-spec.json')}
                style={{
                  padding: '0.75rem 1.5rem',
                  backgroundColor: '#10b981',
                  border: '1px solid #374151',
                  borderRadius: '4px',
                  color: '#ffffff',
                  fontSize: '0.9rem',
                  cursor: 'pointer'
                }}
              >
                📋 Download OpenAPI Spec
              </button>
            </div>
          </div>
        )}

        {/* New Inference Button */}
        <div style={{ textAlign: 'center', marginTop: '2rem' }}>
          <button
            onClick={handleNewInference}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#10b981',
              border: '1px solid #374151',
              borderRadius: '4px',
              color: '#ffffff',
              fontSize: '1rem',
              cursor: 'pointer'
            }}
          >
            🔄 New Inference
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
