import React, { useState, useEffect, useMemo, useRef } from 'react';
import { LogiqSession, useLogiqData } from './api/DataProvider';
import {
  Activity, AlertTriangle, ArrowRight, ArrowUpRight, BookOpen, Box,
  Check, CheckCircle2, ChevronDown, ChevronRight, Clock, Code2,
  Copy, Cpu, Database, Download, ExternalLink, FileCode, FileText,
  Filter, FolderOpen, GitBranch, Globe, HardDrive, HelpCircle,
  Info, Layers, LayoutGrid, ListFilter, Menu, Play, RefreshCw,
  Search, Server, Settings, Shield, Sliders, Sparkles, Terminal,
  Upload, X, ZoomIn, ZoomOut, Maximize2, RotateCcw, Eye, EyeOff
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  Tooltip as RechartsTooltip, CartesianGrid, ReferenceLine, LineChart, Line
} from 'recharts';

/**
 * ============================================================================
 * GSAP LOADER & MOTION HOOKS (Editorial Engineering Precision)
 * Dynamically loads GSAP + ScrollTrigger from CDN with graceful fallback.
 * ============================================================================
 */
const useGsapEngine = () => {
  const [gsapReady, setGsapReady] = useState(() => Boolean(window.gsap && window.ScrollTrigger));

  useEffect(() => {
    if (window.gsap && window.ScrollTrigger) {
      window.gsap.registerPlugin(window.ScrollTrigger);
      setGsapReady(true);
      return;
    }

    const loadScript = (src) =>
      new Promise((resolve, reject) => {
        const existing = document.querySelector(`script[src="${src}"]`);
        if (existing) {
          if (window.gsap && src.includes('gsap.min.js')) {
            resolve();
            return;
          }
          if (window.ScrollTrigger && src.includes('ScrollTrigger.min.js')) {
            resolve();
            return;
          }
          existing.addEventListener('load', resolve);
          existing.addEventListener('error', reject);
          return;
        }
        const s = document.createElement('script');
        s.src = src;
        s.async = true;
        s.onload = resolve;
        s.onerror = reject;
        document.head.appendChild(s);
      });

    let mounted = true;
    loadScript('https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js')
      .then(() => loadScript('https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js'))
      .then(() => {
        if (!mounted) return;
        if (window.gsap && window.ScrollTrigger) {
          window.gsap.registerPlugin(window.ScrollTrigger);
          setGsapReady(true);
        }
      })
      .catch(() => {});

    return () => {
      mounted = false;
    };
  }, []);

  return gsapReady;
};

/**
 * ============================================================================
 * LOGIQ DESIGN SYSTEM & DATA MODEL
 * Editorial Engineering: Near-black (#101112), warm charcoal (#151719 / #1B1D1F),
 * crisp 1px borders (#303438), muted sage green accent (#A6C8B5).
 * ============================================================================
 */

const ARCHITECTURE_LAYERS = [
  {
    id: 'layer-1',
    name: 'Layer 1 — External Data Sources',
    subtitle: 'Origins of application telemetry and static log datasets',
    boundary: 'monitored'
  },
  {
    id: 'layer-2',
    name: 'Layer 2 — Collection & API Access',
    subtitle: 'Ingestion entry points, validation, and source registration',
    boundary: 'monitored'
  },
  {
    id: 'layer-3',
    name: 'Layer 3 — Message Transport & Processing',
    subtitle: 'Asynchronous decoupling, normalization, and template extraction',
    boundary: 'monitored'
  },
  {
    id: 'layer-4',
    name: 'Layer 4 — Intelligence & Analytics',
    subtitle: 'Pattern frequency tracking, anomaly detection, and service aggregates',
    boundary: 'monitored'
  },
  {
    id: 'layer-5',
    name: 'Layer 5 — Persistence & State Storage',
    subtitle: 'Structured relational records, object storage, and fast-access cache',
    boundary: 'monitored'
  },
  {
    id: 'layer-6',
    name: 'Layer 6 — LOGIQ Web Application',
    subtitle: 'Interactive investigation workspace consuming backend REST APIs',
    boundary: 'monitored'
  },
  {
    id: 'layer-7',
    name: 'Layer 7 — LOGIQ Self-Observability Boundary',
    subtitle: 'Internal health metrics, worker heartbeats, queue depth, and infrastructure telemetry',
    boundary: 'self'
  }
];

const ARCHITECTURE_COMPONENTS = [
  {
    id: 'apps-microservices',
    layerId: 'layer-1',
    layerName: 'Layer 1 — External Data Sources',
    name: 'Applications & Microservices',
    status: 'External integration',
    responsibility: 'Emits structured JSON or unstructured text logs during request execution and background jobs.',
    input: 'Application runtime events',
    output: 'HTTP log payloads or stdout/stderr streams',
    upstream: ['Host runtime / Kubernetes'],
    downstream: ['API Gateway', 'OpenTelemetry Collector'],
    technologies: ['JSON / stdout', 'HTTP/REST'],
    contractNote: 'Illustrative structured payload schema (service, level, timestamp, message, trace_id).'
  },
  {
    id: 'servers-containers',
    layerId: 'layer-1',
    layerName: 'Layer 1 — External Data Sources',
    name: 'Servers, Containers & Datasets',
    status: 'Implemented',
    responsibility: 'Provides container log files and offline historical log archives uploaded for batch analysis.',
    input: 'Container log files (.log, .jsonl) or archived exports',
    output: 'Multipart dataset uploads or forwarded log lines',
    upstream: ['Operator / CI / Host filesystem'],
    downstream: ['Dataset & Source Management Service', 'Fluent Bit'],
    technologies: ['Docker', 'JSONL / Plaintext'],
    contractNote: 'Dataset upload supported via web interface and multipart API.'
  },
  {
    id: 'api-gateway',
    layerId: 'layer-2',
    layerName: 'Layer 2 — Collection & API Access',
    name: 'API Gateway',
    status: 'Implemented',
    responsibility: 'Provides the unified HTTP entry point, routes external ingestion and frontend queries, and enforces access boundaries.',
    input: 'External ingestion HTTP requests and frontend API queries',
    output: 'Validated internal service requests',
    upstream: ['Applications', 'LOGIQ Web Application'],
    downstream: ['Log Collection Service', 'Dataset & Source Management Service', 'Analytics Service'],
    technologies: ['Python 3.11+', 'FastAPI', 'Pydantic'],
    contractNote: 'REST over HTTP/JSON; schema validation via Pydantic models.'
  },
  {
    id: 'log-collection-service',
    layerId: 'layer-2',
    layerName: 'Layer 2 — Collection & API Access',
    name: 'Log Collection Service',
    status: 'Implemented',
    responsibility: 'Accepts incoming log batches, validates required metadata fields, assigns ingestion timestamps, and publishes events.',
    input: 'Validated log batch payloads from API Gateway or collectors',
    output: 'Raw ingestion event envelopes',
    upstream: ['API Gateway', 'OpenTelemetry Collector'],
    downstream: ['Apache Kafka'],
    technologies: ['Python 3.11+', 'FastAPI', 'Pydantic'],
    contractNote: 'Publishes validated events to logical ingestion stream.'
  },
  {
    id: 'dataset-service',
    layerId: 'layer-2',
    layerName: 'Layer 2 — Collection & API Access',
    name: 'Dataset & Source Management Service',
    status: 'Implemented',
    responsibility: 'Manages registered log sources, tracks uploaded dataset lifecycle states, and stores raw files in object storage.',
    input: 'Uploaded log files and source configuration records',
    output: 'Stored raw objects and dataset processing triggers',
    upstream: ['API Gateway'],
    downstream: ['MinIO', 'PostgreSQL', 'Apache Kafka'],
    technologies: ['FastAPI', 'SQLAlchemy', 'MinIO SDK'],
    contractNote: 'Tracks dataset state: uploaded -> processing -> ready / failed.'
  },
  {
    id: 'otel-collector',
    layerId: 'layer-2',
    layerName: 'Layer 2 — Collection & API Access',
    name: 'OpenTelemetry Collector / Fluent Bit',
    status: 'Partially implemented',
    responsibility: 'Forwards logs from containerized workloads and host environments into the LOGIQ collection layer.',
    input: 'OTLP log streams and tailed container log files',
    output: 'Batched HTTP payloads sent to Log Collection Service',
    upstream: ['Servers & Containers'],
    downstream: ['Log Collection Service'],
    technologies: ['OpenTelemetry Collector', 'Fluent Bit'],
    contractNote: 'HTTP exporter configuration supported; native OTLP gRPC receiver planned.'
  },
  {
    id: 'kafka',
    layerId: 'layer-3',
    layerName: 'Layer 3 — Message Transport & Processing',
    name: 'Apache Kafka',
    status: 'Implemented',
    responsibility: 'Provides asynchronous event transport, decoupling ingestion spikes from downstream parsing and intelligence workers.',
    input: 'Serialized ingestion and preprocessed log event envelopes',
    output: 'Ordered partition streams consumed by processing workers',
    upstream: ['Log Collection Service', 'Preprocessing Service'],
    downstream: ['Preprocessing Service', 'Parser Service', 'Intelligence Service'],
    technologies: ['Apache Kafka'],
    contractNote: 'Logical event streams separating raw, normalized, and parsed stages.'
  },
  {
    id: 'preprocessing-service',
    layerId: 'layer-3',
    layerName: 'Layer 3 — Message Transport & Processing',
    name: 'Preprocessing Service',
    status: 'Implemented',
    responsibility: 'Cleans raw log payloads, normalizes ISO-8601 timestamps, standardizes severity levels, and extracts trace/request IDs.',
    input: 'Raw log event stream from Kafka',
    output: 'Normalized canonical log events',
    upstream: ['Apache Kafka'],
    downstream: ['Apache Kafka', 'Redis'],
    technologies: ['Python 3.11+', 'Pydantic'],
    contractNote: 'Produces normalized log schema for downstream template parsing.'
  },
  {
    id: 'parser-service',
    layerId: 'layer-3',
    layerName: 'Layer 3 — Message Transport & Processing',
    name: 'Parser Service',
    status: 'Implemented',
    responsibility: 'Extracts structural log templates by masking variable tokens (<*>) and capturing parameter values.',
    input: 'Normalized log events',
    output: 'Structured log records with template ID, template string, and extracted parameters',
    upstream: ['Apache Kafka', 'Redis'],
    downstream: ['Intelligence Service', 'PostgreSQL'],
    technologies: ['Python 3.11+', 'Drain-inspired template miner'],
    contractNote: 'Outputs deterministic template signatures and parameter maps.'
  },
  {
    id: 'intelligence-service',
    layerId: 'layer-4',
    layerName: 'Layer 4 — Intelligence & Analytics',
    name: 'Intelligence Service',
    status: 'Partially implemented',
    responsibility: 'Tracks template frequency baselines, surfaces newly seen templates, and flags statistically unusual shifts.',
    input: 'Parsed log events and historical template frequency windows',
    output: 'Anomaly candidate records and template trend deltas',
    upstream: ['Parser Service', 'Redis'],
    downstream: ['PostgreSQL', 'Analytics Service'],
    technologies: ['Python 3.11+', 'NumPy / Statistical windowing'],
    contractNote: 'Frequency delta & unseen template detection implemented; automated root-cause inference not claimed.'
  },
  {
    id: 'analytics-service',
    layerId: 'layer-4',
    layerName: 'Layer 4 — Intelligence & Analytics',
    name: 'Analytics Service',
    status: 'Implemented',
    responsibility: 'Serves aggregated service metrics, log search queries, template distributions, and anomaly investigation views.',
    input: 'Query filters, time ranges, and structured database records',
    output: 'Paginated log results, time-series buckets, and correlation summaries',
    upstream: ['API Gateway'],
    downstream: ['PostgreSQL', 'Redis'],
    technologies: ['FastAPI', 'SQLAlchemy'],
    contractNote: 'Powers Overview, Log Explorer, Template Explorer, and Anomaly Investigation endpoints.'
  },
  {
    id: 'postgresql',
    layerId: 'layer-5',
    layerName: 'Layer 5 — Persistence & State Storage',
    name: 'PostgreSQL',
    status: 'Implemented',
    responsibility: 'Persists service registry, dataset metadata, extracted templates, anomaly records, and indexed structured log records.',
    input: 'Relational writes from Parser, Intelligence, and Dataset services',
    output: 'Indexed query results for Analytics Service',
    upstream: ['Parser Service', 'Intelligence Service', 'Dataset & Source Management Service'],
    downstream: ['Analytics Service'],
    technologies: ['PostgreSQL', 'SQLAlchemy', 'Alembic'],
    contractNote: 'Schema migrations managed via Alembic.'
  },
  {
    id: 'minio',
    layerId: 'layer-5',
    layerName: 'Layer 5 — Persistence & State Storage',
    name: 'MinIO Object Storage',
    status: 'Implemented',
    responsibility: 'Stores uploaded raw dataset archives and large batch artifacts outside relational tables.',
    input: 'Raw dataset files (.log, .jsonl, .csv)',
    output: 'Object streams for batch ingestion workers',
    upstream: ['Dataset & Source Management Service'],
    downstream: ['Preprocessing Service'],
    technologies: ['MinIO (S3-compatible)'],
    contractNote: 'Bucketed by environment and dataset ID.'
  },
  {
    id: 'redis',
    layerId: 'layer-5',
    layerName: 'Layer 5 — Persistence & State Storage',
    name: 'Redis',
    status: 'Partially implemented',
    responsibility: 'Provides fast-access template lookup caching, sliding window counters, and worker heartbeat coordination.',
    input: 'Ephemeral cache keys and rolling window counters',
    output: 'Sub-millisecond template metadata and heartbeat state',
    upstream: ['Preprocessing Service', 'Parser Service', 'Intelligence Service'],
    downstream: ['Analytics Service'],
    technologies: ['Redis'],
    contractNote: 'Used for hot template cache and short-TTL operational state.'
  },
  {
    id: 'web-app',
    layerId: 'layer-6',
    layerName: 'Layer 6 — LOGIQ Web Application',
    name: 'LOGIQ Web Application',
    status: 'Implemented',
    responsibility: 'Provides engineers with Service Overview, Log Explorer, Anomaly Investigation, Template Explorer, and Dataset workflows.',
    input: 'JSON responses from API Gateway',
    output: 'Interactive investigation queries and triage state updates',
    upstream: ['API Gateway'],
    downstream: ['Backend Engineers / SREs'],
    technologies: ['React', 'TypeScript', 'Vite', 'Tailwind CSS', 'Recharts', 'TanStack Query'],
    contractNote: 'Single-page engineering workspace sharing global time range and filter state.'
  },
  {
    id: 'prometheus-grafana',
    layerId: 'layer-7',
    layerName: 'Layer 7 — LOGIQ Self-Observability Boundary',
    name: 'Prometheus & Grafana (Internal)',
    status: 'Partially implemented',
    responsibility: 'Scrapes internal FastAPI metrics, Kafka consumer lag, worker heartbeats, and database health independently of monitored user logs.',
    input: '/metrics endpoints, worker heartbeats, queue depth exporters',
    output: 'Internal operational dashboards and Platform Health status checks',
    upstream: ['API Gateway', 'Processing Workers', 'Kafka / Redis / PostgreSQL'],
    downstream: ['Platform Health View', 'Grafana'],
    technologies: ['Prometheus', 'Grafana'],
    contractNote: 'Domain B: Monitors LOGIQ itself so platform degradation is never masked by monitored app traffic.'
  }
];

const SERVICES_DATA = [
  {
    id: 'payment-service',
    name: 'payment-service',
    status: 'degraded',
    logVolume: '148,920',
    errorRate: '6.42%',
    baselineDelta: '+518%',
    lastSeen: '12s ago',
    owner: 'payments-core',
    runtime: 'Python 3.11 / FastAPI'
  },
  {
    id: 'checkout-gateway',
    name: 'checkout-gateway',
    status: 'warning',
    logVolume: '312,450',
    errorRate: '1.85%',
    baselineDelta: '+142%',
    lastSeen: '8s ago',
    owner: 'commerce-edge',
    runtime: 'Go 1.22'
  },
  {
    id: 'auth-token-verifier',
    name: 'auth-token-verifier',
    status: 'healthy',
    logVolume: '490,110',
    errorRate: '0.04%',
    baselineDelta: '-2%',
    lastSeen: '4s ago',
    owner: 'identity-platform',
    runtime: 'Rust / Tokio'
  },
  {
    id: 'ledger-worker',
    name: 'ledger-worker',
    status: 'healthy',
    logVolume: '89,340',
    errorRate: '0.11%',
    baselineDelta: '+4%',
    lastSeen: '19s ago',
    owner: 'payments-core',
    runtime: 'Python 3.11 / Celery'
  },
  {
    id: 'webhook-dispatcher',
    name: 'webhook-dispatcher',
    status: 'unknown',
    logVolume: 'Unavailable',
    errorRate: 'Unavailable',
    baselineDelta: 'Unavailable',
    lastSeen: '42m ago',
    owner: 'integrations',
    runtime: 'Node.js 20'
  }
];

const ANOMALIES_DATA = [
  {
    id: 'anom-2026-084',
    title: 'Spike in upstream settlement gateway timeouts & newly observed fallback template',
    service: 'payment-service',
    severity: 'critical',
    status: 'investigating',
    firstObserved: '2026-11-23 01:42:10 UTC',
    lastObserved: '2026-11-23 02:05:48 UTC',
    changeSummary: '+518% error template surge; 1 new circuit-breaker template observed',
    summary:
      'Beginning at 01:42:10 UTC, payment-service exhibited a sharp increase in upstream settlement gateway timeout errors alongside a previously unseen circuit-breaker fallback log template. Correlated trace IDs indicate cascading retry latency into checkout-gateway. Automated root-cause determination is not claimed; investigation is active.',
    changedTemplates: [
      {
        id: 'tpl-pay-timeout',
        type: 'Increased Frequency',
        template: 'Upstream settlement gateway timeout after <*>ms for tx_id=<*> (attempt <*>/3)',
        prevFreq: '14 / hr',
        currFreq: '1,842 / hr',
        changePct: '+13,057%'
      },
      {
        id: 'tpl-pay-cb',
        type: 'Newly Observed',
        template: 'Circuit breaker state transition CLOSED -> OPEN for provider=<*> failure_count=<*>',
        prevFreq: '0 / hr',
        currFreq: '96 / hr',
        changePct: 'New'
      },
      {
        id: 'tpl-pay-ok',
        type: 'Decreased Frequency',
        template: 'Settlement capture completed tx_id=<*> latency_ms=<*>',
        prevFreq: '6,120 / hr',
        currFreq: '4,210 / hr',
        changePct: '-31.2%'
      }
    ],
    correlatedTraceIds: ['tr-8f92e1a04b', 'tr-7c31d99f12', 'tr-5a09b44e81'],
    correlatedRequestIds: ['req-0094910', 'req-0094884']
  },
  {
    id: 'anom-2026-083',
    title: 'Elevated downstream retry backoff warnings on /v2/checkout/confirm',
    service: 'checkout-gateway',
    severity: 'warning',
    status: 'open',
    firstObserved: '2026-11-23 01:43:02 UTC',
    lastObserved: '2026-11-23 02:05:12 UTC',
    changeSummary: '+142% retry warning rate correlated with payment-service latency',
    summary:
      'checkout-gateway began logging elevated retry backoff warnings 52 seconds after payment-service timeout spikes began. Shared trace identifiers link these warnings directly to downstream payment authorization calls.',
    changedTemplates: [
      {
        id: 'tpl-chk-retry',
        type: 'Increased Frequency',
        template: 'Retrying downstream authorization call to payment-service trace=<*> backoff=<*>ms',
        prevFreq: '42 / hr',
        currFreq: '618 / hr',
        changePct: '+1,371%'
      }
    ],
    correlatedTraceIds: ['tr-8f92e1a04b', 'tr-5a09b44e81'],
    correlatedRequestIds: ['req-0094910']
  }
];

const TEMPLATES_DATA = [
  {
    id: 'tpl-pay-timeout',
    service: 'payment-service',
    tag: 'Rising',
    template: 'Upstream settlement gateway timeout after <*>ms for tx_id=<*> (attempt <*>/3)',
    frequency: '1,842 / hr',
    trend: '+13,057%',
    firstSeen: '2026-10-14 09:12 UTC',
    lastSeen: '12s ago',
    sparkline: [12, 14, 11, 15, 13, 14, 190, 620, 1210, 1842],
    parameters: ['duration_ms (int)', 'tx_id (string)', 'attempt (int)'],
    examples: [
      'Upstream settlement gateway timeout after 5000ms for tx_id=tx_99b04d1e (attempt 3/3)',
      'Upstream settlement gateway timeout after 5000ms for tx_id=tx_99b04c8a (attempt 2/3)'
    ]
  },
  {
    id: 'tpl-pay-cb',
    service: 'payment-service',
    tag: 'New',
    template: 'Circuit breaker state transition CLOSED -> OPEN for provider=<*> failure_count=<*>',
    frequency: '96 / hr',
    trend: 'New',
    firstSeen: '2026-11-23 01:44 UTC',
    lastSeen: '28s ago',
    sparkline: [0, 0, 0, 0, 0, 0, 14, 29, 48, 96],
    parameters: ['provider (string)', 'failure_count (int)'],
    examples: [
      'Circuit breaker state transition CLOSED -> OPEN for provider=adyen-eu failure_count=25'
    ]
  },
  {
    id: 'tpl-chk-retry',
    service: 'checkout-gateway',
    tag: 'Rising',
    template: 'Retrying downstream authorization call to payment-service trace=<*> backoff=<*>ms',
    frequency: '618 / hr',
    trend: '+1,371%',
    firstSeen: '2026-09-02 14:20 UTC',
    lastSeen: '8s ago',
    sparkline: [38, 41, 40, 44, 39, 42, 110, 290, 480, 618],
    parameters: ['trace (string)', 'backoff_ms (int)'],
    examples: [
      'Retrying downstream authorization call to payment-service trace=tr-8f92e1a04b backoff=500ms'
    ]
  },
  {
    id: 'tpl-auth-ok',
    service: 'auth-token-verifier',
    tag: 'Frequent',
    template: 'JWT signature verified key_id=<*> subject=<*> ttl=<*>s',
    frequency: '29,400 / hr',
    trend: '-1.8%',
    firstSeen: '2026-08-01 00:00 UTC',
    lastSeen: '4s ago',
    sparkline: [29800, 29500, 29900, 29400, 29100, 29600, 29300, 29450, 29380, 29400],
    parameters: ['key_id (string)', 'subject (string)', 'ttl (int)'],
    examples: [
      'JWT signature verified key_id=k_2026_11 subject=usr_51209 ttl=3599s'
    ]
  },
  {
    id: 'tpl-pay-ok',
    service: 'payment-service',
    tag: 'Frequent',
    template: 'Settlement capture completed tx_id=<*> latency_ms=<*>',
    frequency: '4,210 / hr',
    trend: '-31.2%',
    firstSeen: '2026-08-01 00:00 UTC',
    lastSeen: '15s ago',
    sparkline: [6100, 6150, 6080, 6200, 6120, 6090, 5100, 4620, 4390, 4210],
    parameters: ['tx_id (string)', 'latency_ms (int)'],
    examples: [
      'Settlement capture completed tx_id=tx_99b04e02 latency_ms=142'
    ]
  }
];

const LOG_ENTRIES_DATA = [
  {
    id: 'log-1001',
    timestamp: '2026-11-23T02:05:48.114Z',
    severity: 'ERROR',
    service: 'payment-service',
    templateId: 'tpl-pay-timeout',
    template: 'Upstream settlement gateway timeout after <*>ms for tx_id=<*> (attempt <*>/3)',
    message: 'Upstream settlement gateway timeout after 5000ms for tx_id=tx_99b04d1e (attempt 3/3)',
    traceId: 'tr-8f92e1a04b',
    requestId: 'req-0094910',
    source: 'otel-collector-02',
    parameters: { duration_ms: 5000, tx_id: 'tx_99b04d1e', attempt: 3 },
    attributes: { host: 'pay-worker-03.eu-west-1', region: 'eu-west-1', http_status: 504, provider: 'adyen-eu' }
  },
  {
    id: 'log-1002',
    timestamp: '2026-11-23T02:05:47.802Z',
    severity: 'WARN',
    service: 'checkout-gateway',
    templateId: 'tpl-chk-retry',
    template: 'Retrying downstream authorization call to payment-service trace=<*> backoff=<*>ms',
    message: 'Retrying downstream authorization call to payment-service trace=tr-8f92e1a04b backoff=500ms',
    traceId: 'tr-8f92e1a04b',
    requestId: 'req-0094910',
    source: 'fluent-bit-ingress',
    parameters: { trace: 'tr-8f92e1a04b', backoff_ms: 500 },
    attributes: { host: 'chk-edge-01.eu-west-1', route: 'POST /v2/checkout/confirm', attempt: 3 }
  },
  {
    id: 'log-1003',
    timestamp: '2026-11-23T02:05:31.440Z',
    severity: 'ERROR',
    service: 'payment-service',
    templateId: 'tpl-pay-cb',
    template: 'Circuit breaker state transition CLOSED -> OPEN for provider=<*> failure_count=<*>',
    message: 'Circuit breaker state transition CLOSED -> OPEN for provider=adyen-eu failure_count=25',
    traceId: 'tr-7c31d99f12',
    requestId: 'req-0094884',
    source: 'otel-collector-02',
    parameters: { provider: 'adyen-eu', failure_count: 25 },
    attributes: { host: 'pay-worker-01.eu-west-1', breaker_window_sec: 60 }
  },
  {
    id: 'log-1004',
    timestamp: '2026-11-23T02:05:19.009Z',
    severity: 'INFO',
    service: 'auth-token-verifier',
    templateId: 'tpl-auth-ok',
    template: 'JWT signature verified key_id=<*> subject=<*> ttl=<*>s',
    message: 'JWT signature verified key_id=k_2026_11 subject=usr_51209 ttl=3599s',
    traceId: 'tr-4b11c90a8d',
    requestId: 'req-0094914',
    source: 'otel-collector-01',
    parameters: { key_id: 'k_2026_11', subject: 'usr_51209', ttl: 3599 },
    attributes: { host: 'auth-pod-04.eu-west-1', alg: 'EdDSA' }
  },
  {
    id: 'log-1005',
    timestamp: '2026-11-23T02:04:58.612Z',
    severity: 'ERROR',
    service: 'payment-service',
    templateId: 'tpl-pay-timeout',
    template: 'Upstream settlement gateway timeout after <*>ms for tx_id=<*> (attempt <*>/3)',
    message: 'Upstream settlement gateway timeout after 5000ms for tx_id=tx_99b04c8a (attempt 2/3)',
    traceId: 'tr-5a09b44e81',
    requestId: 'req-0094861',
    source: 'otel-collector-02',
    parameters: { duration_ms: 5000, tx_id: 'tx_99b04c8a', attempt: 2 },
    attributes: { host: 'pay-worker-02.eu-west-1', http_status: 504, provider: 'adyen-eu' }
  },
  {
    id: 'log-1006',
    timestamp: '2026-11-23T02:04:41.225Z',
    severity: 'INFO',
    service: 'payment-service',
    templateId: 'tpl-pay-ok',
    template: 'Settlement capture completed tx_id=<*> latency_ms=<*>',
    message: 'Settlement capture completed tx_id=tx_99b04e02 latency_ms=142',
    traceId: 'tr-1e72a08c33',
    requestId: 'req-0094840',
    source: 'otel-collector-01',
    parameters: { tx_id: 'tx_99b04e02', latency_ms: 142 },
    attributes: { host: 'pay-worker-04.eu-west-1', provider: 'stripe-eu' }
  },
  {
    id: 'log-1007',
    timestamp: '2026-11-23T02:04:12.905Z',
    severity: 'INFO',
    service: 'ledger-worker',
    templateId: 'tpl-led-batch',
    template: 'Double-entry journal batch committed batch_id=<*> entries=<*>',
    message: 'Double-entry journal batch committed batch_id=b_20261123_0204 entries=480',
    traceId: 'tr-9d00f31b77',
    requestId: 'req-0094812',
    source: 'batch-dataset-import',
    parameters: { batch_id: 'b_20261123_0204', entries: 480 },
    attributes: { host: 'ledger-cron-01.eu-west-1', queue: 'settlement-ledger' }
  }
];

const TIMELINE_SERIES_DATA = [
  { time: '01:20', total: 420, errors: 6 },
  { time: '01:25', total: 435, errors: 5 },
  { time: '01:30', total: 418, errors: 7 },
  { time: '01:35', total: 440, errors: 6 },
  { time: '01:40', total: 455, errors: 9 },
  { time: '01:42', total: 610, errors: 98 },
  { time: '01:45', total: 780, errors: 214 },
  { time: '01:50', total: 845, errors: 312 },
  { time: '01:55', total: 890, errors: 368 },
  { time: '02:00', total: 920, errors: 405 },
  { time: '02:05', total: 910, errors: 392 }
];

const INITIAL_DATASETS = [
  {
    id: 'ds-019',
    name: 'payment-incident-capture-2026-11-23.jsonl',
    sourceType: 'JSONL Batch Upload',
    uploadStatus: 'Uploaded',
    processingStatus: 'Ready',
    recordCount: '48,912',
    createdAt: '2026-11-23 01:58 UTC',
    size: '18.4 MB'
  },
  {
    id: 'ds-018',
    name: 'checkout-gateway-access-2026-11-22.log',
    sourceType: 'Plaintext Log Archive',
    uploadStatus: 'Uploaded',
    processingStatus: 'Ready',
    recordCount: '192,405',
    createdAt: '2026-11-22 22:14 UTC',
    size: '64.1 MB'
  },
  {
    id: 'ds-017',
    name: 'legacy-billing-export-corrupt.jsonl',
    sourceType: 'JSONL Batch Upload',
    uploadStatus: 'Uploaded',
    processingStatus: 'Failed',
    recordCount: 'Unavailable',
    createdAt: '2026-11-21 16:40 UTC',
    size: '4.2 MB',
    errorDetail: 'Malformed JSON object at line 1,402: unexpected EOF while parsing timestamp.'
  }
];

const SOURCES_DATA = [
  {
    id: 'src-otel-prod',
    name: 'otel-collector-eu-west-1',
    type: 'OpenTelemetry Collector (HTTP)',
    status: 'Active',
    configSummary: 'Batch size: 512 | Flush: 2s | TLS: Enabled',
    lastActivity: '4s ago'
  },
  {
    id: 'src-fb-edge',
    name: 'fluent-bit-gateway-nodes',
    type: 'Fluent Bit Forwarder',
    status: 'Active',
    configSummary: 'Input: tail /var/log/containers/*.log | Format: JSON',
    lastActivity: '8s ago'
  },
  {
    id: 'src-webhook-hook',
    name: 'webhook-dispatcher-agent',
    type: 'Direct HTTP Ingestion',
    status: 'Unknown',
    configSummary: 'Configured endpoint: /ingest (No heartbeat in 42m)',
    lastActivity: '42m ago'
  }
];

const PLATFORM_HEALTH_COMPONENTS = [
  {
    name: 'API Gateway & Collection API',
    category: 'Backend Services',
    status: 'Healthy',
    heartbeat: '2s ago',
    detail: 'FastAPI workers responsive; p95 validation latency within nominal range.',
    recentFailures: '0 in last 24h'
  },
  {
    name: 'Preprocessing & Parser Workers',
    category: 'Processing Pipeline',
    status: 'Healthy',
    heartbeat: '3s ago',
    detail: '4 active consumer workers processing Kafka partitions.',
    recentFailures: '0 in last 24h'
  },
  {
    name: 'Apache Kafka Broker & Streams',
    category: 'Message Transport',
    status: 'Healthy',
    heartbeat: '5s ago',
    detail: 'Consumer lag: 142 messages (nominal). Dead-letter queue: 3 events.',
    recentFailures: '0 broker disconnects'
  },
  {
    name: 'PostgreSQL Primary',
    category: 'Persistence',
    status: 'Healthy',
    heartbeat: '2s ago',
    detail: 'Connection pool 18/50 active; Alembic migration head verified.',
    recentFailures: '0 query timeouts'
  },
  {
    name: 'MinIO Object Storage',
    category: 'Persistence',
    status: 'Healthy',
    heartbeat: '6s ago',
    detail: 'Bucket logiq-datasets reachable; read/write checks passing.',
    recentFailures: '0 in last 24h'
  },
  {
    name: 'Redis Cache & Heartbeat Store',
    category: 'State & Cache',
    status: 'Healthy',
    heartbeat: '2s ago',
    detail: 'Memory utilization 24%; template cache hit ratio 94.2%.',
    recentFailures: '0 evictions'
  },
  {
    name: 'Prometheus Self-Metrics Exporter',
    category: 'Self-Observability',
    status: 'Unavailable',
    heartbeat: 'Unavailable',
    detail: 'External Prometheus scrape endpoint not connected in local demo environment.',
    recentFailures: 'Unavailable'
  }
];

const DOCS_PAGES = [
  {
    id: 'intro',
    section: 'Getting Started',
    title: 'Introduction',
    summary: 'Overview of LOGIQ, its design goals, and how backend engineers use structured template intelligence to investigate incidents.',
    body: [
      'LOGIQ is a centralized log intelligence and observability platform built for backend engineers, SREs, and platform teams. Rather than treating logs strictly as unstructured text streams, LOGIQ normalizes incoming events, extracts recurring log templates, and surfaces abnormal shifts in service behavior.',
      'This documentation describes both implemented capabilities and architectural boundaries so operators have an accurate model of how data moves through the system.'
    ],
    codeNote: null,
    related: ['what-is-logiq', 'architecture-overview']
  },
  {
    id: 'what-is-logiq',
    section: 'Getting Started',
    title: 'What is LOGIQ?',
    summary: 'Core concepts: centralized ingestion, template mining, parameter extraction, and anomaly-oriented triage.',
    body: [
      'Modern distributed services emit millions of repetitive log lines where only specific identifiers—such as transaction IDs, durations, or IP addresses—change between executions. LOGIQ separates the static message template from dynamic parameters.',
      'By tracking template frequencies over time, LOGIQ highlights newly introduced error templates and sudden frequency spikes alongside correlated trace and request identifiers.'
    ],
    codeNote: {
      label: 'Illustrative Template Extraction Example',
      code: `Raw Log:
"Upstream settlement gateway timeout after 5000ms for tx_id=tx_99b04d1e (attempt 3/3)"

Extracted Template:
"Upstream settlement gateway timeout after <*>ms for tx_id=<*> (attempt <*>/3)"

Extracted Parameters:
{ "duration_ms": 5000, "tx_id": "tx_99b04d1e", "attempt": 3 }`
    },
    related: ['log-templates', 'anomaly-investigation']
  },
  {
    id: 'architecture-overview',
    section: 'Architecture',
    title: 'Architecture Overview',
    summary: 'Seven-layer modular architecture separating monitored application telemetry from LOGIQ self-observability.',
    body: [
      'LOGIQ is structured into seven distinct layers: External Data Sources, Collection & API Access, Message Transport & Processing, Intelligence & Analytics, Persistence, the React Web Application, and a dedicated Self-Observability boundary.',
      'Separating Domain A (user application logs) from Domain B (LOGIQ internal worker and queue health) ensures that platform bottlenecks can be diagnosed even during high-volume application incidents.'
    ],
    codeNote: null,
    related: ['data-flow', 'services-responsibilities']
  },
  {
    id: 'data-flow',
    section: 'Architecture',
    title: 'Data Flow',
    summary: 'End-to-end lifecycle of a log event from ingestion through Kafka streams into PostgreSQL and MinIO.',
    body: [
      '1. Collection: Applications or collectors submit batches via the API Gateway to the Log Collection Service, or operators upload static files via Dataset Management.',
      '2. Transport & Preprocessing: Events are published to Apache Kafka logical streams, cleaned by the Preprocessing Service, and normalized into canonical timestamps and attributes.',
      '3. Parsing & Intelligence: The Parser Service extracts templates and parameters, while the Intelligence Service evaluates frequency changes before persisting structured records to PostgreSQL.'
    ],
    codeNote: null,
    related: ['processing-pipeline', 'log-collection']
  },
  {
    id: 'services-responsibilities',
    section: 'Architecture',
    title: 'Services and Responsibilities',
    summary: 'Service boundaries across FastAPI microservices, Kafka consumers, and storage engines.',
    body: [
      'Each service owns a clear boundary: API Gateway handles routing and validation; Dataset Service manages MinIO object storage; Preprocessing normalizes schemas; Parser extracts templates; Intelligence computes frequency anomalies; Analytics serves read queries.',
      'All relational metadata and structured analytics reside in PostgreSQL, while raw uploaded dataset files are stored in MinIO.'
    ],
    codeNote: null,
    related: ['technology-stack', 'platform-health']
  },
  {
    id: 'technology-stack',
    section: 'Architecture',
    title: 'Technology Stack',
    summary: 'Verified languages, frameworks, brokers, and storage engines used across LOGIQ.',
    body: [
      'Backend services are implemented in Python 3.11+ using FastAPI, Pydantic, SQLAlchemy, and Alembic. Asynchronous decoupling relies on Apache Kafka with Redis for fast-access caching.',
      'Persistence combines PostgreSQL and MinIO. The frontend is built with React, TypeScript, Vite, Tailwind CSS, Recharts, and TanStack Query.'
    ],
    codeNote: null,
    related: ['configuration', 'architecture-overview']
  },
  {
    id: 'log-collection',
    section: 'Ingestion & Data',
    title: 'Log Collection',
    summary: 'How external applications and collectors send log events into LOGIQ.',
    body: [
      'Services can forward structured log events over HTTP to the collection layer or route container logs via OpenTelemetry Collector and Fluent Bit.',
      'Note: Exact production endpoint paths and authentication headers depend on deployment configuration. The snippet below shows an illustrative JSON event contract.'
    ],
    codeNote: {
      label: 'Illustrative Ingestion Payload (Conceptual Schema)',
      code: `{
  "timestamp": "2026-11-23T02:05:48.114Z",
  "service": "payment-service",
  "environment": "prod-eu-west-1",
  "severity": "ERROR",
  "message": "Upstream settlement gateway timeout after 5000ms for tx_id=tx_99b04d1e (attempt 3/3)",
  "trace_id": "tr-8f92e1a04b",
  "request_id": "req-0094910",
  "attributes": {
    "provider": "adyen-eu",
    "http_status": 504
  }
}`
    },
    related: ['dataset-upload', 'processing-pipeline']
  },
  {
    id: 'dataset-upload',
    section: 'Ingestion & Data',
    title: 'Dataset Upload',
    summary: 'Uploading historical log files for offline parsing and incident replay.',
    body: [
      'Engineers can upload static log datasets directly through the Datasets view in the LOGIQ application. Uploaded files are persisted in MinIO and queued for asynchronous preprocessing and template extraction.',
      'Supported file formats are configurable per deployment (commonly newline-delimited JSON and structured plaintext logs).'
    ],
    codeNote: null,
    related: ['log-collection', 'log-templates']
  },
  {
    id: 'processing-pipeline',
    section: 'Processing & Intelligence',
    title: 'Processing Pipeline',
    summary: 'Normalization, validation, and Kafka-backed stream stages.',
    body: [
      'Incoming events pass through validation before entering Kafka logical streams. Preprocessing standardizes timestamps to UTC ISO-8601 format, maps severity aliases (e.g., warning -> WARN), and extracts correlation identifiers.',
      'Malformed records that fail schema checks are isolated so a single noisy producer cannot stall downstream consumers.'
    ],
    codeNote: null,
    related: ['log-templates', 'troubleshooting']
  },
  {
    id: 'log-templates',
    section: 'Processing & Intelligence',
    title: 'Log Templates',
    summary: 'How LOGIQ groups repetitive messages into parameterized templates.',
    body: [
      'Log template extraction replaces high-cardinality tokens (UUIDs, numeric durations, IP addresses, hex hashes) with wildcard placeholders (<*>).',
      'Grouping events by template allows engineers to inspect 50,000 raw timeout errors as a single pattern with sortable parameter distributions.'
    ],
    codeNote: null,
    related: ['anomaly-investigation', 'what-is-logiq']
  },
  {
    id: 'anomaly-investigation',
    section: 'Processing & Intelligence',
    title: 'Anomaly Investigation',
    summary: 'Investigating template frequency shifts, newly observed patterns, and correlated traces.',
    body: [
      'When a service exhibits an unusual surge in error templates or emits a previously unseen template signature, LOGIQ flags an anomaly record with first-observed and last-observed timestamps.',
      'LOGIQ presents objective evidence—changed templates, volume timelines, sample logs, and shared trace IDs—without fabricating automated root-cause claims.'
    ],
    codeNote: null,
    related: ['log-templates', 'platform-health']
  },
  {
    id: 'platform-health',
    section: 'Operations',
    title: 'Platform Health',
    summary: 'Monitoring LOGIQ internal API workers, Kafka queues, PostgreSQL, and MinIO.',
    body: [
      'The Platform Health view tracks LOGIQ internal infrastructure separately from monitored customer services. Operators can verify worker heartbeats, database connectivity, and object storage availability.',
      'If an internal telemetry source such as Prometheus is not connected, the UI explicitly displays an Unavailable state rather than fabricated zeros.'
    ],
    codeNote: null,
    related: ['configuration', 'troubleshooting']
  },
  {
    id: 'configuration',
    section: 'Operations',
    title: 'Configuration',
    summary: 'Environment variables, Docker Compose services, and retention parameters.',
    body: [
      'LOGIQ services are configured via environment variables and deployed using Docker and Docker Compose. Core configuration covers Kafka bootstrap brokers, PostgreSQL DSNs, MinIO credentials, and Redis connection URLs.'
    ],
    codeNote: {
      label: 'Illustrative Service Configuration (.env)',
      code: `LOGIQ_ENV=development
POSTGRES_DSN=postgresql+asyncpg://logiq:***@postgres:5432/logiq
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000`
    },
    related: ['troubleshooting', 'platform-health']
  },
  {
    id: 'troubleshooting',
    section: 'Operations',
    title: 'Troubleshooting',
    summary: 'Diagnosing dataset parsing failures, stalled workers, and missing service telemetry.',
    body: [
      'If a service shows "Unavailable" metrics in Overview, verify that its collector or HTTP forwarder is actively sending events and check Sources for last-activity timestamps.',
      'If an uploaded dataset transitions to "Failed", inspect the dataset detail drawer for line-level parsing diagnostics and retry processing after correcting malformed lines.'
    ],
    codeNote: null,
    related: ['platform-health', 'dataset-upload']
  }
];

/**
 * ============================================================================
 * REUSABLE UI PRIMITIVES (Status Badges, Copy Button, Sparkline)
 * ============================================================================
 */

const StatusBadge = ({ status }) => {
  const normalized = (status || 'unknown').toLowerCase();
  const styles = {
    healthy: 'text-[#8FBE9F] bg-[#8FBE9F]/10 border-[#8FBE9F]/25',
    implemented: 'text-[#8FBE9F] bg-[#8FBE9F]/10 border-[#8FBE9F]/25',
    ready: 'text-[#8FBE9F] bg-[#8FBE9F]/10 border-[#8FBE9F]/25',
    active: 'text-[#8FBE9F] bg-[#8FBE9F]/10 border-[#8FBE9F]/25',
    connected: 'text-[#8FBE9F] bg-[#8FBE9F]/10 border-[#8FBE9F]/25',
    uploaded: 'text-[#8FBE9F] bg-[#8FBE9F]/10 border-[#8FBE9F]/25',
    warning: 'text-[#D6AD75] bg-[#D6AD75]/10 border-[#D6AD75]/25',
    'partially implemented': 'text-[#D6AD75] bg-[#D6AD75]/10 border-[#D6AD75]/25',
    investigating: 'text-[#D6AD75] bg-[#D6AD75]/10 border-[#D6AD75]/25',
    processing: 'text-[#D6AD75] bg-[#D6AD75]/10 border-[#D6AD75]/25',
    degraded: 'text-[#D77F7F] bg-[#D77F7F]/10 border-[#D77F7F]/25',
    critical: 'text-[#D77F7F] bg-[#D77F7F]/10 border-[#D77F7F]/25',
    error: 'text-[#D77F7F] bg-[#D77F7F]/10 border-[#D77F7F]/25',
    failed: 'text-[#D77F7F] bg-[#D77F7F]/10 border-[#D77F7F]/25',
    planned: 'text-[#91AFC7] bg-[#91AFC7]/10 border-[#91AFC7]/25',
    'external integration': 'text-[#A1A5A5] bg-[#202326] border-[#303438]',
    unknown: 'text-[#747A7D] bg-[#202326] border-[#303438]',
    unavailable: 'text-[#747A7D] bg-[#202326] border-[#303438]',
    open: 'text-[#D6AD75] bg-[#D6AD75]/10 border-[#D6AD75]/25',
    resolved: 'text-[#8FBE9F] bg-[#8FBE9F]/10 border-[#8FBE9F]/25'
  };

  const dotColors = {
    healthy: 'bg-[#8FBE9F]',
    implemented: 'bg-[#8FBE9F]',
    ready: 'bg-[#8FBE9F]',
    active: 'bg-[#8FBE9F]',
    connected: 'bg-[#8FBE9F]',
    uploaded: 'bg-[#8FBE9F]',
    warning: 'bg-[#D6AD75]',
    'partially implemented': 'bg-[#D6AD75]',
    investigating: 'bg-[#D6AD75]',
    processing: 'bg-[#D6AD75]',
    open: 'bg-[#D6AD75]',
    degraded: 'bg-[#D77F7F]',
    critical: 'bg-[#D77F7F]',
    error: 'bg-[#D77F7F]',
    failed: 'bg-[#D77F7F]',
    planned: 'bg-[#91AFC7]',
    'external integration': 'bg-[#A1A5A5]',
    unknown: 'bg-[#747A7D]',
    unavailable: 'bg-[#747A7D]',
    resolved: 'bg-[#8FBE9F]'
  };

  const isLiveAlert = ['degraded', 'critical', 'error', 'investigating'].includes(normalized);
  const cls = styles[normalized] || styles.unknown;
  const dot = dotColors[normalized] || dotColors.unknown;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] font-medium border rounded ${cls}`}>
      <span className="relative flex h-1.5 w-1.5">
        {isLiveAlert && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${dot}`} />
        )}
        <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${dot}`} />
      </span>
      <span className="capitalize">{status}</span>
    </span>
  );
};

const SeverityBadge = ({ severity }) => {
  const s = (severity || 'INFO').toUpperCase();
  const map = {
    ERROR: 'text-[#D77F7F] bg-[#D77F7F]/10 border-[#D77F7F]/30',
    CRITICAL: 'text-[#D77F7F] bg-[#D77F7F]/10 border-[#D77F7F]/30',
    WARN: 'text-[#D6AD75] bg-[#D6AD75]/10 border-[#D6AD75]/30',
    WARNING: 'text-[#D6AD75] bg-[#D6AD75]/10 border-[#D6AD75]/30',
    INFO: 'text-[#91AFC7] bg-[#91AFC7]/10 border-[#91AFC7]/30',
    DEBUG: 'text-[#747A7D] bg-[#202326] border-[#303438]'
  };
  return (
    <span className={`inline-block px-1.5 py-0.5 font-mono text-[10px] font-semibold tracking-wider border rounded ${map[s] || map.INFO}`}>
      {s}
    </span>
  );
};

const CopyButton = ({ text, label = 'Copy' }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e) => {
    e.stopPropagation();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(() => {});
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-mono text-[#A1A5A5] hover:text-[#ECEDEA] bg-[#101112] hover:bg-[#202326] border border-[#303438] rounded transition-colors"
      title={`Copy ${label}`}
    >
      {copied ? <Check className="w-3 h-3 text-[#8FBE9F]" /> : <Copy className="w-3 h-3" />}
      <span>{copied ? 'Copied' : label}</span>
    </button>
  );
};

const MiniSparkline = ({ values = [], color = '#A6C8B5' }) => {
  if (!values.length) return null;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const width = 88;
  const height = 24;
  const points = values
    .map((v, idx) => {
      const x = (idx / (values.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        points={points}
      />
    </svg>
  );
};

/**
 * ============================================================================
 * PART 3 — INTERACTIVE 7-LAYER ARCHITECTURE EXPLORER (ANIMATED SVG NODE GRAPH)
 * ============================================================================
 */
const GRAPH_NODE_POSITIONS = {
  // Layer 1 (y: 66)
  'apps-microservices': { x: 255, y: 66 },
  'servers-containers': { x: 645, y: 66 },
  // Layer 2 (y: 196)
  'api-gateway': { x: 145, y: 196 },
  'log-collection-service': { x: 380, y: 196 },
  'dataset-service': { x: 615, y: 196 },
  'otel-collector': { x: 835, y: 196 },
  // Layer 3 (y: 326)
  'kafka': { x: 235, y: 326 },
  'preprocessing-service': { x: 495, y: 326 },
  'parser-service': { x: 755, y: 326 },
  // Layer 4 (y: 456)
  'intelligence-service': { x: 345, y: 456 },
  'analytics-service': { x: 645, y: 456 },
  // Layer 5 (y: 586)
  'postgresql': { x: 235, y: 586 },
  'minio': { x: 495, y: 586 },
  'redis': { x: 755, y: 586 },
  // Layer 6 (y: 716)
  'web-app': { x: 495, y: 716 },
  // Layer 7 — Self-Observability Boundary (y: 866)
  'prometheus-grafana': { x: 495, y: 866 }
};

const GRAPH_EDGES = [
  { id: 'e-app-gw', from: 'apps-microservices', to: 'api-gateway', label: 'HTTP / JSON', domain: 'monitored' },
  { id: 'e-app-otel', from: 'apps-microservices', to: 'otel-collector', label: 'OTLP', domain: 'monitored' },
  { id: 'e-srv-ds', from: 'servers-containers', to: 'dataset-service', label: 'Dataset Upload', domain: 'monitored' },
  { id: 'e-srv-otel', from: 'servers-containers', to: 'otel-collector', label: 'File Tail', domain: 'monitored' },
  { id: 'e-gw-col', from: 'api-gateway', to: 'log-collection-service', label: 'Validated Batch', domain: 'monitored' },
  { id: 'e-gw-ds', from: 'api-gateway', to: 'dataset-service', label: 'Admin / Upload', domain: 'monitored' },
  { id: 'e-otel-col', from: 'otel-collector', to: 'log-collection-service', label: 'Forwarded Batch', domain: 'monitored' },
  { id: 'e-col-kafka', from: 'log-collection-service', to: 'kafka', label: 'Raw Stream', domain: 'monitored' },
  { id: 'e-ds-minio', from: 'dataset-service', to: 'minio', label: 'Raw Archive', domain: 'monitored' },
  { id: 'e-ds-kafka', from: 'dataset-service', to: 'kafka', label: 'Ingest Event', domain: 'monitored' },
  { id: 'e-kafka-pre', from: 'kafka', to: 'preprocessing-service', label: 'Consume Raw', domain: 'monitored' },
  { id: 'e-pre-parse', from: 'preprocessing-service', to: 'parser-service', label: 'Normalized Event', domain: 'monitored' },
  { id: 'e-parse-intel', from: 'parser-service', to: 'intelligence-service', label: 'Templates', domain: 'monitored' },
  { id: 'e-parse-pg', from: 'parser-service', to: 'postgresql', label: 'Structured Logs', domain: 'monitored' },
  { id: 'e-intel-pg', from: 'intelligence-service', to: 'postgresql', label: 'Anomalies', domain: 'monitored' },
  { id: 'e-intel-redis', from: 'intelligence-service', to: 'redis', label: 'Window State', domain: 'monitored' },
  { id: 'e-pg-ana', from: 'postgresql', to: 'analytics-service', label: 'SQL Query', domain: 'monitored' },
  { id: 'e-redis-ana', from: 'redis', to: 'analytics-service', label: 'Hot Cache', domain: 'monitored' },
  { id: 'e-ana-web', from: 'analytics-service', to: 'web-app', label: 'REST / JSON', domain: 'monitored' },
  { id: 'e-kafka-self', from: 'kafka', to: 'prometheus-grafana', label: 'Consumer Lag', domain: 'self', dashed: true },
  { id: 'e-pg-self', from: 'postgresql', to: 'prometheus-grafana', label: 'DB Health', domain: 'self', dashed: true },
  { id: 'e-redis-self', from: 'redis', to: 'prometheus-grafana', label: 'Heartbeats', domain: 'self', dashed: true }
];

const ArchitectureExplorer = ({ compact = false, onOpenFullArchitecture, gsapReady }) => {
  const [selectedComponentId, setSelectedComponentId] = useState('parser-service');
  const [hoveredComponentId, setHoveredComponentId] = useState(null);
  const [activeLayerFilter, setActiveLayerFilter] = useState('all');
  const [viewMode, setViewMode] = useState('graph'); // 'graph' | 'simplified'
  const [streamPlaying, setStreamPlaying] = useState(true);
  const [zoomLevel, setZoomLevel] = useState(100);
  const [componentsState, setComponentsState] = useState(ARCHITECTURE_COMPONENTS);
  const inspectorRef = useRef(null);
  const svgGraphRef = useRef(null);

  const selectedComponent = useMemo(
    () => componentsState.find((c) => c.id === selectedComponentId) || componentsState[0],
    [componentsState, selectedComponentId]
  );

  // Subtle GSAP transition when inspecting a new architecture node
  useEffect(() => {
    if (!gsapReady || !window.gsap || !inspectorRef.current) return;
    window.gsap.fromTo(
      inspectorRef.current,
      { opacity: 0.45, y: 6 },
      { opacity: 1, y: 0, duration: 0.28, ease: 'power2.out', clearProps: 'transform' }
    );
  }, [selectedComponentId, gsapReady]);

  // GSAP Dashed Line Flow Animation on SVG Edges
  useEffect(() => {
    if (!gsapReady || !window.gsap || !svgGraphRef.current || !streamPlaying) return;
    const ctx = window.gsap.context(() => {
      window.gsap.to('.arch-svg-flow-line', {
        strokeDashoffset: -36,
        duration: 1.4,
        repeat: -1,
        ease: 'none'
      });
    }, svgGraphRef);
    return () => ctx.revert();
  }, [gsapReady, streamPlaying, viewMode, activeLayerFilter]);

  const handleStatusChange = (compId, newStatus) => {
    setComponentsState((prev) =>
      prev.map((item) => (item.id === compId ? { ...item, status: newStatus } : item))
    );
  };

  const handleReset = () => {
    setSelectedComponentId('parser-service');
    setActiveLayerFilter('all');
    setViewMode('graph');
    setStreamPlaying(true);
    setZoomLevel(100);
  };

  const activeNodeFocus = hoveredComponentId || selectedComponentId;

  const isNodeVisible = (comp) => {
    if (activeLayerFilter === 'all') return true;
    const layer = ARCHITECTURE_LAYERS.find((l) => l.id === comp.layerId);
    if (activeLayerFilter === 'monitored') return layer?.boundary === 'monitored';
    if (activeLayerFilter === 'self') return layer?.boundary === 'self';
    return comp.layerId === activeLayerFilter;
  };

  const buildCurvePath = (fromId, toId) => {
    const p1 = GRAPH_NODE_POSITIONS[fromId];
    const p2 = GRAPH_NODE_POSITIONS[toId];
    if (!p1 || !p2) return '';
    const startX = p1.x;
    const startY = p1.y + 24;
    const endX = p2.x;
    const endY = p2.y - 24;
    const midY = (startY + endY) / 2;
    return `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`;
  };

  const getStatusStroke = (status) => {
    if (status === 'Implemented') return '#8FBE9F';
    if (status === 'Partially implemented') return '#D6AD75';
    if (status === 'Planned') return '#91AFC7';
    return '#A1A5A5';
  };

  return (
    <div className="border border-[#303438] bg-[#151719] rounded-md overflow-hidden">
      {/* Architecture Toolbar */}
      <div className="px-4 py-3 border-b border-[#303438] bg-[#1B1D1F] flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded border border-[#303438] bg-[#101112] p-0.5 text-xs">
            <button
              onClick={() => setViewMode('graph')}
              className={`px-2.5 py-1 rounded-sm transition-colors ${
                viewMode === 'graph'
                  ? 'bg-[#202326] text-[#ECEDEA] font-medium'
                  : 'text-[#747A7D] hover:text-[#A1A5A5]'
              }`}
            >
              Interactive Topology Graph
            </button>
            <button
              onClick={() => setViewMode('simplified')}
              className={`px-2.5 py-1 rounded-sm transition-colors ${
                viewMode === 'simplified'
                  ? 'bg-[#202326] text-[#ECEDEA] font-medium'
                  : 'text-[#747A7D] hover:text-[#A1A5A5]'
              }`}
            >
              Simplified Pipeline
            </button>
          </div>

          {viewMode === 'graph' && (
            <>
              <select
                value={activeLayerFilter}
                onChange={(e) => setActiveLayerFilter(e.target.value)}
                className="px-2.5 py-1 text-xs bg-[#101112] border border-[#303438] rounded text-[#ECEDEA] focus:outline-none focus:border-[#A6C8B5]"
              >
                <option value="all">All Layers & Boundaries</option>
                <option value="monitored">Domain A: Monitored Log Pipeline (Layers 1–6)</option>
                <option value="self">Domain B: LOGIQ Self-Observability (Layer 7)</option>
                {ARCHITECTURE_LAYERS.map((layer) => (
                  <option key={layer.id} value={layer.id}>
                    {layer.name}
                  </option>
                ))}
              </select>

              <button
                onClick={() => setStreamPlaying(!streamPlaying)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono border rounded transition-colors ${
                  streamPlaying
                    ? 'bg-[#A6C8B5]/12 border-[#A6C8B5]/40 text-[#A6C8B5]'
                    : 'bg-[#101112] border-[#303438] text-[#A1A5A5]'
                }`}
                title="Toggle live telemetry pulse animation"
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    streamPlaying ? 'bg-[#A6C8B5] animate-pulse' : 'bg-[#747A7D]'
                  }`}
                />
                <span>{streamPlaying ? 'Signal Flow: Active' : 'Signal Flow: Paused'}</span>
              </button>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-1 border border-[#303438] bg-[#101112] rounded px-1.5 py-0.5 text-xs font-mono text-[#A1A5A5]">
            <button
              onClick={() => setZoomLevel((z) => Math.max(80, z - 10))}
              className="p-1 hover:text-[#ECEDEA]"
              title="Zoom out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="px-1">{zoomLevel}%</span>
            <button
              onClick={() => setZoomLevel((z) => Math.min(115, z + 10))}
              className="p-1 hover:text-[#ECEDEA]"
              title="Zoom in"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            onClick={handleReset}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs text-[#A1A5A5] hover:text-[#ECEDEA] bg-[#101112] border border-[#303438] rounded"
            title="Reset graph view"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset</span>
          </button>

          {compact && onOpenFullArchitecture && (
            <button
              onClick={onOpenFullArchitecture}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-[#101112] bg-[#A6C8B5] hover:bg-[#B9D6C6] rounded"
            >
              <span>Full View</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Legend Bar */}
      <div className="px-4 py-2 border-b border-[#303438] bg-[#101112] flex flex-wrap items-center justify-between gap-3 text-[11px] text-[#A1A5A5]">
        <div className="flex flex-wrap items-center gap-4">
          <span className="font-mono text-[#747A7D] uppercase">Status Legend:</span>
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#8FBE9F]" /> Implemented
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#D6AD75]" /> Partially implemented
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#91AFC7]" /> Planned
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#A1A5A5]" /> External integration
          </span>
        </div>
        <div className="font-mono text-[10px] text-[#747A7D]">
          Hover to trace upstream/downstream edges • Click node to inspect contracts
        </div>
      </div>

      {/* Main SVG Graph + Side Inspector Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12">
        {/* Interactive Directed Graph Canvas */}
        <div className="lg:col-span-8 p-3 sm:p-5 overflow-x-auto bg-[#101112]">
          <div
            style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'top left' }}
            className="transition-transform duration-200 min-w-[760px]"
          >
            {viewMode === 'simplified' ? (
              <div className="p-4 space-y-4">
                <div className="text-[11px] font-mono text-[#747A7D] uppercase tracking-wider">
                  Simplified End-to-End Pipeline Graph
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 items-center">
                  {[
                    { id: 'otel-collector', label: '1. Ingestion', sub: 'Sources & Collectors' },
                    { id: 'kafka', label: '2. Transport', sub: 'Apache Kafka' },
                    { id: 'parser-service', label: '3. Parsing', sub: 'Templates & Params' },
                    { id: 'intelligence-service', label: '4. Intelligence', sub: 'Patterns & Anomalies' },
                    { id: 'web-app', label: '5. Investigation', sub: 'LOGIQ Workspace' }
                  ].map((step, i, arr) => (
                    <React.Fragment key={step.id}>
                      <button
                        onClick={() => setSelectedComponentId(step.id)}
                        className={`p-3.5 rounded border text-left transition-colors ${
                          selectedComponentId === step.id
                            ? 'bg-[#A6C8B5]/12 border-[#A6C8B5] text-[#ECEDEA]'
                            : 'bg-[#1B1D1F] border-[#303438] text-[#A1A5A5] hover:border-[#747A7D]'
                        }`}
                      >
                        <div className="text-xs font-mono font-semibold text-[#ECEDEA]">{step.label}</div>
                        <div className="text-[11px] mt-1">{step.sub}</div>
                      </button>
                      {i < arr.length - 1 && (
                        <div className="hidden sm:flex justify-center text-[#A6C8B5] font-mono text-xs">
                          ──▶
                        </div>
                      )}
                    </React.Fragment>
                  ))}
                </div>
              </div>
            ) : (
              <svg
                ref={svgGraphRef}
                viewBox="0 0 980 935"
                className="w-full h-auto select-none"
                role="img"
                aria-label="LOGIQ Interactive 7-Layer System Architecture Graph"
              >
                <defs>
                  {/* Subtle Engineering Blueprint Dot Matrix */}
                  <pattern id="logiq-dot-grid" width="24" height="24" patternUnits="userSpaceOnUse">
                    <circle cx="1.5" cy="1.5" r="0.85" fill="#25282C" />
                  </pattern>

                  {/* Arrowhead Markers */}
                  <marker
                    id="arrow-default"
                    viewBox="0 0 10 10"
                    refX="8"
                    refY="5"
                    markerWidth="5.5"
                    markerHeight="5.5"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#4B5157" />
                  </marker>
                  <marker
                    id="arrow-active"
                    viewBox="0 0 10 10"
                    refX="8"
                    refY="5"
                    markerWidth="6"
                    markerHeight="6"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#A6C8B5" />
                  </marker>
                  <marker
                    id="arrow-self"
                    viewBox="0 0 10 10"
                    refX="8"
                    refY="5"
                    markerWidth="5.5"
                    markerHeight="5.5"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#D6AD75" />
                  </marker>
                </defs>

                {/* Blueprint Background */}
                <rect x="0" y="0" width="980" height="935" rx="6" fill="url(#logiq-dot-grid)" />

                {/* Horizontal Layer Swimlane Bands */}
                {ARCHITECTURE_LAYERS.map((layer, index) => {
                  const yTop = index === 6 ? 802 : 16 + index * 130;
                  const bandHeight = index === 6 ? 114 : 104;
                  const isSelf = layer.boundary === 'self';
                  const dimmed =
                    activeLayerFilter !== 'all' &&
                    activeLayerFilter !== layer.id &&
                    !(activeLayerFilter === 'monitored' && !isSelf) &&
                    !(activeLayerFilter === 'self' && isSelf);

                  return (
                    <g key={layer.id} opacity={dimmed ? 0.22 : 1} className="transition-opacity duration-200">
                      <rect
                        x="14"
                        y={yTop}
                        width="952"
                        height={bandHeight}
                        rx="5"
                        fill={isSelf ? '#161718' : '#141618'}
                        stroke={isSelf ? '#D6AD75' : '#262A2E'}
                        strokeOpacity={isSelf ? 0.45 : 1}
                        strokeDasharray={isSelf ? '5 4' : undefined}
                        strokeWidth="1"
                      />
                      <text
                        x="26"
                        y={yTop + 17}
                        fill={isSelf ? '#D6AD75' : '#747A7D'}
                        fontSize="10"
                        fontFamily="monospace"
                        letterSpacing="0.06em"
                      >
                        {layer.name.toUpperCase()}
                      </text>
                      {isSelf && (
                        <text
                          x="952"
                          y={yTop + 17}
                          textAnchor="end"
                          fill="#D6AD75"
                          fontSize="9.5"
                          fontFamily="monospace"
                        >
                          DOMAIN B: SELF-OBSERVABILITY BOUNDARY
                        </text>
                      )}
                    </g>
                  );
                })}

                {/* Directed Cubic Bezier Edges & Animated Telemetry Pulses */}
                {GRAPH_EDGES.map((edge) => {
                  const fromComp = componentsState.find((c) => c.id === edge.from);
                  const toComp = componentsState.find((c) => c.id === edge.to);
                  if (!fromComp || !toComp) return null;

                  const bothVisible = isNodeVisible(fromComp) && isNodeVisible(toComp);
                  const isConnectedToFocus =
                    edge.from === activeNodeFocus || edge.to === activeNodeFocus;
                  const pathD = buildCurvePath(edge.from, edge.to);
                  const isSelfEdge = edge.domain === 'self';

                  const strokeColor = isConnectedToFocus
                    ? isSelfEdge
                      ? '#D6AD75'
                      : '#A6C8B5'
                    : isSelfEdge
                    ? '#6E5B3E'
                    : '#383D42';

                  return (
                    <g
                      key={edge.id}
                      opacity={!bothVisible ? 0.12 : isConnectedToFocus ? 1 : 0.65}
                      className="transition-opacity duration-200"
                    >
                      {/* Base Structural Edge */}
                      <path
                        d={pathD}
                        fill="none"
                        stroke={strokeColor}
                        strokeWidth={isConnectedToFocus ? 1.8 : 1.15}
                        strokeDasharray={edge.dashed ? '4 4' : undefined}
                        markerEnd={
                          isConnectedToFocus
                            ? isSelfEdge
                              ? 'url(#arrow-self)'
                              : 'url(#arrow-active)'
                            : isSelfEdge
                            ? 'url(#arrow-self)'
                            : 'url(#arrow-default)'
                        }
                      />

                      {/* Animated Signal Flow Overlay */}
                      {streamPlaying && bothVisible && (
                        <path
                          d={pathD}
                          fill="none"
                          stroke={isSelfEdge ? '#D6AD75' : '#A6C8B5'}
                          strokeOpacity={isConnectedToFocus ? 0.9 : 0.35}
                          strokeWidth={isConnectedToFocus ? 2 : 1.2}
                          strokeDasharray="4 14"
                          className="arch-svg-flow-line"
                        />
                      )}

                      {/* Travelling Telemetry Packet Dot */}
                      {streamPlaying && bothVisible && (isConnectedToFocus || edge.id === 'e-col-kafka' || edge.id === 'e-pre-parse' || edge.id === 'e-parse-intel') && (
                        <circle
                          r={isConnectedToFocus ? 3.2 : 2.3}
                          fill={isSelfEdge ? '#D6AD75' : '#A6C8B5'}
                        >
                          <animateMotion
                            dur={isConnectedToFocus ? '1.9s' : '2.8s'}
                            repeatCount="indefinite"
                            path={pathD}
                          />
                        </circle>
                      )}
                    </g>
                  );
                })}

                {/* Interactive Service Nodes */}
                {componentsState.map((comp) => {
                  const pos = GRAPH_NODE_POSITIONS[comp.id];
                  if (!pos) return null;

                  const visible = isNodeVisible(comp);
                  const isSelected = selectedComponentId === comp.id;
                  const isHovered = hoveredComponentId === comp.id;
                  const isNeighbor = GRAPH_EDGES.some(
                    (e) =>
                      (e.from === activeNodeFocus && e.to === comp.id) ||
                      (e.to === activeNodeFocus && e.from === comp.id)
                  );

                  const boxWidth = 204;
                  const boxHeight = 48;
                  const x = pos.x - boxWidth / 2;
                  const y = pos.y - boxHeight / 2;
                  const statusColor = getStatusStroke(comp.status);

                  return (
                    <g
                      key={comp.id}
                      transform={`translate(${x}, ${y})`}
                      onClick={() => setSelectedComponentId(comp.id)}
                      onMouseEnter={() => setHoveredComponentId(comp.id)}
                      onMouseLeave={() => setHoveredComponentId(null)}
                      opacity={!visible ? 0.2 : 1}
                      className="cursor-pointer transition-opacity duration-200"
                    >
                      {/* Node Container */}
                      <rect
                        width={boxWidth}
                        height={boxHeight}
                        rx="4"
                        fill={isSelected ? '#1E2522' : isHovered || isNeighbor ? '#202326' : '#181A1D'}
                        stroke={
                          isSelected
                            ? '#A6C8B5'
                            : isHovered || isNeighbor
                            ? '#747A7D'
                            : '#303438'
                        }
                        strokeWidth={isSelected ? 1.6 : 1}
                      />

                      {/* Left Status Accent Strip */}
                      <rect
                        x="0"
                        y="0"
                        width="3.5"
                        height={boxHeight}
                        rx="1.5"
                        fill={statusColor}
                      />

                      {/* Node Title */}
                      <text
                        x="13"
                        y="20"
                        fill="#ECEDEA"
                        fontSize="11"
                        fontWeight="600"
                        fontFamily="Inter, sans-serif"
                      >
                        {comp.name.length > 26 ? `${comp.name.slice(0, 25)}…` : comp.name}
                      </text>

                      {/* Primary Tech Tag */}
                      <text
                        x="13"
                        y="36"
                        fill="#A1A5A5"
                        fontSize="9.5"
                        fontFamily="monospace"
                      >
                        {comp.technologies.slice(0, 2).join(' · ')}
                      </text>

                      {/* Status Indicator Dot */}
                      <circle cx={boxWidth - 12} cy="16" r="3.5" fill={statusColor} />
                    </g>
                  );
                })}
              </svg>
            )}
          </div>
        </div>

        {/* Right-Hand Component Inspector Panel */}
        <div
          ref={inspectorRef}
          className="lg:col-span-4 border-t lg:border-t-0 lg:border-l border-[#303438] bg-[#151719] p-5 flex flex-col justify-between"
        >
          <div className="space-y-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-[10px] font-mono uppercase tracking-wider text-[#747A7D]">
                  Node Contract Inspector
                </div>
                <h4 className="text-base font-semibold text-[#ECEDEA] mt-0.5">
                  {selectedComponent.name}
                </h4>
              </div>
              <StatusBadge status={selectedComponent.status} />
            </div>

            <div className="text-xs text-[#A1A5A5] leading-relaxed">
              {selectedComponent.responsibility}
            </div>

            <div className="grid grid-cols-1 gap-2.5 pt-2 border-t border-[#303438] text-xs">
              <div>
                <span className="text-[10px] font-mono uppercase text-[#747A7D] block">Architecture Layer</span>
                <span className="text-[#ECEDEA]">{selectedComponent.layerName}</span>
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase text-[#747A7D] block">Input</span>
                <span className="text-[#A1A5A5]">{selectedComponent.input}</span>
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase text-[#747A7D] block">Output</span>
                <span className="text-[#A1A5A5]">{selectedComponent.output}</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-[10px] font-mono uppercase text-[#747A7D] block">Upstream</span>
                  <span className="text-[#A1A5A5] text-[11px]">
                    {selectedComponent.upstream.join(', ')}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] font-mono uppercase text-[#747A7D] block">Downstream</span>
                  <span className="text-[#A1A5A5] text-[11px]">
                    {selectedComponent.downstream.join(', ')}
                  </span>
                </div>
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase text-[#747A7D] block mb-1">
                  Associated Technologies
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {selectedComponent.technologies.map((tech) => (
                    <span
                      key={tech}
                      className="px-2 py-0.5 text-[11px] font-mono bg-[#101112] border border-[#303438] rounded text-[#ECEDEA]"
                    >
                      {tech}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase text-[#747A7D] block">Contract / Interface</span>
                <span className="text-[11px] font-mono text-[#A6C8B5]">{selectedComponent.contractNote}</span>
              </div>
            </div>
          </div>

          {/* Editable Implementation Status Selector */}
          <div className="mt-5 pt-4 border-t border-[#303438]">
            <label className="block text-[10px] font-mono uppercase text-[#747A7D] mb-1.5">
              Verification Status (Editable Model)
            </label>
            <select
              value={selectedComponent.status}
              onChange={(e) => handleStatusChange(selectedComponent.id, e.target.value)}
              className="w-full px-2.5 py-1.5 text-xs bg-[#101112] border border-[#303438] rounded text-[#ECEDEA] focus:outline-none focus:border-[#A6C8B5]"
            >
              <option value="Implemented">Implemented</option>
              <option value="Partially implemented">Partially implemented</option>
              <option value="Planned">Planned</option>
              <option value="External integration">External integration</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * ============================================================================
 * PART 2 — PUBLIC WEBSITE (Landing Page + Dedicated Architecture Page)
 * ============================================================================
 */
const PublicWebsite = ({
  subPage,
  setSubPage,
  onOpenPlatform,
  onOpenDocs,
  gsapReady
}) => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [streamIndex, setStreamIndex] = useState(0);
  const pageRootRef = useRef(null);

  // Subtle live stream rotation in the hero product preview
  useEffect(() => {
    const timer = setInterval(() => {
      setStreamIndex((prev) => (prev + 1) % LOG_ENTRIES_DATA.length);
    }, 3400);
    return () => clearInterval(timer);
  }, []);

  const previewLogs = useMemo(() => {
    const rotated = [];
    for (let i = 0; i < 3; i++) {
      rotated.push(LOG_ENTRIES_DATA[(streamIndex + i) % LOG_ENTRIES_DATA.length]);
    }
    return rotated;
  }, [streamIndex]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // GSAP Hero Stagger & ScrollTrigger Choreographed Reveals
  useEffect(() => {
    if (!gsapReady || !window.gsap || !pageRootRef.current) return;
    const gsap = window.gsap;
    const ScrollTrigger = window.ScrollTrigger;

    const ctx = gsap.context(() => {
      // 1. Crisp Above-the-Fold Hero Choreography
      gsap.fromTo(
        '.gsap-hero-stagger',
        { y: 18, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.65,
          stagger: 0.08,
          ease: 'power3.out',
          clearProps: 'transform'
        }
      );

      // 2. Hero Product Preview Frame Entrance
      gsap.fromTo(
        '.gsap-hero-preview',
        { y: 24, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.75,
          delay: 0.25,
          ease: 'power3.out',
          clearProps: 'transform'
        }
      );

      // 3. Scroll-Triggered Editorial Sections
      if (ScrollTrigger) {
        gsap.utils.toArray('.gsap-reveal-group').forEach((group) => {
          const cards = group.querySelectorAll('.gsap-reveal-item');
          if (!cards.length) return;
          gsap.fromTo(
            cards,
            { y: 20, opacity: 0 },
            {
              y: 0,
              opacity: 1,
              duration: 0.55,
              stagger: 0.07,
              ease: 'power2.out',
              clearProps: 'transform',
              scrollTrigger: {
                trigger: group,
                start: 'top 84%',
                once: true
              }
            }
          );
        });

        // 4. Lifecycle Pipeline Connector Line Draw
        gsap.fromTo(
          '.gsap-pipeline-progress',
          { scaleX: 0 },
          {
            scaleX: 1,
            duration: 0.9,
            ease: 'power2.inOut',
            transformOrigin: 'left center',
            scrollTrigger: {
              trigger: '.gsap-pipeline-section',
              start: 'top 80%',
              once: true
            }
          }
        );
      }
    }, pageRootRef);

    return () => ctx.revert();
  }, [gsapReady, subPage]);

  const scrollToSection = (sectionId) => {
    setMobileMenuOpen(false);
    if (subPage !== 'landing') {
      setSubPage('landing');
      setTimeout(() => {
        document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth' });
      }, 60);
    } else {
      document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div ref={pageRootRef} className="min-h-screen bg-[#101112] text-[#ECEDEA] selection:bg-[#A6C8B5]/20 selection:text-[#A6C8B5]">
      {/* Sticky Restrained Top Navigation */}
      <header
        className={`sticky top-0 z-40 transition-colors border-b ${
          scrolled
            ? 'bg-[#101112]/95 border-[#303438]'
            : 'bg-[#101112] border-[#303438]/60'
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between gap-8">
          {/* Left: LOGIQ Wordmark */}
          <div className="flex items-center gap-6">
            <button
              onClick={() => {
                setSubPage('landing');
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              className="flex items-center gap-2 text-left"
            >
              <span className="w-2 h-2 bg-[#A6C8B5] inline-block" />
              <span className="font-mono font-semibold tracking-[0.14em] text-sm text-[#ECEDEA]">
                LOGIQ
              </span>
            </button>
          </div>

          {/* Centre/Right Desktop Links */}
          <nav className="hidden md:flex items-center gap-6 text-xs text-[#A1A5A5] whitespace-nowrap">
            <button
              onClick={() => scrollToSection('capabilities')}
              className="hover:text-[#ECEDEA] transition-colors"
            >
              Platform
            </button>
            <button
              onClick={() => setSubPage('architecture')}
              className={`transition-colors ${
                subPage === 'architecture' ? 'text-[#A6C8B5] font-medium' : 'hover:text-[#ECEDEA]'
              }`}
            >
              Architecture
            </button>
            <button
              onClick={() => onOpenDocs('intro')}
              className="hover:text-[#ECEDEA] transition-colors"
            >
              Documentation
            </button>
            <button
              onClick={() => scrollToSection('technology')}
              className="hover:text-[#ECEDEA] transition-colors"
            >
              Technology
            </button>
            <button
              onClick={() => scrollToSection('about')}
              className="hover:text-[#ECEDEA] transition-colors"
            >
              About
            </button>
          </nav>

          {/* Right Actions */}
          <div className="hidden md:flex items-center gap-3 shrink-0">
            <a
              href="#github-repository-placeholder"
              onClick={(e) => {
                e.preventDefault();
                onOpenDocs('intro');
              }}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-[#A1A5A5] hover:text-[#ECEDEA] border border-[#303438] rounded bg-[#151719] transition-colors"
            >
              <GitBranch className="w-3.5 h-3.5" />
              <span>GitHub</span>
            </a>
            <button
              onClick={() => onOpenPlatform('overview')}
              className="px-3.5 py-1.5 text-xs font-medium bg-[#A6C8B5] hover:bg-[#B9D6C6] text-[#101112] rounded transition-colors"
            >
              Open Platform
            </button>
          </div>

          {/* Mobile Hamburger */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 text-[#A1A5A5] hover:text-[#ECEDEA]"
            aria-label="Toggle Menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-[#303438] bg-[#151719] px-4 py-4 space-y-3 text-sm">
            <button onClick={() => scrollToSection('capabilities')} className="block w-full text-left text-[#A1A5A5] py-1">
              Platform
            </button>
            <button
              onClick={() => {
                setSubPage('architecture');
                setMobileMenuOpen(false);
              }}
              className="block w-full text-left text-[#A1A5A5] py-1"
            >
              Architecture
            </button>
            <button
              onClick={() => {
                onOpenDocs('intro');
                setMobileMenuOpen(false);
              }}
              className="block w-full text-left text-[#A1A5A5] py-1"
            >
              Documentation
            </button>
            <button onClick={() => scrollToSection('technology')} className="block w-full text-left text-[#A1A5A5] py-1">
              Technology
            </button>
            <button onClick={() => scrollToSection('about')} className="block w-full text-left text-[#A1A5A5] py-1">
              About
            </button>
            <div className="pt-2 border-t border-[#303438] flex gap-2">
              <button
                onClick={() => onOpenPlatform('overview')}
                className="flex-1 py-2 text-center text-xs font-medium bg-[#A6C8B5] text-[#101112] rounded"
              >
                Open Platform
              </button>
            </div>
          </div>
        )}
      </header>

      {/* DEDICATED ARCHITECTURE VIEW OR MAIN LANDING PAGE */}
      {subPage === 'architecture' ? (
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#303438] pb-6">
            <div>
              <div className="text-[11px] font-mono uppercase tracking-[0.14em] text-[#A6C8B5] mb-2">
                SYSTEM ARCHITECTURE SPECIFICATION
              </div>
              <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#ECEDEA]">
                Seven-Layer Log Intelligence & Self-Observability Architecture
              </h1>
              <p className="mt-2 text-sm text-[#A1A5A5] max-w-3xl">
                Interactive reference architecture showing ingestion, Kafka event transport, template parsing, persistence boundaries, and internal self-observability.
              </p>
            </div>
            <button
              onClick={() => setSubPage('landing')}
              className="px-3 py-1.5 text-xs text-[#A1A5A5] hover:text-[#ECEDEA] bg-[#151719] border border-[#303438] rounded"
            >
              ← Back to Overview
            </button>
          </div>

          <ArchitectureExplorer compact={false} gsapReady={gsapReady} />

          {/* Dual Observability Boundary Explanation */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
            <div className="p-5 border border-[#303438] bg-[#151719] rounded">
              <div className="text-[11px] font-mono uppercase text-[#A6C8B5] mb-1">
                Domain A — External Application Observability
              </div>
              <h3 className="text-base font-semibold text-[#ECEDEA] mb-2">
                Monitored Services & Datasets (Layers 1–6)
              </h3>
              <p className="text-xs text-[#A1A5A5] leading-relaxed">
                Receives logs emitted by user microservices, containers, and uploaded datasets. Events are decoupled over Kafka, normalized, parsed into structural templates, and queried through the LOGIQ workspace.
              </p>
            </div>
            <div className="p-5 border border-dashed border-[#D6AD75]/50 bg-[#151719] rounded">
              <div className="text-[11px] font-mono uppercase text-[#D6AD75] mb-1">
                Domain B — LOGIQ Self-Observability
              </div>
              <h3 className="text-base font-semibold text-[#ECEDEA] mb-2">
                Internal Platform Telemetry (Layer 7)
              </h3>
              <p className="text-xs text-[#A1A5A5] leading-relaxed">
                Monitors the health of LOGIQ’s own FastAPI services, Kafka consumer lag, worker heartbeats, PostgreSQL connectivity, and MinIO storage via Prometheus and Grafana so internal failures remain visible.
              </p>
            </div>
          </div>
        </main>
      ) : (
        <main>
          {/* B. HERO SECTION (Typography-led + Integrated Product Cropped Preview) */}
          <section className="border-b border-[#303438] relative overflow-hidden">
            {/* Subtle Technical Grid Backdrop */}
            <div
              className="pointer-events-none absolute inset-0 opacity-[0.035]"
              style={{
                backgroundImage:
                  'linear-gradient(to right, #ECEDEA 1px, transparent 1px), linear-gradient(to bottom, #ECEDEA 1px, transparent 1px)',
                backgroundSize: '48px 48px'
              }}
            />
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-14 pb-16 lg:pt-20 lg:pb-24 relative">
              <div className="max-w-3xl">
                <div className="gsap-hero-stagger text-[11px] font-mono uppercase tracking-[0.16em] text-[#A6C8B5] mb-4 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#A6C8B5] animate-pulse" />
                  <span>OBSERVABILITY, WITH CONTEXT.</span>
                </div>
                <h1 className="gsap-hero-stagger text-3xl sm:text-5xl lg:text-[52px] font-semibold tracking-tight text-[#ECEDEA] leading-[1.12]">
                  Logs tell you what happened.
                  <br />
                  <span className="text-[#A1A5A5]">LOGIQ helps you understand why.</span>
                </h1>
                <p className="gsap-hero-stagger mt-5 text-base sm:text-lg text-[#A1A5A5] leading-relaxed max-w-2xl">
                  Centralize application logs, identify anomalies, understand recurring patterns and investigate incidents through one unified observability platform.
                </p>

                <div className="gsap-hero-stagger mt-8 flex flex-wrap items-center gap-3">
                  <button
                    onClick={() => onOpenPlatform('overview')}
                    className="px-4 py-2.5 text-sm font-medium bg-[#A6C8B5] hover:bg-[#B9D6C6] text-[#101112] rounded inline-flex items-center gap-2 transition-all hover:translate-y-[-1px]"
                  >
                    <span>Explore the Platform</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setSubPage('architecture')}
                    className="px-4 py-2.5 text-sm font-medium bg-[#151719] hover:bg-[#1B1D1F] text-[#ECEDEA] border border-[#303438] rounded transition-colors"
                  >
                    Explore Architecture
                  </button>
                </div>

                <div className="gsap-hero-stagger mt-6 text-[11px] font-mono tracking-[0.12em] text-[#747A7D]">
                  CENTRALIZED LOG INTELLIGENCE / ENGINEERING PROJECT
                </div>
              </div>

              {/* Integrated Cropped Product Preview (Not a floating glass card) */}
              <div className="gsap-hero-preview mt-12 border border-[#303438] bg-[#151719] rounded-md overflow-hidden">
                <div className="px-4 py-2.5 border-b border-[#303438] bg-[#1B1D1F] flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono">
                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center gap-1.5 text-[#ECEDEA] font-semibold">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#8FBE9F] animate-pulse" />
                      LOGIQ // WORKSPACE PREVIEW
                    </span>
                    <span className="text-[#747A7D]">env: prod-eu-west-1</span>
                    <span className="px-1.5 py-0.5 bg-[#202326] border border-[#303438] rounded text-[#A1A5A5]">
                      Illustrative Demo Data
                    </span>
                  </div>
                  <button
                    onClick={() => onOpenPlatform('anomaly')}
                    className="text-[#A6C8B5] hover:underline inline-flex items-center gap-1"
                  >
                    <span>Open live investigation</span>
                    <ArrowUpRight className="w-3 h-3" />
                  </button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-[#303438]">
                  {/* Left: Compact Service Health & Anomaly Notification */}
                  <div className="lg:col-span-5 p-4 space-y-4">
                    <div className="p-3 bg-[#101112] border border-[#D77F7F]/40 rounded">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="text-[11px] font-mono text-[#D77F7F] uppercase">
                          Active Anomaly • payment-service
                        </span>
                        <StatusBadge status="critical" />
                      </div>
                      <p className="text-xs text-[#ECEDEA] font-medium">
                        +518% error template surge; 1 new circuit-breaker template observed
                      </p>
                      <div className="mt-2 text-[11px] font-mono text-[#747A7D]">
                        First observed: 01:42:10 UTC • trace: tr-8f92e1a04b
                      </div>
                    </div>

                    <div>
                      <div className="text-[10px] font-mono uppercase text-[#747A7D] mb-2">
                        Monitored Services (Snapshot)
                      </div>
                      <div className="divide-y divide-[#303438] border border-[#303438] bg-[#101112] rounded text-xs">
                        {SERVICES_DATA.slice(0, 3).map((svc) => (
                          <div key={svc.id} className="px-3 py-2 flex items-center justify-between">
                            <span className="font-mono text-[#ECEDEA]">{svc.name}</span>
                            <div className="flex items-center gap-3">
                              <span className="font-mono text-[11px] text-[#A1A5A5] tabular-nums">
                                {svc.errorRate}
                              </span>
                              <StatusBadge status={svc.status} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Right: Activity Timeline + Realistic Log Entries */}
                  <div className="lg:col-span-7 p-4 flex flex-col justify-between space-y-4">
                    <div>
                      <div className="flex items-center justify-between text-[10px] font-mono text-[#747A7D] mb-2">
                        <span>LOG & ERROR VOLUME TIMELINE (01:20 – 02:05 UTC)</span>
                        <span className="text-[#D77F7F]">Inflection @ 01:42 UTC</span>
                      </div>
                      <div className="h-28 w-full bg-[#101112] border border-[#303438] rounded p-2">
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart data={TIMELINE_SERIES_DATA}>
                            <CartesianGrid stroke="#202326" strokeDasharray="3 3" vertical={false} />
                            <XAxis dataKey="time" stroke="#747A7D" fontSize={10} tickLine={false} />
                            <YAxis stroke="#747A7D" fontSize={10} tickLine={false} width={28} />
                            <Area
                              type="monotone"
                              dataKey="total"
                              stroke="#A6C8B5"
                              fill="#A6C8B5"
                              fillOpacity={0.08}
                              strokeWidth={1.5}
                            />
                            <Area
                              type="monotone"
                              dataKey="errors"
                              stroke="#D77F7F"
                              fill="#D77F7F"
                              fillOpacity={0.18}
                              strokeWidth={1.5}
                            />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* Realistic Log Entries Strip (Live Rotating Stream) */}
                    <div className="border border-[#303438] bg-[#101112] rounded divide-y divide-[#303438] font-mono text-[11px]">
                      {previewLogs.map((entry) => (
                        <div
                          key={`${entry.id}-${streamIndex}`}
                          className="px-3 py-2 flex flex-wrap sm:flex-nowrap items-center gap-2.5 hover:bg-[#1B1D1F] transition-all duration-300"
                        >
                          <span className="text-[#747A7D] shrink-0">{entry.timestamp.slice(11, 23)}</span>
                          <SeverityBadge severity={entry.severity} />
                          <span className="text-[#A6C8B5] shrink-0">{entry.service}</span>
                          <span className="text-[#ECEDEA] truncate">{entry.message}</span>
                          <span className="ml-auto text-[#747A7D] shrink-0">{entry.traceId}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* C. PROBLEM SECTION (Clean Editorial Grid) */}
          <section className="gsap-reveal-group border-b border-[#303438] py-16 lg:py-20">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="max-w-2xl mb-12 gsap-reveal-item">
                <div className="text-[11px] font-mono uppercase tracking-[0.14em] text-[#747A7D] mb-2">
                  THE OPERATIONAL PROBLEM
                </div>
                <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#ECEDEA]">
                  Observability becomes difficult when context is scattered.
                </h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 border-t border-l border-[#303438]">
                {[
                  {
                    num: '01',
                    title: 'Fragmented logs',
                    desc: 'Application logs are distributed across services, containers, and offline dataset exports without unified indexing.'
                  },
                  {
                    num: '02',
                    title: 'Noisy data',
                    desc: 'Repetitive health checks and high-volume routine messages obscure meaningful state transitions during incidents.'
                  },
                  {
                    num: '03',
                    title: 'Slow investigations',
                    desc: 'Engineers manually correlate timestamps, service boundaries, and trace or request identifiers across disconnected views.'
                  },
                  {
                    num: '04',
                    title: 'Hidden anomalies',
                    desc: 'Gradual shifts in template frequency and newly introduced error signatures frequently go unnoticed until SLOs breach.'
                  }
                ].map((item) => (
                  <div
                    key={item.num}
                    className="gsap-reveal-item p-6 border-r border-b border-[#303438] bg-[#101112] hover:bg-[#151719]/60 transition-colors"
                  >
                    <div className="font-mono text-xs text-[#A6C8B5] mb-3">{item.num}</div>
                    <h3 className="text-base font-semibold text-[#ECEDEA] mb-2">{item.title}</h3>
                    <p className="text-xs text-[#A1A5A5] leading-relaxed">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* D. SOLUTION SECTION (4-Stage Technical Flow) */}
          <section className="gsap-reveal-group gsap-pipeline-section border-b border-[#303438] py-16 lg:py-20 bg-[#151719]/40">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="max-w-2xl mb-10 gsap-reveal-item">
                <div className="text-[11px] font-mono uppercase tracking-[0.14em] text-[#A6C8B5] mb-2">
                  THE LIFECYCLE APPROACH
                </div>
                <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#ECEDEA]">
                  From raw logs to actionable understanding.
                </h2>
              </div>

              {/* Animated Pipeline Progress Track */}
              <div className="hidden md:block h-[1px] w-full bg-[#303438] mb-6 relative overflow-hidden">
                <div className="gsap-pipeline-progress absolute inset-y-0 left-0 right-0 bg-[#A6C8B5]" />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 relative">
                {[
                  {
                    stage: '01 — COLLECT',
                    title: 'Centralized Ingestion',
                    desc: 'Bring application logs and uploaded datasets into one centralized collection pipeline.',
                    meta: 'API Gateway / OTel / Dataset Upload'
                  },
                  {
                    stage: '02 — PROCESS',
                    title: 'Stream Normalization',
                    desc: 'Normalize timestamps, validate schemas, and prepare incoming events over Kafka streams.',
                    meta: 'Kafka / Preprocessing Workers'
                  },
                  {
                    stage: '03 — UNDERSTAND',
                    title: 'Pattern & Anomaly Analysis',
                    desc: 'Identify recurring log templates, extract parameters, and detect meaningful activity shifts.',
                    meta: 'Parser / Intelligence Engine'
                  },
                  {
                    stage: '04 — INVESTIGATE',
                    title: 'Correlated Triage',
                    desc: 'Explore anomalies, sample messages, timestamps, and correlated trace identifiers in one workspace.',
                    meta: 'Explorer / Anomaly Investigation'
                  }
                ].map((step, index) => (
                  <div
                    key={step.stage}
                    className="gsap-reveal-item relative flex flex-col justify-between p-5 border border-[#303438] hover:border-[#747A7D] bg-[#151719] rounded transition-colors"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <span className="font-mono text-xs font-semibold text-[#A6C8B5]">
                          {step.stage}
                        </span>
                        {index < 3 && (
                          <span className="hidden md:inline font-mono text-xs text-[#747A7D]">→</span>
                        )}
                      </div>
                      <h3 className="text-base font-semibold text-[#ECEDEA] mb-2">{step.title}</h3>
                      <p className="text-xs text-[#A1A5A5] leading-relaxed mb-4">{step.desc}</p>
                    </div>
                    <div className="pt-3 border-t border-[#303438] font-mono text-[11px] text-[#747A7D]">
                      {step.meta}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* E. PRODUCT CAPABILITIES (Authentic Cropped UI Mockups) */}
          <section id="capabilities" className="gsap-reveal-group border-b border-[#303438] py-16 lg:py-20">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex flex-wrap items-end justify-between gap-4 mb-12 gsap-reveal-item">
                <div className="max-w-2xl">
                  <div className="text-[11px] font-mono uppercase tracking-[0.14em] text-[#A6C8B5] mb-2">
                    APPLICATION MODULES
                  </div>
                  <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#ECEDEA]">
                    Purpose-built workspaces for incident investigation.
                  </h2>
                </div>
                <button
                  onClick={() => onOpenPlatform('overview')}
                  className="text-xs font-mono text-[#A6C8B5] hover:underline inline-flex items-center gap-1"
                >
                  <span>Launch full application</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* 1. Service Overview */}
                <div className="gsap-reveal-item border border-[#303438] hover:border-[#747A7D] bg-[#151719] rounded flex flex-col justify-between transition-colors">
                  <div className="p-5">
                    <h3 className="text-base font-semibold text-[#ECEDEA]">Service Overview</h3>
                    <p className="mt-1.5 text-xs text-[#A1A5A5] leading-relaxed">
                      Understand service activity, error rate baselines, and emerging anomalies at a glance.
                    </p>
                    <div className="mt-4 p-3 bg-[#101112] border border-[#303438] rounded font-mono text-[11px] space-y-1.5">
                      <div className="flex justify-between text-[#747A7D]">
                        <span>SERVICE</span>
                        <span>ERR RATE / DELTA</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#ECEDEA]">payment-service</span>
                        <span className="text-[#D77F7F]">6.42% (+518%)</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#ECEDEA]">auth-token-verifier</span>
                        <span className="text-[#8FBE9F]">0.04% (-2%)</span>
                      </div>
                    </div>
                  </div>
                  <div className="px-5 py-3 border-t border-[#303438]">
                    <button
                      onClick={() => onOpenPlatform('overview')}
                      className="text-xs font-mono text-[#A6C8B5] hover:underline inline-flex items-center gap-1"
                    >
                      <span>Open Service Overview</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>

                {/* 2. Log Explorer */}
                <div className="gsap-reveal-item border border-[#303438] hover:border-[#747A7D] bg-[#151719] rounded flex flex-col justify-between transition-colors">
                  <div className="p-5">
                    <h3 className="text-base font-semibold text-[#ECEDEA]">Log Explorer</h3>
                    <p className="mt-1.5 text-xs text-[#A1A5A5] leading-relaxed">
                      Search and inspect individual log events using structured filters, trace IDs, and extracted parameters.
                    </p>
                    <div className="mt-4 p-3 bg-[#101112] border border-[#303438] rounded font-mono text-[11px] space-y-2">
                      <div className="px-2 py-1 bg-[#1B1D1F] border border-[#303438] rounded text-[#A6C8B5] truncate">
                        service:payment-service severity:ERROR
                      </div>
                      <div className="text-[#A1A5A5] truncate">
                        02:05:48.114Z • tx_id=tx_99b04d1e • tr-8f92e1a04b
                      </div>
                    </div>
                  </div>
                  <div className="px-5 py-3 border-t border-[#303438]">
                    <button
                      onClick={() => onOpenPlatform('explorer')}
                      className="text-xs font-mono text-[#A6C8B5] hover:underline inline-flex items-center gap-1"
                    >
                      <span>Open Log Explorer</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>

                {/* 3. Anomaly Investigation */}
                <div className="gsap-reveal-item border border-[#303438] hover:border-[#747A7D] bg-[#151719] rounded flex flex-col justify-between transition-colors">
                  <div className="p-5">
                    <h3 className="text-base font-semibold text-[#ECEDEA]">Anomaly Investigation</h3>
                    <p className="mt-1.5 text-xs text-[#A1A5A5] leading-relaxed">
                      Investigate unusual log activity through inflection timelines, changed templates, and correlated traces.
                    </p>
                    <div className="mt-4 p-3 bg-[#101112] border border-[#303438] rounded font-mono text-[11px] space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[#D6AD75]">Newly Observed Template</span>
                        <span className="text-[#ECEDEA]">96 / hr</span>
                      </div>
                      <div className="text-[#747A7D] truncate">
                        Circuit breaker CLOSED -&gt; OPEN provider=&lt;*&gt;
                      </div>
                    </div>
                  </div>
                  <div className="px-5 py-3 border-t border-[#303438]">
                    <button
                      onClick={() => onOpenPlatform('anomaly')}
                      className="text-xs font-mono text-[#A6C8B5] hover:underline inline-flex items-center gap-1"
                    >
                      <span>Open Anomaly Investigation</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>

                {/* 4. Template Intelligence */}
                <div className="gsap-reveal-item border border-[#303438] hover:border-[#747A7D] bg-[#151719] rounded flex flex-col justify-between transition-colors">
                  <div className="p-5">
                    <h3 className="text-base font-semibold text-[#ECEDEA]">Template Intelligence</h3>
                    <p className="mt-1.5 text-xs text-[#A1A5A5] leading-relaxed">
                      Understand recurring log patterns, parameter signatures, and frequency shifts over time.
                    </p>
                    <div className="mt-4 p-3 bg-[#101112] border border-[#303438] rounded font-mono text-[11px] space-y-1.5">
                      <div className="text-[#ECEDEA] truncate">
                        timeout after &lt;*&gt;ms for tx_id=&lt;*&gt;
                      </div>
                      <div className="flex justify-between text-[#747A7D]">
                        <span>1,842 / hr</span>
                        <span className="text-[#D77F7F]">+13,057%</span>
                      </div>
                    </div>
                  </div>
                  <div className="px-5 py-3 border-t border-[#303438]">
                    <button
                      onClick={() => onOpenPlatform('templates')}
                      className="text-xs font-mono text-[#A6C8B5] hover:underline inline-flex items-center gap-1"
                    >
                      <span>Open Template Explorer</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>

                {/* 5. Platform Health */}
                <div className="gsap-reveal-item border border-[#303438] hover:border-[#747A7D] bg-[#151719] rounded flex flex-col justify-between transition-colors">
                  <div className="p-5">
                    <h3 className="text-base font-semibold text-[#ECEDEA]">Platform Health</h3>
                    <p className="mt-1.5 text-xs text-[#A1A5A5] leading-relaxed">
                      Monitor the internal health of LOGIQ’s own API workers, Kafka queues, PostgreSQL, and MinIO.
                    </p>
                    <div className="mt-4 p-3 bg-[#101112] border border-[#303438] rounded font-mono text-[11px] space-y-1.5">
                      <div className="flex justify-between">
                        <span className="text-[#A1A5A5]">Kafka Consumer Lag</span>
                        <span className="text-[#8FBE9F]">142 msgs</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#A1A5A5]">Parser Workers</span>
                        <span className="text-[#8FBE9F]">4 / 4 Healthy</span>
                      </div>
                    </div>
                  </div>
                  <div className="px-5 py-3 border-t border-[#303438]">
                    <button
                      onClick={() => onOpenPlatform('health')}
                      className="text-xs font-mono text-[#A6C8B5] hover:underline inline-flex items-center gap-1"
                    >
                      <span>Open Platform Health</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>

                {/* 6. Dataset Management */}
                <div className="gsap-reveal-item border border-[#303438] hover:border-[#747A7D] bg-[#151719] rounded flex flex-col justify-between transition-colors">
                  <div className="p-5">
                    <h3 className="text-base font-semibold text-[#ECEDEA]">Dataset Management</h3>
                    <p className="mt-1.5 text-xs text-[#A1A5A5] leading-relaxed">
                      Upload static log datasets, monitor batch ingestion status, and inspect parsing diagnostics.
                    </p>
                    <div className="mt-4 p-3 bg-[#101112] border border-[#303438] rounded font-mono text-[11px] space-y-1.5">
                      <div className="text-[#ECEDEA] truncate">
                        payment-incident-capture.jsonl
                      </div>
                      <div className="flex justify-between text-[#747A7D]">
                        <span>48,912 records</span>
                        <span className="text-[#8FBE9F]">Ready</span>
                      </div>
                    </div>
                  </div>
                  <div className="px-5 py-3 border-t border-[#303438]">
                    <button
                      onClick={() => onOpenPlatform('datasets')}
                      className="text-xs font-mono text-[#A6C8B5] hover:underline inline-flex items-center gap-1"
                    >
                      <span>Open Dataset Management</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* F. INTERACTIVE ARCHITECTURE SECTION */}
          <section className="border-b border-[#303438] py-16 lg:py-20 bg-[#151719]/25">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div className="max-w-2xl">
                  <div className="text-[11px] font-mono uppercase tracking-[0.14em] text-[#A6C8B5] mb-2">
                    INTERNAL ARCHITECTURE
                  </div>
                  <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#ECEDEA]">
                    An architecture designed around the log lifecycle.
                  </h2>
                  <p className="mt-2 text-sm text-[#A1A5A5]">
                    LOGIQ brings together collection, distributed processing, intelligence and analytics through a modular architecture.
                  </p>
                </div>
                <button
                  onClick={() => setSubPage('architecture')}
                  className="px-3.5 py-2 text-xs font-medium bg-[#1B1D1F] hover:bg-[#202326] text-[#ECEDEA] border border-[#303438] rounded inline-flex items-center gap-1.5"
                >
                  <span>Explore the complete architecture</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <ArchitectureExplorer
                compact={true}
                gsapReady={gsapReady}
                onOpenFullArchitecture={() => setSubPage('architecture')}
              />
            </div>
          </section>

          {/* G. HOW TO USE LOGIQ (Developer Onboarding Guide) */}
          <section className="border-b border-[#303438] py-16 lg:py-20">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="max-w-2xl mb-12">
                <div className="text-[11px] font-mono uppercase tracking-[0.14em] text-[#A6C8B5] mb-2">
                  DEVELOPER WORKFLOW
                </div>
                <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#ECEDEA]">
                  Connect a service. Start investigating.
                </h2>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                <div className="lg:col-span-6 space-y-4">
                  {[
                    {
                      step: 'Step 01',
                      title: 'Configure a log source',
                      desc: 'Register your service or configure OpenTelemetry Collector / Fluent Bit to forward structured logs, or prepare a JSONL dataset archive.'
                    },
                    {
                      step: 'Step 02',
                      title: 'Send logs into the collection layer',
                      desc: 'Transmit log batches via the supported HTTP ingestion interface or upload a dataset file through Dataset Management.'
                    },
                    {
                      step: 'Step 03',
                      title: 'Allow the processing pipeline to normalize and analyze',
                      desc: 'Kafka streams route incoming payloads through Preprocessing and Parser workers to extract templates and evaluate frequency baselines.'
                    },
                    {
                      step: 'Step 04',
                      title: 'Investigate service activity, templates, and anomalies',
                      desc: 'Open Overview, Log Explorer, or Anomaly Investigation to filter by service, template signature, or trace ID.'
                    }
                  ].map((s) => (
                    <div key={s.step} className="p-4 border border-[#303438] bg-[#151719] rounded">
                      <div className="text-[11px] font-mono text-[#A6C8B5]">{s.step}</div>
                      <h3 className="text-sm font-semibold text-[#ECEDEA] mt-1">{s.title}</h3>
                      <p className="text-xs text-[#A1A5A5] mt-1 leading-relaxed">{s.desc}</p>
                    </div>
                  ))}
                </div>

                {/* Illustrative Pseudocode / Schema Contract */}
                <div className="lg:col-span-6 border border-[#303438] bg-[#151719] rounded overflow-hidden">
                  <div className="px-4 py-2.5 border-b border-[#303438] bg-[#1B1D1F] flex items-center justify-between text-[11px] font-mono">
                    <span className="text-[#ECEDEA]">Illustrative Log Event Payload (Conceptual Schema)</span>
                    <span className="text-[#747A7D]">JSON / UTF-8</span>
                  </div>
                  <pre className="p-4 font-mono text-xs text-[#A1A5A5] overflow-x-auto leading-relaxed">
{`// Illustrative log structure accepted by the collection pipeline
// Exact endpoint path and auth headers depend on deployment config
{
  "timestamp": "2026-11-23T02:05:48.114Z",
  "service": "payment-service",
  "environment": "prod-eu-west-1",
  "severity": "ERROR",
  "message": "Upstream settlement gateway timeout after 5000ms for tx_id=tx_99b04d1e (attempt 3/3)",
  "trace_id": "tr-8f92e1a04b",
  "request_id": "req-0094910",
  "attributes": {
    "provider": "adyen-eu",
    "http_status": 504
  }
}

// Expected Pipeline Output:
// -> Normalized in Preprocessing Service
// -> Template ID: tpl-pay-timeout
// -> Visible in: Overview, Log Explorer, Template Explorer`}
                  </pre>
                  <div className="px-4 py-3 border-t border-[#303438] bg-[#101112] flex items-center justify-between">
                    <span className="text-[11px] text-[#747A7D]">
                      See documentation for verified schema details and dataset formats.
                    </span>
                    <button
                      onClick={() => onOpenDocs('log-collection')}
                      className="text-xs font-mono text-[#A6C8B5] hover:underline inline-flex items-center gap-1"
                    >
                      <span>Read Integration Guide</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* H. TECHNOLOGY SECTION (Monochrome Engineering Stack) */}
          <section id="technology" className="gsap-reveal-group border-b border-[#303438] py-16 lg:py-20 bg-[#151719]/30">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="max-w-2xl mb-10 gsap-reveal-item">
                <div className="text-[11px] font-mono uppercase tracking-[0.14em] text-[#A6C8B5] mb-2">
                  ENGINEERING STACK
                </div>
                <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#ECEDEA]">
                  Built with a modular engineering stack.
                </h2>
                <p className="mt-2 text-xs text-[#A1A5A5]">
                  Technologies organized by architectural role. Integration maturity varies across core services and optional collectors.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {[
                  {
                    role: 'Backend',
                    items: ['Python 3.11+', 'FastAPI', 'Pydantic', 'SQLAlchemy', 'Alembic']
                  },
                  {
                    role: 'Streaming & Distributed Processing',
                    items: ['Apache Kafka', 'Redis']
                  },
                  {
                    role: 'Storage',
                    items: ['PostgreSQL', 'MinIO']
                  },
                  {
                    role: 'Collection & Self-Observability',
                    items: ['OpenTelemetry Collector', 'Fluent Bit (where appropriate)', 'Prometheus', 'Grafana']
                  },
                  {
                    role: 'Frontend',
                    items: ['React', 'TypeScript', 'Vite', 'Tailwind CSS', 'Recharts', 'React Router', 'TanStack Query']
                  },
                  {
                    role: 'Infrastructure',
                    items: ['Docker', 'Docker Compose']
                  }
                ].map((group) => (
                  <div
                    key={group.role}
                    className="gsap-reveal-item p-5 border border-[#303438] hover:border-[#747A7D] bg-[#151719] rounded transition-colors"
                  >
                    <div className="text-xs font-mono uppercase tracking-wider text-[#A1A5A5] mb-3 pb-2 border-b border-[#303438]">
                      {group.role}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {group.items.map((tech) => (
                        <span
                          key={tech}
                          className="px-2.5 py-1 text-xs font-mono text-[#ECEDEA] bg-[#101112] border border-[#303438] rounded"
                        >
                          {tech}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* I. ABOUT LOGIQ */}
          <section id="about" className="border-b border-[#303438] py-16 lg:py-20">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
              <div className="lg:col-span-7 space-y-4">
                <div className="text-[11px] font-mono uppercase tracking-[0.14em] text-[#A6C8B5]">
                  PROJECT FOCUS
                </div>
                <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#ECEDEA]">
                  Built to make log intelligence more accessible.
                </h2>
                <p className="text-sm text-[#A1A5A5] leading-relaxed">
                  LOGIQ is a modular centralized log intelligence and observability engineering project focused on turning high-volume raw telemetry into structured operational context. Rather than relying on opaque black-box claims, it emphasizes clear service boundaries, deterministic template extraction, and trace-correlated incident workflows.
                </p>
                <div className="pt-2 text-xs font-mono text-[#747A7D]">
                  Maintainers: LOGIQ Engineering Contributors (Open Architecture Reference)
                </div>
              </div>
              <div className="lg:col-span-5 border border-[#303438] bg-[#151719] p-5 rounded space-y-3">
                <div className="text-xs font-mono uppercase text-[#747A7D]">Core Engineering Pillars</div>
                <ul className="space-y-2.5 text-xs text-[#ECEDEA]">
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-[#A6C8B5]" /> Distributed log processing over Kafka streams
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-[#A6C8B5]" /> Structured log normalization & parameter extraction
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-[#A6C8B5]" /> Recurring template mining & frequency tracking
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-[#A6C8B5]" /> Evidence-first anomaly investigation
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-[#A6C8B5]" /> Explicit separation of external & internal observability
                  </li>
                </ul>
              </div>
            </div>
          </section>

          {/* J. FINAL CTA */}
          <section className="py-16 lg:py-20 bg-[#151719]/40">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
              <div>
                <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#ECEDEA]">
                  Make every log more useful.
                </h2>
                <p className="mt-1.5 text-sm text-[#A1A5A5]">
                  Inspect the interactive observability workspace or review the 7-layer system architecture.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => onOpenPlatform('overview')}
                  className="px-4 py-2.5 text-sm font-medium bg-[#A6C8B5] hover:bg-[#B9D6C6] text-[#101112] rounded"
                >
                  Explore the Platform
                </button>
                <button
                  onClick={() => setSubPage('architecture')}
                  className="px-4 py-2.5 text-sm font-medium bg-[#151719] hover:bg-[#1B1D1F] text-[#ECEDEA] border border-[#303438] rounded"
                >
                  View Architecture
                </button>
              </div>
            </div>
          </section>
        </main>
      )}

      {/* Compact Technical Footer */}
      <footer className="border-t border-[#303438] bg-[#101112] py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-4 text-xs text-[#747A7D]">
          <div className="flex items-center gap-2 font-mono text-[#ECEDEA]">
            <span className="w-2 h-2 bg-[#A6C8B5]" />
            <span>LOGIQ</span>
            <span className="text-[#747A7D]">— Centralized Log Intelligence</span>
          </div>
          <div className="flex flex-wrap items-center gap-5">
            <button onClick={() => onOpenPlatform('overview')} className="hover:text-[#ECEDEA]">
              Platform
            </button>
            <button onClick={() => setSubPage('architecture')} className="hover:text-[#ECEDEA]">
              Architecture
            </button>
            <button onClick={() => onOpenDocs('intro')} className="hover:text-[#ECEDEA]">
              Documentation
            </button>
            <button onClick={() => scrollToSection('technology')} className="hover:text-[#ECEDEA]">
              Technology
            </button>
            <button onClick={() => scrollToSection('about')} className="hover:text-[#ECEDEA]">
              About
            </button>
            <span className="font-mono text-[#747A7D]">GitHub (Placeholder)</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

/**
 * ============================================================================
 * PART 4 — DOCUMENTATION AND DEVELOPER GUIDE
 * ============================================================================
 */
const DocumentationView = ({ activeDocId, setActiveDocId, onBackToWebsite, onOpenPlatform }) => {
  const currentDoc = useMemo(
    () => DOCS_PAGES.find((d) => d.id === activeDocId) || DOCS_PAGES[0],
    [activeDocId]
  );

  const sections = ['Getting Started', 'Architecture', 'Ingestion & Data', 'Processing & Intelligence', 'Operations'];

  return (
    <div className="min-h-screen bg-[#101112] text-[#ECEDEA] flex flex-col">
      {/* Top Documentation Bar */}
      <header className="sticky top-0 z-30 h-14 border-b border-[#303438] bg-[#101112]/95 px-4 sm:px-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={onBackToWebsite}
            className="flex items-center gap-2 font-mono text-sm font-semibold tracking-wider text-[#ECEDEA]"
          >
            <span className="w-2 h-2 bg-[#A6C8B5]" />
            <span>LOGIQ</span>
          </button>
          <span className="text-[#303438]">/</span>
          <span className="text-xs font-mono text-[#A1A5A5]">Documentation</span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onBackToWebsite}
            className="text-xs text-[#A1A5A5] hover:text-[#ECEDEA]"
          >
            Website
          </button>
          <button
            onClick={() => onOpenPlatform('overview')}
            className="px-3 py-1.5 text-xs font-medium bg-[#A6C8B5] hover:bg-[#B9D6C6] text-[#101112] rounded"
          >
            Open Platform
          </button>
        </div>
      </header>

      <div className="max-w-7xl w-full mx-auto flex-1 grid grid-cols-1 md:grid-cols-12">
        {/* Left Sidebar Navigation */}
        <aside className="md:col-span-3 border-b md:border-b-0 md:border-r border-[#303438] p-4 sm:p-6 space-y-6 bg-[#151719]/40">
          {sections.map((sec) => (
            <div key={sec}>
              <div className="text-[10px] font-mono uppercase tracking-wider text-[#747A7D] mb-2">
                {sec}
              </div>
              <div className="space-y-1">
                {DOCS_PAGES.filter((p) => p.section === sec).map((page) => {
                  const active = page.id === currentDoc.id;
                  return (
                    <button
                      key={page.id}
                      onClick={() => setActiveDocId(page.id)}
                      className={`block w-full text-left px-2.5 py-1.5 rounded text-xs transition-colors ${
                        active
                          ? 'bg-[#A6C8B5]/12 text-[#A6C8B5] font-medium border border-[#A6C8B5]/30'
                          : 'text-[#A1A5A5] hover:text-[#ECEDEA] hover:bg-[#1B1D1F]'
                      }`}
                    >
                      {page.title}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </aside>

        {/* Main Technical Article Area */}
        <article className="md:col-span-7 p-6 sm:p-10 space-y-6">
          <div className="border-b border-[#303438] pb-5">
            <div className="text-[11px] font-mono uppercase text-[#A6C8B5] mb-1">
              {currentDoc.section}
            </div>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#ECEDEA]">
              {currentDoc.title}
            </h1>
            <p className="mt-2 text-sm text-[#A1A5A5] leading-relaxed">{currentDoc.summary}</p>
          </div>

          <div className="space-y-4 text-sm text-[#ECEDEA]/90 leading-relaxed">
            {currentDoc.body.map((paragraph, idx) => (
              <p key={idx}>{paragraph}</p>
            ))}
          </div>

          {currentDoc.codeNote && (
            <div className="border border-[#303438] bg-[#151719] rounded overflow-hidden">
              <div className="px-4 py-2 border-b border-[#303438] bg-[#1B1D1F] flex items-center justify-between">
                <span className="text-xs font-mono text-[#A1A5A5]">{currentDoc.codeNote.label}</span>
                <CopyButton text={currentDoc.codeNote.code} />
              </div>
              <pre className="p-4 font-mono text-xs text-[#ECEDEA] overflow-x-auto leading-relaxed">
                {currentDoc.codeNote.code}
              </pre>
            </div>
          )}

          {/* Related Pages */}
          <div className="pt-6 border-t border-[#303438]">
            <div className="text-[11px] font-mono uppercase text-[#747A7D] mb-3">Related Pages</div>
            <div className="flex flex-wrap gap-2">
              {currentDoc.related.map((relId) => {
                const relDoc = DOCS_PAGES.find((d) => d.id === relId);
                if (!relDoc) return null;
                return (
                  <button
                    key={relId}
                    onClick={() => setActiveDocId(relId)}
                    className="px-3 py-1.5 text-xs bg-[#151719] hover:bg-[#1B1D1F] border border-[#303438] rounded text-[#A6C8B5]"
                  >
                    {relDoc.title} →
                  </button>
                );
              })}
            </div>
          </div>
        </article>

        {/* Right-Side Table of Contents */}
        <aside className="hidden md:block md:col-span-2 border-l border-[#303438] p-6">
          <div className="text-[10px] font-mono uppercase tracking-wider text-[#747A7D] mb-3">
            On This Page
          </div>
          <ul className="space-y-2 text-xs text-[#A1A5A5]">
            <li className="text-[#ECEDEA]">Overview</li>
            <li>Operational Context</li>
            {currentDoc.codeNote && <li>Schema / Configuration</li>}
            <li>Related Topics</li>
          </ul>
        </aside>
      </div>
    </div>
  );
};

/**
 * ============================================================================
 * PART 5 — LOGIQ ENGINEERING APPLICATION
 * Persistent shell with Overview, Services, Anomalies, Log Explorer,
 * Templates, Datasets, Sources, Platform Health, and Settings.
 * ============================================================================
 */
const EMPTY_ANOMALY = {
  id: '', title: 'No anomalies in this window', service: '—', severity: 'unknown', status: '—',
  firstObserved: '—', lastObserved: '—', changeSummary: '—', summary: 'No anomaly data is available yet.',
  changedTemplates: [], correlatedTraceIds: [], correlatedRequestIds: []
};
const EMPTY_TEMPLATE = {
  id: '', service: '—', tag: '—', template: 'No templates have been discovered yet.', frequency: '—',
  trend: '—', firstSeen: '—', lastSeen: '—', sparkline: [], parameters: [], examples: []
};

const LogiqApplication = ({
  initialTab = 'overview',
  onBackToWebsite,
  onOpenDocs,
  gsapReady
}) => {
  const [activeTab, setActiveTab] = useState(initialTab);
  const [sidebarMobileOpen, setSidebarMobileOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [liveEvents, setLiveEvents] = useState([]);
  const appContentRef = useRef(null);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  // Global Application Context State
  const [environment, setEnvironment] = useState('prod-eu-west-1');
  const [timeRange, setTimeRange] = useState('Last 1h');

  // Log Explorer Filter State
  const [explorerQuery, setExplorerQuery] = useState('service:payment-service severity:ERROR');
  const [selectedServiceFilter, setSelectedServiceFilter] = useState('all');
  const [selectedSeverityFilter, setSelectedSeverityFilter] = useState('all');
  const [selectedTemplateFilter, setSelectedTemplateFilter] = useState('all');
  const [selectedTraceFilter, setSelectedTraceFilter] = useState('');
  const [explorerSearchInput, setExplorerSearchInput] = useState('');
  const [expandedLogId, setExpandedLogId] = useState('log-1001');
  const [liveTailDemo, setLiveTailDemo] = useState(false);

  // Anomaly Investigation State
  const [selectedAnomalyId, setSelectedAnomalyId] = useState('anom-2026-084');
  const [anomalyStatuses, setAnomalyStatuses] = useState({
    'anom-2026-084': 'investigating',
    'anom-2026-083': 'open'
  });

  // Template Explorer Drawer State
  const [selectedTemplateId, setSelectedTemplateId] = useState('tpl-pay-timeout');

  // Live backend data (see src/api). Shadows the demo mock constants inside this component.
  const live = useLogiqData();
  const {
    services: SERVICES_DATA, anomalies: ANOMALIES_DATA, templates: TEMPLATES_DATA,
    logs: LOG_ENTRIES_DATA, timeline: TIMELINE_SERIES_DATA, datasets: LIVE_DATASETS,
    platformHealth: PLATFORM_HEALTH_COMPONENTS, sources: SOURCES_DATA
  } = live;

  // Datasets State (seeded from the backend; kept in sync on each refresh)
  const [datasets, setDatasets] = useState([]);
  useEffect(() => { setDatasets(LIVE_DATASETS); }, [LIVE_DATASETS]);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [uploadingDataset, setUploadingDataset] = useState(false);

  // Animate Application View Transitions & Metric Counters via GSAP
  useEffect(() => {
    if (!gsapReady || !window.gsap || !appContentRef.current) return;
    const gsap = window.gsap;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        '.gsap-app-view',
        { opacity: 0, y: 10 },
        { opacity: 1, y: 0, duration: 0.32, ease: 'power2.out', clearProps: 'transform' }
      );

      gsap.utils.toArray('.gsap-kpi-number').forEach((el) => {
        const target = parseInt(el.dataset.target || '0', 10);
        const obj = { val: 0 };
        gsap.to(obj, {
          val: target,
          duration: 0.65,
          ease: 'power2.out',
          onUpdate: () => {
            el.textContent = Math.round(obj.val).toString();
          }
        });
      });
    }, appContentRef);

    return () => ctx.revert();
  }, [activeTab, gsapReady]);

  // Simulated Live Tail Event Stream when toggled in Log Explorer
  useEffect(() => {
    if (!liveTailDemo) {
      setLiveEvents([]);
      return;
    }
    const templates = [
      {
        service: 'payment-service',
        severity: 'ERROR',
        templateId: 'tpl-pay-timeout',
        template: 'Upstream settlement gateway timeout after <*>ms for tx_id=<*> (attempt <*>/3)',
        message: 'Upstream settlement gateway timeout after 5000ms for tx_id=tx_99b04d1e (attempt 3/3)',
        traceId: 'tr-8f92e1a04b',
        requestId: 'req-0094910',
        source: 'otel-collector-02',
        parameters: { duration_ms: 5000, tx_id: 'tx_99b04d1e', attempt: 3 },
        attributes: { host: 'pay-worker-03.eu-west-1', region: 'eu-west-1', http_status: 504 }
      },
      {
        service: 'checkout-gateway',
        severity: 'WARN',
        templateId: 'tpl-chk-retry',
        template: 'Retrying downstream authorization call to payment-service trace=<*> backoff=<*>ms',
        message: 'Retrying downstream authorization call to payment-service trace=tr-8f92e1a04b backoff=500ms',
        traceId: 'tr-8f92e1a04b',
        requestId: 'req-0094910',
        source: 'fluent-bit-ingress',
        parameters: { trace: 'tr-8f92e1a04b', backoff_ms: 500 },
        attributes: { host: 'chk-edge-01.eu-west-1', route: 'POST /v2/checkout/confirm', attempt: 3 }
      },
      {
        service: 'auth-token-verifier',
        severity: 'INFO',
        templateId: 'tpl-auth-ok',
        template: 'JWT signature verified key_id=<*> subject=<*> ttl=<*>s',
        message: 'JWT signature verified key_id=k_2026_11 subject=usr_51209 ttl=3599s',
        traceId: 'tr-4b11c90a8d',
        requestId: 'req-0094914',
        source: 'otel-collector-01',
        parameters: { key_id: 'k_2026_11', subject: 'usr_51209', ttl: 3599 },
        attributes: { host: 'auth-pod-04.eu-west-1', alg: 'EdDSA' }
      }
    ];

    let counter = 0;
    const interval = setInterval(() => {
      const sample = templates[counter % templates.length];
      counter += 1;
      const nowIso = new Date().toISOString();
      setLiveEvents((prev) => [
        {
          ...sample,
          id: `live-${Date.now()}`,
          timestamp: nowIso
        },
        ...prev.slice(0, 9)
      ]);
    }, 2600);

    return () => clearInterval(interval);
  }, [liveTailDemo]);

  // Filtered Logs Computation
  const filteredLogs = useMemo(() => {
    const combinedLogs = [...liveEvents, ...LOG_ENTRIES_DATA];
    return combinedLogs.filter((log) => {
      if (selectedServiceFilter !== 'all' && log.service !== selectedServiceFilter) return false;
      if (selectedSeverityFilter !== 'all' && log.severity !== selectedSeverityFilter) return false;
      if (selectedTemplateFilter !== 'all' && log.templateId !== selectedTemplateFilter) return false;
      if (
        selectedTraceFilter.trim() &&
        !log.traceId.toLowerCase().includes(selectedTraceFilter.trim().toLowerCase()) &&
        !log.requestId.toLowerCase().includes(selectedTraceFilter.trim().toLowerCase())
      ) {
        return false;
      }
      if (
        explorerSearchInput.trim() &&
        !log.message.toLowerCase().includes(explorerSearchInput.trim().toLowerCase()) &&
        !log.service.toLowerCase().includes(explorerSearchInput.trim().toLowerCase()) &&
        !log.traceId.toLowerCase().includes(explorerSearchInput.trim().toLowerCase())
      ) {
        return false;
      }
      return true;
    });
  }, [
    liveEvents,
    selectedServiceFilter,
    selectedSeverityFilter,
    selectedTemplateFilter,
    selectedTraceFilter,
    explorerSearchInput
  ]);

  // Cross-Page Investigation Helpers
  const navigateToLogsWithFilter = ({ service = 'all', severity = 'all', templateId = 'all', traceId = '' }) => {
    setSelectedServiceFilter(service);
    setSelectedSeverityFilter(severity);
    setSelectedTemplateFilter(templateId);
    setSelectedTraceFilter(traceId);
    const parts = [];
    if (service !== 'all') parts.push(`service:${service}`);
    if (severity !== 'all') parts.push(`severity:${severity}`);
    if (templateId !== 'all') parts.push(`template:${templateId}`);
    if (traceId) parts.push(`trace:${traceId}`);
    setExplorerQuery(parts.join(' ') || '*');
    setActiveTab('explorer');
  };

  const navigateToAnomaly = (anomalyId) => {
    setSelectedAnomalyId(anomalyId);
    setActiveTab('anomaly');
  };

  const handleSimulatedUpload = (fileName = 'custom-service-capture-2026.jsonl') => {
    setUploadingDataset(true);
    setTimeout(() => {
      const newDs = {
        id: `ds-0${datasets.length + 17}`,
        name: fileName,
        sourceType: 'JSONL Batch Upload',
        uploadStatus: 'Uploaded',
        processingStatus: 'Ready',
        recordCount: '12,480',
        createdAt: 'Just now',
        size: '4.8 MB'
      };
      setDatasets((prev) => [newDs, ...prev]);
      setUploadingDataset(false);
    }, 900);
  };

  const activeAnomaly = useMemo(
    () => ANOMALIES_DATA.find((a) => a.id === selectedAnomalyId) || ANOMALIES_DATA[0] || EMPTY_ANOMALY,
    [selectedAnomalyId]
  );

  const activeTemplate = useMemo(
    () => TEMPLATES_DATA.find((t) => t.id === selectedTemplateId) || TEMPLATES_DATA[0] || EMPTY_TEMPLATE,
    [selectedTemplateId]
  );

  const navGroups = [
    {
      label: 'OBSERVE',
      items: [
        { id: 'overview', label: 'Overview', icon: LayoutGrid },
        { id: 'services', label: 'Services', icon: Server }
      ]
    },
    {
      label: 'INVESTIGATE',
      items: [
        { id: 'anomaly', label: 'Anomalies', icon: AlertTriangle, badge: '2' },
        { id: 'explorer', label: 'Log Explorer', icon: Terminal },
        { id: 'templates', label: 'Templates', icon: Layers }
      ]
    },
    {
      label: 'MANAGE',
      items: [
        { id: 'datasets', label: 'Datasets', icon: Database },
        { id: 'sources', label: 'Sources', icon: GitBranch }
      ]
    },
    {
      label: 'SYSTEM',
      items: [
        { id: 'health', label: 'Platform Health', icon: Activity },
        { id: 'settings', label: 'Settings', icon: Settings }
      ]
    }
  ];

  const pageTitles = {
    overview: 'Overview',
    services: 'Services',
    anomaly: 'Anomaly Investigation',
    explorer: 'Log Explorer',
    templates: 'Template Explorer',
    datasets: 'Datasets',
    sources: 'Sources',
    health: 'Platform Health',
    settings: 'Settings'
  };

  return (
    <div className="min-h-screen bg-[#101112] text-[#ECEDEA] flex flex-col lg:flex-row">
      {live.errors.length > 0 && (
        <div role="status" className="fixed top-0 inset-x-0 z-[60] bg-[#D77F7F]/15 border-b border-[#D77F7F]/30 text-[#F0C4C4] text-xs px-4 py-2">
          Some live data is unavailable: {live.errors.join(' · ')}
        </div>
      )}
      {/* Mobile Sidebar Backdrop */}
      {sidebarMobileOpen && (
        <div
          onClick={() => setSidebarMobileOpen(false)}
          className="fixed inset-0 bg-black/60 z-40 lg:hidden"
        />
      )}

      {/* NARROW COMPACT APPLICATION SIDEBAR */}
      <aside
        className={`fixed lg:sticky top-0 left-0 z-50 h-screen w-60 bg-[#151719] border-r border-[#303438] flex flex-col justify-between transition-transform duration-200 ${
          sidebarMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div>
          {/* Top Wordmark + Environment Selector */}
          <div className="p-4 border-b border-[#303438] space-y-3">
            <div className="flex items-center justify-between">
              <button
                onClick={onBackToWebsite}
                className="flex items-center gap-2 font-mono text-sm font-semibold tracking-[0.14em] text-[#ECEDEA]"
                title="Return to LOGIQ Public Website"
              >
                <span className="w-2 h-2 bg-[#A6C8B5]" />
                <span>LOGIQ</span>
              </button>
              <button
                onClick={onBackToWebsite}
                className="text-[11px] font-mono text-[#747A7D] hover:text-[#A6C8B5]"
              >
                ← Site
              </button>
            </div>

            <select
              value={environment}
              onChange={(e) => setEnvironment(e.target.value)}
              className="w-full px-2.5 py-1.5 text-xs font-mono bg-[#101112] border border-[#303438] rounded text-[#ECEDEA] focus:outline-none focus:border-[#A6C8B5]"
            >
              <option value="prod-eu-west-1">env: prod-eu-west-1</option>
              <option value="staging-eu-west-1">env: staging-eu-west-1</option>
              <option value="local-replay">env: local-replay</option>
            </select>
          </div>

          {/* Navigation Groups */}
          <nav className="p-3 space-y-5 overflow-y-auto">
            {navGroups.map((group) => (
              <div key={group.label}>
                <div className="px-2.5 mb-1.5 text-[10px] font-mono uppercase tracking-wider text-[#747A7D]">
                  {group.label}
                </div>
                <div className="space-y-0.5">
                  {group.items.map((item) => {
                    const Icon = item.icon;
                    const active = activeTab === item.id;
                    return (
                      <button
                        key={item.id}
                        onClick={() => {
                          setActiveTab(item.id);
                          setSidebarMobileOpen(false);
                        }}
                        className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs transition-colors ${
                          active
                            ? 'bg-[#A6C8B5]/12 text-[#A6C8B5] font-medium border border-[#A6C8B5]/30'
                            : 'text-[#A1A5A5] hover:text-[#ECEDEA] hover:bg-[#1B1D1F]'
                        }`}
                      >
                        <span className="flex items-center gap-2.5">
                          <Icon className="w-3.5 h-3.5" />
                          <span>{item.label}</span>
                        </span>
                        {item.badge && (
                          <span className="px-1.5 py-0.5 text-[10px] font-mono bg-[#D6AD75]/15 text-[#D6AD75] border border-[#D6AD75]/30 rounded">
                            {item.badge}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </nav>
        </div>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-[#303438] space-y-2 text-[11px]">
          <button
            onClick={() => onOpenDocs('intro')}
            className="w-full flex items-center justify-between px-2.5 py-1.5 text-[#A1A5A5] hover:text-[#ECEDEA] hover:bg-[#1B1D1F] rounded"
          >
            <span className="flex items-center gap-2">
              <BookOpen className="w-3.5 h-3.5" />
              <span>Documentation</span>
            </span>
            <ExternalLink className="w-3 h-3" />
          </button>
          <div className="px-2.5 py-1.5 bg-[#101112] border border-[#303438] rounded flex items-center justify-between font-mono text-[10px] text-[#747A7D]">
            <span>sre-operator</span>
            <span>v0.4-alpha</span>
          </div>
        </div>
      </aside>

      {/* MAIN APPLICATION WORKSPACE */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Main Persistent Application Header */}
        <header className="sticky top-0 z-30 h-14 border-b border-[#303438] bg-[#101112]/95 px-4 sm:px-6 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarMobileOpen(true)}
              className="lg:hidden p-1.5 text-[#A1A5A5] hover:text-[#ECEDEA] border border-[#303438] rounded"
            >
              <Menu className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-2 text-xs">
              <span className="font-mono text-[#747A7D] hidden sm:inline">{environment}</span>
              <span className="text-[#303438] hidden sm:inline">/</span>
              <span className="font-semibold text-[#ECEDEA]">{pageTitles[activeTab]}</span>
            </div>
            <span className="hidden md:inline-block px-2 py-0.5 text-[10px] font-mono bg-[#151719] border border-[#303438] rounded text-[#747A7D]">
              Illustrative Demo Dataset
            </span>
          </div>

          {/* Global Time Range & Refresh Controls */}
          <div className="flex items-center gap-2">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#151719] border border-[#303438] rounded text-xs">
              <Clock className="w-3.5 h-3.5 text-[#A6C8B5]" />
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="bg-transparent text-[#ECEDEA] font-mono text-xs focus:outline-none"
              >
                <option value="Last 15m">Last 15m</option>
                <option value="Last 1h">Last 1h</option>
                <option value="Last 6h">Last 6h</option>
                <option value="Last 24h">Last 24h</option>
              </select>
            </div>

            <button
              onClick={() => {
                setIsRefreshing(true);
                setTimeout(() => setIsRefreshing(false), 550);
              }}
              title="Refresh view"
              className="p-1.5 text-[#A1A5A5] hover:text-[#ECEDEA] bg-[#151719] border border-[#303438] rounded"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 transition-transform duration-500 ${
                  isRefreshing ? 'rotate-180 text-[#A6C8B5]' : ''
                }`}
              />
            </button>
          </div>
        </header>

        {/* MAIN PAGE CONTENT AREA */}
        <main ref={appContentRef} className="flex-1 p-4 sm:p-6 max-w-7xl w-full mx-auto space-y-6">
          {/* ==============================================================
              PAGE 1: OVERVIEW (Main Incident-Oriented Dashboard)
             ============================================================== */}
          {activeTab === 'overview' && (
            <div className="gsap-app-view space-y-6">
              {/* Section A — Page Heading */}
              <div className="flex flex-wrap items-end justify-between gap-2">
                <div>
                  <h1 className="text-xl font-semibold text-[#ECEDEA]">Overview</h1>
                  <p className="text-xs text-[#A1A5A5] mt-0.5">
                    Your services and their recent activity ({timeRange}).
                  </p>
                </div>
              </div>

              {/* Section B — Restrained Service Health Summary */}
              <div className="grid grid-cols-2 lg:grid-cols-4 border border-[#303438] bg-[#151719] rounded divide-y sm:divide-y-0 sm:divide-x divide-[#303438]">
                <div className="p-4">
                  <div className="text-[11px] font-mono uppercase text-[#747A7D]">Monitored Services</div>
                  <div
                    data-target="5"
                    className="gsap-kpi-number mt-1 text-xl font-semibold font-mono tabular-nums text-[#ECEDEA]"
                  >
                    5
                  </div>
                  <div className="mt-0.5 text-[11px] text-[#A1A5A5]">4 reporting, 1 unavailable</div>
                </div>
                <div className="p-4">
                  <div className="text-[11px] font-mono uppercase text-[#747A7D]">Healthy Services</div>
                  <div
                    data-target="2"
                    className="gsap-kpi-number mt-1 text-xl font-semibold font-mono tabular-nums text-[#8FBE9F]"
                  >
                    2
                  </div>
                  <div className="mt-0.5 text-[11px] text-[#A1A5A5]">Within nominal error bounds</div>
                </div>
                <div className="p-4">
                  <div className="text-[11px] font-mono uppercase text-[#747A7D]">Elevated Errors</div>
                  <div
                    data-target="2"
                    className="gsap-kpi-number mt-1 text-xl font-semibold font-mono tabular-nums text-[#D77F7F]"
                  >
                    2
                  </div>
                  <div className="mt-0.5 text-[11px] text-[#A1A5A5]">payment-service, checkout-gateway</div>
                </div>
                <div className="p-4">
                  <div className="text-[11px] font-mono uppercase text-[#747A7D]">Active Anomalies</div>
                  <div
                    data-target="2"
                    className="gsap-kpi-number mt-1 text-xl font-semibold font-mono tabular-nums text-[#D6AD75]"
                  >
                    2
                  </div>
                  <div className="mt-0.5 text-[11px] text-[#A1A5A5]">1 critical, 1 warning</div>
                </div>
              </div>

              {/* Section C — Active Anomalies Table */}
              <div className="border border-[#303438] bg-[#151719] rounded overflow-hidden">
                <div className="px-4 py-3 border-b border-[#303438] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-[#D6AD75]" />
                    <h2 className="text-xs font-mono uppercase tracking-wider text-[#ECEDEA]">
                      Active Anomalies Requiring Attention
                    </h2>
                  </div>
                  <span className="text-[11px] font-mono text-[#747A7D]">{timeRange}</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-[#303438] bg-[#1B1D1F] text-[11px] font-mono text-[#747A7D]">
                        <th className="py-2.5 px-4 font-medium">Severity</th>
                        <th className="py-2.5 px-4 font-medium">Service</th>
                        <th className="py-2.5 px-4 font-medium">Anomaly Description</th>
                        <th className="py-2.5 px-4 font-medium">First Observed</th>
                        <th className="py-2.5 px-4 font-medium">Relevant Change</th>
                        <th className="py-2.5 px-4 font-medium text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#303438]">
                      {ANOMALIES_DATA.map((anom) => (
                        <tr
                          key={anom.id}
                          onClick={() => navigateToAnomaly(anom.id)}
                          className="hover:bg-[#1B1D1F] cursor-pointer transition-colors"
                        >
                          <td className="py-3 px-4">
                            <StatusBadge status={anom.severity} />
                          </td>
                          <td className="py-3 px-4 font-mono text-[#ECEDEA]">{anom.service}</td>
                          <td className="py-3 px-4 text-[#ECEDEA] max-w-md">{anom.title}</td>
                          <td className="py-3 px-4 font-mono text-[11px] text-[#A1A5A5]">
                            {anom.firstObserved}
                          </td>
                          <td className="py-3 px-4 font-mono text-[11px] text-[#D6AD75]">
                            {anom.changeSummary}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <span className="inline-flex items-center gap-1 font-mono text-[11px] text-[#A6C8B5]">
                              <span>Investigate</span>
                              <ArrowRight className="w-3 h-3" />
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Section D — Service List Table */}
              <div className="border border-[#303438] bg-[#151719] rounded overflow-hidden">
                <div className="px-4 py-3 border-b border-[#303438] flex items-center justify-between">
                  <h2 className="text-xs font-mono uppercase tracking-wider text-[#ECEDEA]">
                    Monitored Services
                  </h2>
                  <span className="text-[11px] text-[#747A7D]">
                    Click a service to inspect filtered logs
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-[#303438] bg-[#1B1D1F] text-[11px] font-mono text-[#747A7D]">
                        <th className="py-2.5 px-4 font-medium">Service</th>
                        <th className="py-2.5 px-4 font-medium">Status</th>
                        <th className="py-2.5 px-4 font-medium">Log Volume</th>
                        <th className="py-2.5 px-4 font-medium">Error Rate</th>
                        <th className="py-2.5 px-4 font-medium">Baseline Comparison</th>
                        <th className="py-2.5 px-4 font-medium">Last Seen</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#303438]">
                      {SERVICES_DATA.map((svc) => (
                        <tr
                          key={svc.id}
                          onClick={() => navigateToLogsWithFilter({ service: svc.name })}
                          className="hover:bg-[#1B1D1F] cursor-pointer transition-colors"
                        >
                          <td className="py-3 px-4 font-mono font-medium text-[#ECEDEA]">
                            {svc.name}
                          </td>
                          <td className="py-3 px-4">
                            <StatusBadge status={svc.status} />
                          </td>
                          <td className="py-3 px-4 font-mono tabular-nums text-[#A1A5A5]">
                            {svc.logVolume}
                          </td>
                          <td
                            className={`py-3 px-4 font-mono tabular-nums ${
                              svc.errorRate === 'Unavailable'
                                ? 'text-[#747A7D]'
                                : parseFloat(svc.errorRate) > 1
                                ? 'text-[#D77F7F]'
                                : 'text-[#ECEDEA]'
                            }`}
                          >
                            {svc.errorRate}
                          </td>
                          <td className="py-3 px-4 font-mono tabular-nums text-[#A1A5A5]">
                            {svc.baselineDelta}
                          </td>
                          <td className="py-3 px-4 font-mono text-[#747A7D]">{svc.lastSeen}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Section E — Activity Timeline */}
              <div className="border border-[#303438] bg-[#151719] rounded p-4">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                  <div>
                    <h2 className="text-xs font-mono uppercase tracking-wider text-[#ECEDEA]">
                      Aggregate Log & Error Activity ({timeRange})
                    </h2>
                    <p className="text-[11px] text-[#747A7D]">
                      Inflection point at 01:42 UTC corresponds to anomaly anom-2026-084
                    </p>
                  </div>
                  <div className="flex items-center gap-4 text-[11px] font-mono">
                    <span className="inline-flex items-center gap-1.5 text-[#A6C8B5]">
                      <span className="w-2 h-2 bg-[#A6C8B5]" /> Total Events
                    </span>
                    <span className="inline-flex items-center gap-1.5 text-[#D77F7F]">
                      <span className="w-2 h-2 bg-[#D77F7F]" /> Error Events
                    </span>
                  </div>
                </div>
                <div className="h-48 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={TIMELINE_SERIES_DATA}>
                      <CartesianGrid stroke="#202326" strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="time" stroke="#747A7D" fontSize={11} />
                      <YAxis stroke="#747A7D" fontSize={11} width={36} />
                      <RechartsTooltip
                        contentStyle={{
                          backgroundColor: '#1B1D1F',
                          borderColor: '#303438',
                          fontSize: '12px',
                          color: '#ECEDEA'
                        }}
                      />
                      <ReferenceLine x="01:42" stroke="#D6AD75" strokeDasharray="3 3" />
                      <Area
                        type="monotone"
                        dataKey="total"
                        stroke="#A6C8B5"
                        fill="#A6C8B5"
                        fillOpacity={0.08}
                        strokeWidth={1.5}
                      />
                      <Area
                        type="monotone"
                        dataKey="errors"
                        stroke="#D77F7F"
                        fill="#D77F7F"
                        fillOpacity={0.18}
                        strokeWidth={1.5}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {/* ==============================================================
              SERVICES DIRECTORY PAGE
             ============================================================== */}
          {activeTab === 'services' && (
            <div className="gsap-app-view space-y-5">
              <div>
                <h1 className="text-xl font-semibold text-[#ECEDEA]">Services</h1>
                <p className="text-xs text-[#A1A5A5] mt-0.5">
                  Registered services emitting telemetry into {environment}.
                </p>
              </div>

              <div className="border border-[#303438] bg-[#151719] rounded overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-[#303438] bg-[#1B1D1F] text-[11px] font-mono text-[#747A7D]">
                        <th className="py-2.5 px-4 font-medium">Service Name</th>
                        <th className="py-2.5 px-4 font-medium">Health Status</th>
                        <th className="py-2.5 px-4 font-medium">Runtime</th>
                        <th className="py-2.5 px-4 font-medium">Owner</th>
                        <th className="py-2.5 px-4 font-medium">Log Volume ({timeRange})</th>
                        <th className="py-2.5 px-4 font-medium">Error Rate</th>
                        <th className="py-2.5 px-4 font-medium text-right">Inspect</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#303438]">
                      {SERVICES_DATA.map((svc) => (
                        <tr key={svc.id} className="hover:bg-[#1B1D1F]">
                          <td className="py-3 px-4 font-mono font-medium text-[#ECEDEA]">{svc.name}</td>
                          <td className="py-3 px-4">
                            <StatusBadge status={svc.status} />
                          </td>
                          <td className="py-3 px-4 font-mono text-[#A1A5A5]">{svc.runtime}</td>
                          <td className="py-3 px-4 font-mono text-[#747A7D]">{svc.owner}</td>
                          <td className="py-3 px-4 font-mono tabular-nums text-[#A1A5A5]">{svc.logVolume}</td>
                          <td className="py-3 px-4 font-mono tabular-nums text-[#ECEDEA]">{svc.errorRate}</td>
                          <td className="py-3 px-4 text-right">
                            <button
                              onClick={() => navigateToLogsWithFilter({ service: svc.name })}
                              className="px-2.5 py-1 text-[11px] font-mono bg-[#101112] hover:bg-[#202326] text-[#A6C8B5] border border-[#303438] rounded"
                            >
                              View Logs →
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ==============================================================
              PAGE 3: LOG EXPLORER (High-Density Investigation Table)
             ============================================================== */}
          {activeTab === 'explorer' && (
            <div className="gsap-app-view space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h1 className="text-xl font-semibold text-[#ECEDEA]">Log Explorer</h1>
                  <p className="text-xs text-[#A1A5A5] mt-0.5">
                    Inspect structured log events, extracted templates, and trace identifiers.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setLiveTailDemo(!liveTailDemo)}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono border rounded ${
                      liveTailDemo
                        ? 'bg-[#A6C8B5]/15 border-[#A6C8B5] text-[#A6C8B5]'
                        : 'bg-[#151719] border-[#303438] text-[#A1A5A5]'
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        liveTailDemo ? 'bg-[#A6C8B5] animate-pulse' : 'bg-[#747A7D]'
                      }`}
                    />
                    <span>{liveTailDemo ? 'Live Tail (Simulated Demo ON)' : 'Live Tail (Demo)'}</span>
                  </button>
                </div>
              </div>

              {/* Technical Query Bar */}
              <div className="border border-[#303438] bg-[#151719] rounded p-3 space-y-3">
                <div className="flex flex-col sm:flex-row gap-2">
                  <div className="flex-1 flex items-center gap-2 px-3 py-2 bg-[#101112] border border-[#303438] focus-within:border-[#A6C8B5] rounded">
                    <Terminal className="w-4 h-4 text-[#A6C8B5] shrink-0" />
                    <input
                      type="text"
                      value={explorerQuery}
                      onChange={(e) => setExplorerQuery(e.target.value)}
                      placeholder="service:payment-service severity:ERROR template:timeout"
                      className="w-full bg-transparent font-mono text-xs text-[#ECEDEA] focus:outline-none"
                    />
                  </div>
                  <button
                    onClick={() => {
                      const q = explorerQuery.toLowerCase();
                      const svcMatch = SERVICES_DATA.find((s) => q.includes(s.name));
                      setSelectedServiceFilter(svcMatch ? svcMatch.name : 'all');
                      if (q.includes('severity:error')) setSelectedSeverityFilter('ERROR');
                      else if (q.includes('severity:warn')) setSelectedSeverityFilter('WARN');
                      else if (q.includes('severity:info')) setSelectedSeverityFilter('INFO');
                      else setSelectedSeverityFilter('all');
                    }}
                    className="px-4 py-2 text-xs font-medium bg-[#A6C8B5] hover:bg-[#B9D6C6] text-[#101112] rounded shrink-0"
                  >
                    Run Query
                  </button>
                </div>

                {/* Structured Filter Bar */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 text-xs">
                  <select
                    value={selectedServiceFilter}
                    onChange={(e) => setSelectedServiceFilter(e.target.value)}
                    className="px-2.5 py-1.5 bg-[#101112] border border-[#303438] rounded text-[#ECEDEA]"
                  >
                    <option value="all">Service: All</option>
                    {SERVICES_DATA.map((s) => (
                      <option key={s.id} value={s.name}>
                        {s.name}
                      </option>
                    ))}
                  </select>

                  <select
                    value={selectedSeverityFilter}
                    onChange={(e) => setSelectedSeverityFilter(e.target.value)}
                    className="px-2.5 py-1.5 bg-[#101112] border border-[#303438] rounded text-[#ECEDEA]"
                  >
                    <option value="all">Severity: All</option>
                    <option value="ERROR">ERROR</option>
                    <option value="WARN">WARN</option>
                    <option value="INFO">INFO</option>
                  </select>

                  <select
                    value={selectedTemplateFilter}
                    onChange={(e) => setSelectedTemplateFilter(e.target.value)}
                    className="px-2.5 py-1.5 bg-[#101112] border border-[#303438] rounded text-[#ECEDEA]"
                  >
                    <option value="all">Template: All</option>
                    {TEMPLATES_DATA.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.id} ({t.service})
                      </option>
                    ))}
                  </select>

                  <input
                    type="text"
                    value={selectedTraceFilter}
                    onChange={(e) => setSelectedTraceFilter(e.target.value)}
                    placeholder="Trace or Request ID..."
                    className="px-2.5 py-1.5 font-mono bg-[#101112] border border-[#303438] rounded text-[#ECEDEA] focus:outline-none focus:border-[#A6C8B5]"
                  />

                  <div className="flex gap-1.5">
                    <input
                      type="text"
                      value={explorerSearchInput}
                      onChange={(e) => setExplorerSearchInput(e.target.value)}
                      placeholder="Filter message text..."
                      className="flex-1 min-w-0 px-2.5 py-1.5 bg-[#101112] border border-[#303438] rounded text-[#ECEDEA] focus:outline-none focus:border-[#A6C8B5]"
                    />
                    <button
                      onClick={() => {
                        setSelectedServiceFilter('all');
                        setSelectedSeverityFilter('all');
                        setSelectedTemplateFilter('all');
                        setSelectedTraceFilter('');
                        setExplorerSearchInput('');
                        setExplorerQuery('*');
                      }}
                      className="px-2.5 py-1.5 text-[#A1A5A5] hover:text-[#ECEDEA] bg-[#101112] border border-[#303438] rounded"
                      title="Clear filters"
                    >
                      Clear
                    </button>
                  </div>
                </div>
              </div>

              {/* High-Density Log Results Table */}
              <div className="border border-[#303438] bg-[#151719] rounded overflow-hidden">
                <div className="px-4 py-2 border-b border-[#303438] bg-[#1B1D1F] flex items-center justify-between text-[11px] font-mono text-[#747A7D]">
                  <span>
                    Showing {filteredLogs.length} matching events ({timeRange})
                  </span>
                  <span>Click any row to expand normalized template & attributes</span>
                </div>

                {filteredLogs.length === 0 ? (
                  <div className="p-10 text-center space-y-2">
                    <div className="text-sm font-medium text-[#ECEDEA]">No matching log events</div>
                    <p className="text-xs text-[#747A7D]">
                      Adjust service, severity, or trace ID filters to broaden your query.
                    </p>
                  </div>
                ) : (
                  <div className="divide-y divide-[#303438]">
                    {filteredLogs.map((log) => {
                      const isExpanded = expandedLogId === log.id;
                      return (
                        <div key={log.id} className="bg-[#151719]">
                          {/* Compact Log Row */}
                          <div
                            onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                            className={`px-4 py-2.5 flex flex-wrap md:flex-nowrap items-center gap-3 cursor-pointer hover:bg-[#1B1D1F] transition-colors font-mono text-xs ${
                              isExpanded ? 'bg-[#1B1D1F]' : ''
                            }`}
                          >
                            <span className="text-[#747A7D] shrink-0">
                              {isExpanded ? (
                                <ChevronDown className="w-3.5 h-3.5 inline" />
                              ) : (
                                <ChevronRight className="w-3.5 h-3.5 inline" />
                              )}
                            </span>
                            <span className="text-[11px] text-[#A1A5A5] shrink-0">
                              {log.timestamp.replace('T', ' ').replace('Z', '')}
                            </span>
                            <SeverityBadge severity={log.severity} />
                            <span className="text-[#A6C8B5] shrink-0">{log.service}</span>
                            <span className="text-[#ECEDEA] truncate flex-1">{log.message}</span>
                            <span className="text-[11px] text-[#747A7D] shrink-0">{log.traceId}</span>
                          </div>

                          {/* Expandable Structured Log Inspector Drawer */}
                          {isExpanded && (
                            <div className="px-6 py-4 bg-[#101112] border-t border-[#303438] space-y-4 text-xs">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
                                  <span className="px-2 py-0.5 bg-[#151719] border border-[#303438] rounded text-[#A1A5A5]">
                                    Trace: <strong className="text-[#ECEDEA]">{log.traceId}</strong>
                                  </span>
                                  <span className="px-2 py-0.5 bg-[#151719] border border-[#303438] rounded text-[#A1A5A5]">
                                    Request: <strong className="text-[#ECEDEA]">{log.requestId}</strong>
                                  </span>
                                  <span className="px-2 py-0.5 bg-[#151719] border border-[#303438] rounded text-[#A1A5A5]">
                                    Source: <strong className="text-[#ECEDEA]">{log.source}</strong>
                                  </span>
                                </div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <button
                                    onClick={() => setSelectedTraceFilter(log.traceId)}
                                    className="px-2.5 py-1 text-[11px] font-mono bg-[#151719] hover:bg-[#202326] text-[#A6C8B5] border border-[#303438] rounded"
                                  >
                                    Filter by Trace ID
                                  </button>
                                  <CopyButton text={log.traceId} label="Copy Trace" />
                                  <CopyButton text={log.message} label="Copy Raw" />
                                </div>
                              </div>

                              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                  <div>
                                    <div className="text-[10px] font-mono uppercase text-[#747A7D]">
                                      Complete Raw Message
                                    </div>
                                    <div className="mt-1 p-2.5 bg-[#151719] border border-[#303438] rounded font-mono text-[11px] text-[#ECEDEA] break-all">
                                      {log.message}
                                    </div>
                                  </div>
                                  <div>
                                    <div className="text-[10px] font-mono uppercase text-[#747A7D]">
                                      Normalized Log Template ({log.templateId})
                                    </div>
                                    <div className="mt-1 p-2.5 bg-[#151719] border border-[#303438] rounded font-mono text-[11px] text-[#A6C8B5] break-all">
                                      {log.template}
                                    </div>
                                  </div>
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                  <div>
                                    <div className="text-[10px] font-mono uppercase text-[#747A7D]">
                                      Extracted Parameters
                                    </div>
                                    <pre className="mt-1 p-2.5 bg-[#151719] border border-[#303438] rounded font-mono text-[11px] text-[#ECEDEA] overflow-x-auto">
                                      {JSON.stringify(log.parameters, null, 2)}
                                    </pre>
                                  </div>
                                  <div>
                                    <div className="text-[10px] font-mono uppercase text-[#747A7D]">
                                      Structured Attributes
                                    </div>
                                    <pre className="mt-1 p-2.5 bg-[#151719] border border-[#303438] rounded font-mono text-[11px] text-[#A1A5A5] overflow-x-auto">
                                      {JSON.stringify(log.attributes, null, 2)}
                                    </pre>
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ==============================================================
              PAGE 4: ANOMALY INVESTIGATION (Core Differentiating Workflow)
             ============================================================== */}
          {activeTab === 'anomaly' && (
            <div className="gsap-app-view space-y-6">
              {/* Anomaly Switcher Strip */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#303438] pb-4">
                <div className="flex flex-wrap items-center gap-2">
                  {ANOMALIES_DATA.map((a) => (
                    <button
                      key={a.id}
                      onClick={() => setSelectedAnomalyId(a.id)}
                      className={`px-3 py-1.5 text-xs font-mono border rounded transition-colors ${
                        selectedAnomalyId === a.id
                          ? 'bg-[#A6C8B5]/12 border-[#A6C8B5] text-[#ECEDEA]'
                          : 'bg-[#151719] border-[#303438] text-[#A1A5A5] hover:text-[#ECEDEA]'
                      }`}
                    >
                      {a.id} • {a.service}
                    </button>
                  ))}
                </div>

                {/* Investigation Status Control */}
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-mono text-[#747A7D]">Status:</span>
                  <select
                    value={anomalyStatuses[activeAnomaly.id] || activeAnomaly.status}
                    onChange={(e) =>
                      setAnomalyStatuses((prev) => ({
                        ...prev,
                        [activeAnomaly.id]: e.target.value
                      }))
                    }
                    className="px-2.5 py-1 font-mono bg-[#151719] border border-[#303438] rounded text-[#ECEDEA]"
                  >
                    <option value="open">Open</option>
                    <option value="investigating">Investigating</option>
                    <option value="resolved">Resolved</option>
                  </select>
                </div>
              </div>

              {/* Header */}
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2.5">
                  <StatusBadge status={activeAnomaly.severity} />
                  <span className="font-mono text-xs text-[#A6C8B5]">{activeAnomaly.service}</span>
                  <span className="text-[#303438]">•</span>
                  <span className="font-mono text-xs text-[#747A7D]">
                    First observed: {activeAnomaly.firstObserved}
                  </span>
                </div>
                <h1 className="text-xl font-semibold text-[#ECEDEA]">{activeAnomaly.title}</h1>
              </div>

              {/* Section A — Evidence-Based Incident Summary */}
              <div className="p-4 border border-[#303438] bg-[#151719] rounded space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-[#A6C8B5]">
                    Observed Behavioral Change Summary
                  </span>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() =>
                        navigateToLogsWithFilter({
                          service: activeAnomaly.service,
                          severity: 'ERROR'
                        })
                      }
                      className="px-2.5 py-1 text-xs font-medium bg-[#A6C8B5] hover:bg-[#B9D6C6] text-[#101112] rounded"
                    >
                      Open Related Logs →
                    </button>
                  </div>
                </div>
                <p className="text-xs text-[#ECEDEA] leading-relaxed">{activeAnomaly.summary}</p>
              </div>

              {/* Section B — Inflection Timeline */}
              <div className="p-4 border border-[#303438] bg-[#151719] rounded">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-mono uppercase tracking-wider text-[#ECEDEA]">
                    Event & Error Volume Around Anomaly Onset
                  </span>
                  <span className="text-[11px] font-mono text-[#D6AD75]">
                    Marker: Anomaly Start (01:42 UTC)
                  </span>
                </div>
                <div className="h-44 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={TIMELINE_SERIES_DATA}>
                      <CartesianGrid stroke="#202326" strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="time" stroke="#747A7D" fontSize={11} />
                      <YAxis stroke="#747A7D" fontSize={11} width={36} />
                      <RechartsTooltip
                        contentStyle={{
                          backgroundColor: '#1B1D1F',
                          borderColor: '#303438',
                          fontSize: '12px'
                        }}
                      />
                      <ReferenceLine
                        x="01:42"
                        stroke="#D6AD75"
                        strokeWidth={1.5}
                        label={{ value: 'Start', fill: '#D6AD75', fontSize: 10 }}
                      />
                      <Area
                        type="monotone"
                        dataKey="total"
                        stroke="#A6C8B5"
                        fill="#A6C8B5"
                        fillOpacity={0.07}
                        strokeWidth={1.5}
                      />
                      <Area
                        type="monotone"
                        dataKey="errors"
                        stroke="#D77F7F"
                        fill="#D77F7F"
                        fillOpacity={0.22}
                        strokeWidth={1.5}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Section C — Changed & Newly Observed Templates */}
              <div className="border border-[#303438] bg-[#151719] rounded overflow-hidden">
                <div className="px-4 py-3 border-b border-[#303438]">
                  <h2 className="text-xs font-mono uppercase tracking-wider text-[#ECEDEA]">
                    Changed & Newly Observed Log Templates
                  </h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-[#303438] bg-[#1B1D1F] text-[11px] font-mono text-[#747A7D]">
                        <th className="py-2.5 px-4 font-medium">Classification</th>
                        <th className="py-2.5 px-4 font-medium">Template Signature</th>
                        <th className="py-2.5 px-4 font-medium">Baseline</th>
                        <th className="py-2.5 px-4 font-medium">Current</th>
                        <th className="py-2.5 px-4 font-medium">Delta</th>
                        <th className="py-2.5 px-4 font-medium text-right">Inspect</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#303438]">
                      {activeAnomaly.changedTemplates.map((tpl) => (
                        <tr key={tpl.id} className="hover:bg-[#1B1D1F]">
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-0.5 text-[11px] font-mono border rounded ${
                                tpl.type === 'Newly Observed'
                                  ? 'text-[#D6AD75] bg-[#D6AD75]/10 border-[#D6AD75]/30'
                                  : tpl.type === 'Increased Frequency'
                                  ? 'text-[#D77F7F] bg-[#D77F7F]/10 border-[#D77F7F]/30'
                                  : 'text-[#91AFC7] bg-[#91AFC7]/10 border-[#91AFC7]/30'
                              }`}
                            >
                              {tpl.type}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-mono text-[11px] text-[#ECEDEA]">
                            {tpl.template}
                          </td>
                          <td className="py-3 px-4 font-mono text-[#747A7D]">{tpl.prevFreq}</td>
                          <td className="py-3 px-4 font-mono text-[#ECEDEA]">{tpl.currFreq}</td>
                          <td className="py-3 px-4 font-mono text-[#D77F7F]">{tpl.changePct}</td>
                          <td className="py-3 px-4 text-right">
                            <button
                              onClick={() =>
                                navigateToLogsWithFilter({
                                  service: activeAnomaly.service,
                                  templateId: tpl.id
                                })
                              }
                              className="text-[11px] font-mono text-[#A6C8B5] hover:underline"
                            >
                              Logs →
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Section D & E — Correlated Identifiers & Sample Events */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-4 border border-[#303438] bg-[#151719] rounded p-4 space-y-4">
                  <div className="text-xs font-mono uppercase tracking-wider text-[#ECEDEA]">
                    Correlated Identifiers
                  </div>
                  <div>
                    <div className="text-[10px] font-mono uppercase text-[#747A7D] mb-2">
                      Shared Trace IDs
                    </div>
                    <div className="space-y-1.5">
                      {activeAnomaly.correlatedTraceIds.map((tid) => (
                        <div
                          key={tid}
                          className="flex items-center justify-between px-2.5 py-1.5 bg-[#101112] border border-[#303438] rounded font-mono text-xs"
                        >
                          <button
                            onClick={() => navigateToLogsWithFilter({ traceId: tid })}
                            className="text-[#A6C8B5] hover:underline"
                          >
                            {tid}
                          </button>
                          <CopyButton text={tid} label="Copy" />
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] font-mono uppercase text-[#747A7D] mb-2">
                      Shared Request IDs
                    </div>
                    <div className="space-y-1.5">
                      {activeAnomaly.correlatedRequestIds.map((rid) => (
                        <div
                          key={rid}
                          className="flex items-center justify-between px-2.5 py-1.5 bg-[#101112] border border-[#303438] rounded font-mono text-xs"
                        >
                          <button
                            onClick={() => navigateToLogsWithFilter({ traceId: rid })}
                            className="text-[#ECEDEA] hover:text-[#A6C8B5]"
                          >
                            {rid}
                          </button>
                          <CopyButton text={rid} label="Copy" />
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="lg:col-span-8 border border-[#303438] bg-[#151719] rounded overflow-hidden">
                  <div className="px-4 py-3 border-b border-[#303438] text-xs font-mono uppercase tracking-wider text-[#ECEDEA]">
                    Sample Correlated Log Events
                  </div>
                  <div className="divide-y divide-[#303438] font-mono text-xs">
                    {LOG_ENTRIES_DATA.filter((l) => l.service === activeAnomaly.service)
                      .slice(0, 4)
                      .map((sample) => (
                        <div key={sample.id} className="p-3.5 space-y-1.5 hover:bg-[#1B1D1F]">
                          <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
                            <div className="flex items-center gap-2">
                              <SeverityBadge severity={sample.severity} />
                              <span className="text-[#747A7D]">{sample.timestamp}</span>
                            </div>
                            <button
                              onClick={() => navigateToLogsWithFilter({ traceId: sample.traceId })}
                              className="text-[#A6C8B5] hover:underline"
                            >
                              {sample.traceId} →
                            </button>
                          </div>
                          <div className="text-[#ECEDEA] break-all">{sample.message}</div>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ==============================================================
              PAGE 5: TEMPLATE EXPLORER
             ============================================================== */}
          {activeTab === 'templates' && (
            <div className="gsap-app-view space-y-6">
              <div>
                <h1 className="text-xl font-semibold text-[#ECEDEA]">Template Explorer</h1>
                <p className="text-xs text-[#A1A5A5] mt-0.5">
                  Normalized log patterns extracted across monitored services ({timeRange}).
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left Template Table */}
                <div className="lg:col-span-7 border border-[#303438] bg-[#151719] rounded overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-[#303438] bg-[#1B1D1F] text-[11px] font-mono text-[#747A7D]">
                          <th className="py-2.5 px-4 font-medium">Classification</th>
                          <th className="py-2.5 px-4 font-medium">Template</th>
                          <th className="py-2.5 px-4 font-medium">Rate</th>
                          <th className="py-2.5 px-4 font-medium">Trend</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#303438]">
                        {TEMPLATES_DATA.map((tpl) => {
                          const selected = tpl.id === activeTemplate.id;
                          return (
                            <tr
                              key={tpl.id}
                              onClick={() => setSelectedTemplateId(tpl.id)}
                              className={`cursor-pointer transition-colors ${
                                selected ? 'bg-[#A6C8B5]/10' : 'hover:bg-[#1B1D1F]'
                              }`}
                            >
                              <td className="py-3 px-4">
                                <span
                                  className={`px-2 py-0.5 text-[10px] font-mono border rounded ${
                                    tpl.tag === 'New'
                                      ? 'text-[#D6AD75] bg-[#D6AD75]/10 border-[#D6AD75]/30'
                                      : tpl.tag === 'Rising'
                                      ? 'text-[#D77F7F] bg-[#D77F7F]/10 border-[#D77F7F]/30'
                                      : 'text-[#A1A5A5] bg-[#202326] border-[#303438]'
                                  }`}
                                >
                                  {tpl.tag}
                                </span>
                              </td>
                              <td className="py-3 px-4">
                                <div className="font-mono text-[11px] text-[#ECEDEA] line-clamp-2">
                                  {tpl.template}
                                </div>
                                <div className="font-mono text-[10px] text-[#747A7D] mt-0.5">
                                  {tpl.service}
                                </div>
                              </td>
                              <td className="py-3 px-4 font-mono tabular-nums text-[#ECEDEA] shrink-0">
                                {tpl.frequency}
                              </td>
                              <td className="py-3 px-4">
                                <MiniSparkline
                                  values={tpl.sparkline}
                                  color={tpl.tag === 'Frequent' ? '#A6C8B5' : '#D77F7F'}
                                />
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Right Template Inspector */}
                <div className="lg:col-span-5 border border-[#303438] bg-[#151719] rounded p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono uppercase text-[#747A7D]">
                      Template Details • {activeTemplate.id}
                    </span>
                    <button
                      onClick={() =>
                        navigateToLogsWithFilter({
                          service: activeTemplate.service,
                          templateId: activeTemplate.id
                        })
                      }
                      className="text-xs font-mono text-[#A6C8B5] hover:underline"
                    >
                      Open Matching Logs →
                    </button>
                  </div>

                  <div className="p-3 bg-[#101112] border border-[#303438] rounded font-mono text-xs text-[#ECEDEA] break-all">
                    {activeTemplate.template}
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="text-[10px] font-mono uppercase text-[#747A7D] block">Service</span>
                      <span className="font-mono text-[#A6C8B5]">{activeTemplate.service}</span>
                    </div>
                    <div>
                      <span className="text-[10px] font-mono uppercase text-[#747A7D] block">Delta</span>
                      <span className="font-mono text-[#ECEDEA]">{activeTemplate.trend}</span>
                    </div>
                    <div>
                      <span className="text-[10px] font-mono uppercase text-[#747A7D] block">First Seen</span>
                      <span className="font-mono text-[#A1A5A5]">{activeTemplate.firstSeen}</span>
                    </div>
                    <div>
                      <span className="text-[10px] font-mono uppercase text-[#747A7D] block">Last Seen</span>
                      <span className="font-mono text-[#A1A5A5]">{activeTemplate.lastSeen}</span>
                    </div>
                  </div>

                  <div>
                    <div className="text-[10px] font-mono uppercase text-[#747A7D] mb-1.5">
                      Extracted Parameter Slots
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {activeTemplate.parameters.map((p) => (
                        <span
                          key={p}
                          className="px-2 py-0.5 text-[11px] font-mono bg-[#101112] border border-[#303438] rounded text-[#A1A5A5]"
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <div className="text-[10px] font-mono uppercase text-[#747A7D] mb-1.5">
                      Example Log Instances
                    </div>
                    <div className="space-y-1.5">
                      {activeTemplate.examples.map((ex, i) => (
                        <div
                          key={i}
                          className="p-2.5 bg-[#101112] border border-[#303438] rounded font-mono text-[11px] text-[#A1A5A5] break-all"
                        >
                          {ex}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ==============================================================
              PAGE 6: PLATFORM HEALTH (LOGIQ Self-Observability)
             ============================================================== */}
          {activeTab === 'health' && (
            <div className="gsap-app-view space-y-6">
              <div className="p-4 border border-dashed border-[#D6AD75]/50 bg-[#151719] rounded flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-wider text-[#D6AD75]">
                    Domain B — Internal Infrastructure Telemetry
                  </div>
                  <h1 className="text-lg font-semibold text-[#ECEDEA] mt-0.5">
                    LOGIQ Platform Health
                  </h1>
                  <p className="text-xs text-[#A1A5A5]">
                    Monitors LOGIQ’s own API workers, Kafka streams, PostgreSQL, MinIO, and Redis—distinct from monitored application logs.
                  </p>
                </div>
                <StatusBadge status="Active" />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {PLATFORM_HEALTH_COMPONENTS.map((comp) => (
                  <div
                    key={comp.name}
                    className="p-4 border border-[#303438] bg-[#151719] rounded flex flex-col justify-between space-y-3"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="text-[10px] font-mono uppercase text-[#747A7D]">
                            {comp.category}
                          </div>
                          <h3 className="text-sm font-semibold text-[#ECEDEA] mt-0.5">{comp.name}</h3>
                        </div>
                        <StatusBadge status={comp.status} />
                      </div>
                      <p className="mt-2 text-xs text-[#A1A5A5] leading-relaxed">{comp.detail}</p>
                    </div>
                    <div className="pt-2.5 border-t border-[#303438] flex items-center justify-between font-mono text-[11px] text-[#747A7D]">
                      <span>Heartbeat: {comp.heartbeat}</span>
                      <span>{comp.recentFailures}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ==============================================================
              PAGE 7A: DATASETS MANAGEMENT
             ============================================================== */}
          {activeTab === 'datasets' && (
            <div className="gsap-app-view space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h1 className="text-xl font-semibold text-[#ECEDEA]">Datasets</h1>
                  <p className="text-xs text-[#A1A5A5] mt-0.5">
                    Upload static log archives into MinIO for asynchronous parsing and template extraction.
                  </p>
                </div>
              </div>

              {/* Drag-and-Drop / File Selection Upload Zone */}
              <div className="p-6 border border-dashed border-[#303438] hover:border-[#A6C8B5] bg-[#151719] rounded text-center space-y-3 transition-colors">
                <Upload className="w-6 h-6 text-[#A6C8B5] mx-auto" />
                <div>
                  <div className="text-sm font-medium text-[#ECEDEA]">
                    Upload Log Dataset Archive
                  </div>
                  <p className="text-xs text-[#747A7D] mt-1">
                    Configurable formats (illustrative: .jsonl, .log, .txt). Files are stored in MinIO and queued via Kafka.
                  </p>
                </div>
                <div className="flex justify-center gap-2">
                  <button
                    onClick={() => handleSimulatedUpload('service-incident-replay.jsonl')}
                    disabled={uploadingDataset}
                    className="px-4 py-2 text-xs font-medium bg-[#A6C8B5] hover:bg-[#B9D6C6] text-[#101112] rounded disabled:opacity-50"
                  >
                    {uploadingDataset ? 'Uploading & Queuing...' : 'Simulate Dataset Upload'}
                  </button>
                </div>
              </div>

              {/* Datasets Table */}
              <div className="border border-[#303438] bg-[#151719] rounded overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-[#303438] bg-[#1B1D1F] text-[11px] font-mono text-[#747A7D]">
                        <th className="py-2.5 px-4 font-medium">Dataset Name</th>
                        <th className="py-2.5 px-4 font-medium">Source Type</th>
                        <th className="py-2.5 px-4 font-medium">Upload</th>
                        <th className="py-2.5 px-4 font-medium">Processing</th>
                        <th className="py-2.5 px-4 font-medium">Records</th>
                        <th className="py-2.5 px-4 font-medium">Created</th>
                        <th className="py-2.5 px-4 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#303438]">
                      {datasets.map((ds) => (
                        <tr key={ds.id} className="hover:bg-[#1B1D1F]">
                          <td className="py-3 px-4 font-mono text-[#ECEDEA]">{ds.name}</td>
                          <td className="py-3 px-4 text-[#A1A5A5]">{ds.sourceType}</td>
                          <td className="py-3 px-4">
                            <StatusBadge status={ds.uploadStatus} />
                          </td>
                          <td className="py-3 px-4">
                            <StatusBadge status={ds.processingStatus} />
                          </td>
                          <td className="py-3 px-4 font-mono tabular-nums text-[#A1A5A5]">
                            {ds.recordCount}
                          </td>
                          <td className="py-3 px-4 font-mono text-[#747A7D]">{ds.createdAt}</td>
                          <td className="py-3 px-4 text-right space-x-2">
                            {ds.processingStatus === 'Failed' && (
                              <button
                                onClick={() =>
                                  setDatasets((prev) =>
                                    prev.map((item) =>
                                      item.id === ds.id
                                        ? { ...item, processingStatus: 'Ready', recordCount: '1,401' }
                                        : item
                                    )
                                  )
                                }
                                className="px-2 py-1 text-[11px] font-mono bg-[#101112] border border-[#303438] text-[#D6AD75] rounded"
                              >
                                Retry
                              </button>
                            )}
                            <button
                              onClick={() =>
                                setSelectedDatasetId(selectedDatasetId === ds.id ? null : ds.id)
                              }
                              className="px-2 py-1 text-[11px] font-mono bg-[#101112] border border-[#303438] text-[#A6C8B5] rounded"
                            >
                              Details
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {selectedDatasetId && (
                  <div className="p-4 border-t border-[#303438] bg-[#101112] text-xs space-y-2">
                    {(() => {
                      const ds = datasets.find((d) => d.id === selectedDatasetId);
                      if (!ds) return null;
                      return (
                        <>
                          <div className="flex items-center justify-between">
                            <span className="font-mono font-semibold text-[#ECEDEA]">
                              Dataset Metadata: {ds.name}
                            </span>
                            <button
                              onClick={() => setSelectedDatasetId(null)}
                              className="text-[#747A7D] hover:text-[#ECEDEA]"
                            >
                              Close
                            </button>
                          </div>
                          <div className="font-mono text-[11px] text-[#A1A5A5]">
                            ID: {ds.id} • Size: {ds.size} • Object Store: MinIO (logiq-datasets)
                          </div>
                          {ds.errorDetail && (
                            <div className="p-2.5 bg-[#D77F7F]/10 border border-[#D77F7F]/30 rounded font-mono text-[11px] text-[#D77F7F]">
                              {ds.errorDetail}
                            </div>
                          )}
                        </>
                      );
                    })()}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ==============================================================
              PAGE 7B: SOURCES MANAGEMENT
             ============================================================== */}
          {activeTab === 'sources' && (
            <div className="gsap-app-view space-y-6">
              <div>
                <h1 className="text-xl font-semibold text-[#ECEDEA]">Log Sources</h1>
                <p className="text-xs text-[#A1A5A5] mt-0.5">
                  Configured collectors and ingestion agents forwarding telemetry to LOGIQ.
                </p>
              </div>

              <div className="border border-[#303438] bg-[#151719] rounded overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-[#303438] bg-[#1B1D1F] text-[11px] font-mono text-[#747A7D]">
                        <th className="py-2.5 px-4 font-medium">Source Name</th>
                        <th className="py-2.5 px-4 font-medium">Collector Type</th>
                        <th className="py-2.5 px-4 font-medium">Status</th>
                        <th className="py-2.5 px-4 font-medium">Configuration Summary</th>
                        <th className="py-2.5 px-4 font-medium">Last Activity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#303438]">
                      {SOURCES_DATA.map((src) => (
                        <tr key={src.id} className="hover:bg-[#1B1D1F]">
                          <td className="py-3 px-4 font-mono font-medium text-[#ECEDEA]">{src.name}</td>
                          <td className="py-3 px-4 text-[#A1A5A5]">{src.type}</td>
                          <td className="py-3 px-4">
                            <StatusBadge status={src.status} />
                          </td>
                          <td className="py-3 px-4 font-mono text-[11px] text-[#A1A5A5]">
                            {src.configSummary}
                          </td>
                          <td className="py-3 px-4 font-mono text-[#747A7D]">{src.lastActivity}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ==============================================================
              PAGE 8: SETTINGS
             ============================================================== */}
          {activeTab === 'settings' && (
            <div className="gsap-app-view space-y-6 max-w-4xl">
              <div>
                <h1 className="text-xl font-semibold text-[#ECEDEA]">Settings</h1>
                <p className="text-xs text-[#A1A5A5] mt-0.5">
                  Workspace preferences, environment configuration, and ingestion key placeholders.
                </p>
              </div>

              <div className="p-5 border border-[#303438] bg-[#151719] rounded space-y-4">
                <div className="text-xs font-mono uppercase tracking-wider text-[#ECEDEA]">
                  Environment Configuration
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div>
                    <label className="block text-[11px] font-mono text-[#747A7D] mb-1">
                      Active Environment
                    </label>
                    <input
                      type="text"
                      readOnly
                      value={environment}
                      className="w-full px-3 py-2 font-mono bg-[#101112] border border-[#303438] rounded text-[#ECEDEA]"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-mono text-[#747A7D] mb-1">
                      Default Query Window
                    </label>
                    <input
                      type="text"
                      readOnly
                      value={timeRange}
                      className="w-full px-3 py-2 font-mono bg-[#101112] border border-[#303438] rounded text-[#ECEDEA]"
                    />
                  </div>
                </div>
              </div>

              <div className="p-5 border border-[#303438] bg-[#151719] rounded space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs font-mono uppercase tracking-wider text-[#ECEDEA]">
                      Ingestion Credentials (Illustrative UI Placeholder)
                    </div>
                    <p className="text-[11px] text-[#747A7D] mt-0.5">
                      Masked credential tokens shown for interface demonstration; connect backend auth provider to issue live keys.
                    </p>
                  </div>
                </div>
                <div className="p-3 bg-[#101112] border border-[#303438] rounded flex flex-wrap items-center justify-between gap-2 font-mono text-xs">
                  <div>
                    <span className="text-[#ECEDEA]">eu-west-1-collector-key</span>
                    <span className="ml-3 text-[#747A7D]">lgq_live_••••••••••••••••8f92</span>
                  </div>
                  <span className="text-[10px] text-[#747A7D]">Placeholder Credential</span>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

/**
 * ============================================================================
 * ERROR BOUNDARY & ROOT APPLICATION SHELL
 * ============================================================================
 */
class LogiqErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, errorMessage: error?.message || 'Unexpected rendering error' };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#101112] text-[#ECEDEA] flex items-center justify-center p-6">
          <div className="max-w-md w-full border border-[#303438] bg-[#151719] rounded p-6 space-y-3">
            <div className="text-xs font-mono uppercase text-[#D77F7F]">LOGIQ Runtime Recovery</div>
            <h2 className="text-base font-semibold">Interface encountered an error</h2>
            <p className="text-xs text-[#A1A5A5] font-mono break-all">{this.state.errorMessage}</p>
            <button
              onClick={() => this.setState({ hasError: false, errorMessage: '' })}
              className="px-3 py-1.5 text-xs font-medium bg-[#A6C8B5] text-[#101112] rounded"
            >
              Reload View
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  // 'website' | 'docs' | 'app'
  const [surface, setSurface] = useState('website');
  const [websiteSubPage, setWebsiteSubPage] = useState('landing'); // 'landing' | 'architecture'
  const [activeDocId, setActiveDocId] = useState('intro');
  const [appInitialTab, setAppInitialTab] = useState('overview');
  const gsapReady = useGsapEngine();

  const handleOpenPlatform = (tab = 'overview') => {
    setAppInitialTab(tab);
    setSurface('app');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleOpenDocs = (docId = 'intro') => {
    setActiveDocId(docId);
    setSurface('docs');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleBackToWebsite = () => {
    setSurface('website');
    setWebsiteSubPage('landing');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <LogiqErrorBoundary>
      {surface === 'app' ? (
        <LogiqSession>
          <LogiqApplication
            initialTab={appInitialTab}
            gsapReady={gsapReady}
            onBackToWebsite={handleBackToWebsite}
            onOpenDocs={handleOpenDocs}
          />
        </LogiqSession>
      ) : surface === 'docs' ? (
        <DocumentationView
          activeDocId={activeDocId}
          setActiveDocId={setActiveDocId}
          onBackToWebsite={handleBackToWebsite}
          onOpenPlatform={handleOpenPlatform}
        />
      ) : (
        <PublicWebsite
          subPage={websiteSubPage}
          setSubPage={setWebsiteSubPage}
          gsapReady={gsapReady}
          onOpenPlatform={handleOpenPlatform}
          onOpenDocs={handleOpenDocs}
        />
      )}
    </LogiqErrorBoundary>
  );
}