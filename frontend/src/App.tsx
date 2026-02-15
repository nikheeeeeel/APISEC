import { useState } from 'react';
import { API_PATHS } from './lib/api';
import V2InferenceForm from './components/V2InferenceForm';
import V2ResultsDisplay from './components/V2ResultsDisplay';

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

function App() {
  const [results, setResults] = useState<V2InferenceResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (requestData: any) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(API_PATHS.infer, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: V2InferenceResult = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSpecGeneration = async (requestData: any) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(API_PATHS.spec, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const specData = await response.json();
      
      // Download the OpenAPI spec
      const blob = new Blob([JSON.stringify(specData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'openapi-spec.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            REST Parameter Discovery v2
          </h1>
          <p className="text-lg text-gray-600">
            Enhanced API parameter discovery with differential analysis, location resolution, and weighted confidence scoring
          </p>
        </div>

        <V2InferenceForm
          onSubmit={handleSubmit}
          onSpecGeneration={handleSpecGeneration}
          isLoading={isLoading}
        />

        {error && (
          <div className="mt-6">
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 111-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Error</h3>
                  <div className="mt-2 text-sm text-red-700">
                    <p>{error}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {results && (
          <div className="mt-6">
            <V2ResultsDisplay results={results} />
          </div>
        )}

        {/* Footer */}
        <div className="mt-12 text-center text-gray-500 text-sm">
          <p>REST Parameter Discovery v2 - Enhanced API Analysis</p>
          <p className="mt-1">Features: Differential Analysis • Location Resolution • Weighted Scoring • Framework Detection</p>
        </div>
      </div>
    </div>
  );
}

export default App;
