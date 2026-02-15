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
};

export type ApiEndpoint = keyof typeof API_PATHS;
