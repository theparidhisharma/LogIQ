// Maps backend responses onto the shapes the demo UI was built against.
// Fields the backend does not produce yet are returned as '—' or empty arrays,
// never as made-up numbers.

type Row = Record<string, any>;

const rows = (payload: any): Row[] => (Array.isArray(payload?.items) ? payload.items : []);

// Postgres timestamps can arrive without a zone; they are UTC.
function toDate(iso?: string | null): Date | null {
  if (!iso) return null;
  const hasZone = /([zZ]|[+-]\d\d:?\d\d)$/.test(iso);
  const d = new Date(hasZone ? iso : `${iso}Z`);
  return isNaN(d.getTime()) ? null : d;
}

export function formatUtc(iso?: string | null): string {
  const d = toDate(iso);
  return d ? `${d.toISOString().replace('T', ' ').slice(0, 19)} UTC` : '—';
}

export function relativeTime(iso?: string | null): string {
  const d = toDate(iso);
  if (!d) return '—';
  const s = Math.max(0, Math.round((Date.now() - d.getTime()) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return `${Math.round(s / 86400)}d ago`;
}

const hhmm = (iso?: string | null) => {
  const d = toDate(iso);
  return d ? d.toISOString().slice(11, 16) : '—';
};

function formatBytes(n?: number | null): string {
  const v = Number(n || 0);
  if (v < 1024) return `${v} B`;
  if (v < 1024 ** 2) return `${(v / 1024).toFixed(1)} KB`;
  if (v < 1024 ** 3) return `${(v / 1024 ** 2).toFixed(1)} MB`;
  return `${(v / 1024 ** 3).toFixed(2)} GB`;
}

const num = (n: unknown) => Number(n || 0).toLocaleString('en-US');

export function adaptServices(payload: any) {
  return rows(payload).map((r) => {
    const rate = Number(r.error_rate || 0);
    return {
      id: r.service_name,
      name: r.service_name,
      status: rate >= 0.05 ? 'degraded' : rate >= 0.01 ? 'warning' : 'healthy',
      logVolume: num(r.event_count),
      errorRate: `${(rate * 100).toFixed(2)}%`,
      baselineDelta: '—',
      lastSeen: relativeTime(r.last_seen),
      owner: `${r.application_count ?? 0} application(s)`,
      runtime: 'Not reported',
    };
  });
}

export function adaptAnomalies(payload: any) {
  return rows(payload).map((r) => ({
    id: String(r.id),
    title: r.description || r.kind,
    kind: r.kind,
    service: r.service_name,
    severity: String(r.severity || 'unknown').toLowerCase(),
    status: String(r.status || 'open').toLowerCase(),
    firstObserved: formatUtc(r.first_seen),
    lastObserved: formatUtc(r.last_seen),
    changeSummary: `${r.kind} · ${r.occurrence_count ?? 0} occurrence(s)`,
    summary: r.description || '',
    changedTemplates: [],
    correlatedTraceIds: [],
    correlatedRequestIds: [],
  }));
}

export function adaptTemplates(payload: any) {
  return rows(payload).map((r) => ({
    id: r.template_id,
    service: r.service_name,
    tag: 'Observed',
    template: r.template,
    frequency: `${num(r.frequency)} total`,
    trend: '—',
    firstSeen: formatUtc(r.first_seen),
    lastSeen: relativeTime(r.last_seen),
    sparkline: [],
    parameters: [],
    examples: [],
  }));
}

export function adaptLogs(payload: any) {
  return rows(payload).map((r) => ({
    id: r.event_id,
    timestamp: r.timestamp,
    severity: String(r.severity || 'INFO').toUpperCase(),
    service: r.service_name,
    templateId: r.template_id,
    template: r.template || r.message,
    message: r.message,
    traceId: r.trace_id || '—',
    requestId: r.request_id || '—',
    source: r.source_type || 'unknown',
    parameters: r.attributes || {},
    attributes: r.attributes || {},
  }));
}

export function adaptTimeline(payload: any) {
  return rows(payload).map((r) => ({
    time: hhmm(r.bucket),
    total: Number(r.events || 0),
    errors: Number(r.errors || 0),
  }));
}

const DATASET_STATUS: Record<string, string> = {
  completed: 'ready',
  failed: 'failed',
  queued: 'processing',
  processing: 'processing',
};

export function adaptDatasets(payload: any) {
  return rows(payload).map((r) => ({
    id: r.id,
    name: r.name,
    sourceType: r.source_type,
    uploadStatus: 'Uploaded',
    processingStatus: DATASET_STATUS[r.status] ?? r.status,
    size: formatBytes(r.byte_size),
    recordCount: num(r.line_count),
    createdAt: formatUtc(r.created_at),
    errorDetail: r.error_message || '',
  }));
}
