import axios from 'axios';

export const TOKEN_KEY = 'logiq_token';
export const INGEST_KEY = 'logiq_ingestion_key';

// Every call goes through nginx at /api, which proxies to the gateway.
export const api = axios.create({ baseURL: '/api' });

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Storage can throw in private windows or with blocked site data; never let it break the UI.
function safeGet(store: Storage, key: string): string | null {
  try { return store.getItem(key); } catch { return null; }
}
function safeSet(store: Storage, key: string, value: string) {
  try { store.setItem(key, value); } catch { /* storage unavailable */ }
}
function safeRemove(store: Storage, key: string) {
  try { store.removeItem(key); } catch { /* storage unavailable */ }
}

export const getToken = () => safeGet(localStorage, TOKEN_KEY);
export const setToken = (token: string) => safeSet(localStorage, TOKEN_KEY, token);

export function clearSession() {
  safeRemove(localStorage, TOKEN_KEY);
  safeRemove(sessionStorage, INGEST_KEY);
}

// Dataset endpoints authenticate with an ingestion API key, not the JWT.
// Create one once per browser session and reuse it.
export async function ensureIngestKey(): Promise<string> {
  const existing = safeGet(sessionStorage, INGEST_KEY);
  if (existing) return existing;
  const { data } = await api.post('/v1/api-keys', { label: 'logiq-ui-ingest' });
  safeSet(sessionStorage, INGEST_KEY, data.api_key);
  return data.api_key;
}

export function errorMessage(error: unknown): string {
  const detail = (error as any)?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d: any) => d.msg).join('; ');
  return (error as any)?.message || 'Request failed';
}
