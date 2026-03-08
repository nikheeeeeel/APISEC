/// <reference types="vite/client" />
const rawBasePath = (import.meta.env.VITE_API_BASE_PATH ?? '/api').trim();
const ensureLeadingSlash = rawBasePath.startsWith('/') ? rawBasePath : `/${rawBasePath}`;
const normalizedBasePath = ensureLeadingSlash.replace(/\/+$/, '') || '/';

const buildEndpoint = (suffix: string) => {
  const normalizedSuffix = suffix.startsWith('/') ? suffix : `/${suffix}`;
  return `${normalizedBasePath}${normalizedSuffix}`;
};

export const API_PATHS = {
  base: normalizedBasePath,
  infer: buildEndpoint('/infer'),
  spec: buildEndpoint('/spec'),
  health: buildEndpoint('/health'),
  
  // API Registry
  apis: buildEndpoint('/apis'),
  apiDetail: (id: number) => buildEndpoint(`/apis/${id}`),
  
  // Schema Monitor
  scanApi: (id: number) => buildEndpoint(`/apis/${id}/scan`),
  scanApiStream: (id: number) => buildEndpoint(`/apis/${id}/scan/stream`),
  rescanApi: (id: number) => buildEndpoint(`/apis/${id}/rescan`),
  rescanApiStream: (id: number) => buildEndpoint(`/apis/${id}/rescan/stream`),
  schemaVersions: (id: number) => buildEndpoint(`/apis/${id}/schemas`),
  schemaVersion: (id: number, version: number) => buildEndpoint(`/apis/${id}/schemas/${version}`),
  compareSchemas: (id: number) => buildEndpoint(`/apis/${id}/compare`),
  downloadSchema: (id: number, version: number) => buildEndpoint(`/apis/${id}/schemas/${version}/download`),
  downloadPdf: (id: number, version: number) => buildEndpoint(`/apis/${id}/schemas/${version}/pdf`),
};

export type ApiEndpoint = keyof typeof API_PATHS;

export interface RegisteredApi {
  id: number;
  name: string;
  base_url: string;
  description: string | null;
  date_added: string;
}

export interface SchemaSnapshot {
  id: number;
  api_id: number;
  version_number: number;
  schema_json: Record<string, unknown>;
  schema_pdf: string | null;
  timestamp: string;
}

export interface SchemaChange {
  type: 'added' | 'removed' | 'modified';
  category: 'endpoint' | 'parameter' | 'response' | 'authentication';
  severity: 'critical' | 'high' | 'medium' | 'low';
  details: string;
  path?: string;
}

export interface SchemaComparison {
  from_version: number;
  to_version: number;
  changes: SchemaChange[];
  identical: boolean;
}
