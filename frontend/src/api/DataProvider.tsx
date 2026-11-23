import { FormEvent, ReactNode, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, clearSession, ensureIngestKey, errorMessage, getToken, setToken } from './client';
import * as A from './adapters';

const REFRESH_MS = 15000;
const NONE: never[] = [];

// Live data for the app surface. Returns the same shapes the demo used,
// plus `errors` so the UI can say what is unavailable instead of showing zeros.
export function useLogiqData() {
  const services = useQuery({
    queryKey: ['logiq', 'services'],
    queryFn: async () => A.adaptServices((await api.get('/v1/analytics/services', { params: { hours: 24 } })).data),
    refetchInterval: REFRESH_MS,
  });
  const anomalies = useQuery({
    queryKey: ['logiq', 'anomalies'],
    queryFn: async () => A.adaptAnomalies((await api.get('/v1/anomalies', { params: { limit: 100 } })).data),
    refetchInterval: REFRESH_MS,
  });
  const templates = useQuery({
    queryKey: ['logiq', 'templates'],
    queryFn: async () => A.adaptTemplates((await api.get('/v1/templates', { params: { limit: 100 } })).data),
    refetchInterval: REFRESH_MS,
  });
  const logs = useQuery({
    queryKey: ['logiq', 'logs'],
    queryFn: async () => A.adaptLogs((await api.get('/v1/logs', { params: { limit: 100 } })).data),
    refetchInterval: REFRESH_MS,
  });
  const timeline = useQuery({
    queryKey: ['logiq', 'timeline'],
    queryFn: async () =>
      A.adaptTimeline((await api.get('/v1/analytics/timeseries', { params: { hours: 2, interval: 'minute' } })).data),
    refetchInterval: REFRESH_MS,
  });
  const datasets = useQuery({
    queryKey: ['logiq', 'datasets'],
    queryFn: async () => {
      const key = await ensureIngestKey();
      return A.adaptDatasets((await api.get('/v1/datasets', { headers: { 'X-API-Key': key } })).data);
    },
    refetchInterval: REFRESH_MS,
  });

  const queries = { services, anomalies, templates, logs, timeline, datasets };
  const errors = Object.entries(queries)
    .filter(([, q]) => q.isError)
    .map(([name, q]) => `${name}: ${errorMessage(q.error)}`);

  return {
    services: services.data ?? NONE,
    anomalies: anomalies.data ?? NONE,
    templates: templates.data ?? NONE,
    logs: logs.data ?? NONE,
    timeline: timeline.data ?? NONE,
    datasets: datasets.data ?? NONE,
    // No backend endpoint yet (needs Prometheus / source registry). Shown as unavailable.
    platformHealth: NONE,
    sources: NONE,
    loading: Object.values(queries).some((q) => q.isLoading),
    errors,
  };
}

// Wraps the app surface: shows a login/register form until a JWT is stored.
export function LogiqSession({ children }: { children: ReactNode }) {
  const [authed, setAuthed] = useState(() => !!getToken());
  const queryClient = useQueryClient();

  if (!authed) {
    return <LoginGate onAuthenticated={() => setAuthed(true)} />;
  }

  const signOut = () => {
    clearSession();
    queryClient.clear();
    setAuthed(false);
  };

  return (
    <>
      {children}
      <button
        onClick={signOut}
        style={{ position: 'fixed', bottom: 12, right: 12, zIndex: 50, fontSize: 12, padding: '6px 10px',
          borderRadius: 8, border: '1px solid #303438', background: '#14171A', color: '#A1A5A5', cursor: 'pointer' }}
      >
        Sign out
      </button>
    </>
  );
}

function LoginGate({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [tenantName, setTenantName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const path = mode === 'register' ? '/v1/auth/register' : '/v1/auth/login';
      const payload = mode === 'register' ? { email, password, tenant_name: tenantName } : { email, password };
      const { data } = await api.post(path, payload);
      setToken(data.access_token);
      onAuthenticated();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const input = { width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid #303438',
    background: '#0E1113', color: '#E6E9EA', marginTop: 4, marginBottom: 12, boxSizing: 'border-box' as const };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#0A0C0E', padding: 16, fontFamily: 'inherit' }}>
      <form onSubmit={submit} style={{ width: 360, maxWidth: '100%', padding: 28, borderRadius: 16,
        border: '1px solid #252A2E', background: '#121518', color: '#E6E9EA' }}>
        <div style={{ width: 40, height: 40, borderRadius: 10, background: '#8FBE9F', color: '#0A0C0E',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, marginBottom: 16 }}>L</div>
        <h1 style={{ fontSize: 20, margin: '0 0 4px' }}>{mode === 'login' ? 'Sign in to LogIQ' : 'Create a LogIQ tenant'}</h1>
        <p style={{ color: '#747A7D', fontSize: 13, margin: '0 0 20px' }}>
          Your session token stays in this browser only.
        </p>
        <label style={{ fontSize: 12, color: '#A1A5A5' }}>Email</label>
        <input style={input} type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <label style={{ fontSize: 12, color: '#A1A5A5' }}>Password</label>
        <input style={input} type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
        {mode === 'register' && (
          <>
            <label style={{ fontSize: 12, color: '#A1A5A5' }}>Tenant name</label>
            <input style={input} required value={tenantName} onChange={(e) => setTenantName(e.target.value)} />
          </>
        )}
        {error && <p style={{ color: '#D77F7F', fontSize: 13, margin: '0 0 12px' }}>{error}</p>}
        <button disabled={busy} type="submit" style={{ width: '100%', padding: 11, borderRadius: 8, border: 0,
          background: '#8FBE9F', color: '#0A0C0E', fontWeight: 600, cursor: busy ? 'wait' : 'pointer' }}>
          {busy ? 'Working…' : mode === 'login' ? 'Sign in' : 'Register'}
        </button>
        <button type="button" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
          style={{ width: '100%', marginTop: 12, background: 'none', border: 0, color: '#91AFC7', cursor: 'pointer', fontSize: 13 }}>
          {mode === 'login' ? 'No account yet? Register' : 'Have an account? Sign in'}
        </button>
      </form>
    </div>
  );
}
