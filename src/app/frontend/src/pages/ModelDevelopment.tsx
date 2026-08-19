import { useEffect, useState } from 'react';
import {
  Code, ExternalLink, FlaskConical, ChevronDown, Library, Clock,
  FlaskRound, ShieldCheck, GitCompare,
} from 'lucide-react';
import { api } from '../lib/api';
import ReviewPromote from './ReviewPromote';
import CompareTest from './CompareTest';
import {
  Page, PageHeader, OnThisPage, Card, CardTitle, Section, Metric, Pill,
  AgentLead, UnderTheHood, Loading, Grid, SectionHead,
} from '../components/ui';

const GITHUB_REPO_URL = 'https://github.com/wryszka/pricing-workbench';

type Tab = 'train' | 'compare' | 'review';

export default function ModelDevelopment() {
  const [tab, setTab] = useState<Tab>('train');

  return (
    <Page>
      <PageHeader
        eyebrow="Bricksurance SE · Model Development"
        title="Train, Compare & Promote"
        subtitle="Where actuaries and data scientists build, test, and promote pricing models."
        icon={Code}
      />

      <AgentLead
        persona="model_review"
        title="Model Validation"
        subtitle="An independent validation read of the current champion models."
        seed="Give me a validation read on the current champion models — calibration, stability across the rolling releases, and any concerns."
        examples={[
          'Is the frequency model well-calibrated?',
          'How stable is gini across releases?',
          'Any fairness concerns?',
        ]}
      />

      <OnThisPage>
        Three stages: Train (run notebooks, track experiments in MLflow), Compare & Test (validate models, run benchmarks), and Promote (move champions into the live rate book). All runs are versioned in Unity Catalog.
      </OnThisPage>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-line mb-5">
        <TabButton active={tab === 'train'}   onClick={() => setTab('train')}
                   icon={<FlaskRound className="w-4 h-4" />} label="Train" />
        <TabButton active={tab === 'compare'} onClick={() => setTab('compare')}
                   icon={<GitCompare className="w-4 h-4" />} label="Compare & Test" />
        <TabButton active={tab === 'review'}  onClick={() => setTab('review')}
                   icon={<ShieldCheck className="w-4 h-4" />} label="Promote" />
      </div>

      {tab === 'train'   && <TrainTab />}
      {tab === 'compare' && <CompareTest />}
      {tab === 'review'  && <ReviewPromote />}

      <UnderTheHood
        lines={[
          { component: 'MLflow experiment tracking', detail: 'All training runs logged with governance tags; experiments auto-created from workspace notebooks.' },
          { component: 'Unity Catalog Model Registry', detail: 'Models versioned and governed; champions aliased for serving.' },
          { component: 'Databricks Serverless ML', detail: 'Training compute auto-scales to zero; isolated notebook environments.' },
          { component: 'Model Factory', detail: 'Automated retraining & promotion pipeline on schedule or on-demand.' },
        ]}
      />
    </Page>
  );
}

function TabButton({ active, onClick, icon, label }:
  { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button onClick={onClick}
            className={`px-4 py-2.5 text-sm font-medium inline-flex items-center gap-2 border-b-2 transition-colors ${
              active
                ? 'border-brand text-brand'
                : 'border-transparent text-mut hover:text-ink hover:border-line'
            }`}>
      {icon} {label}
    </button>
  );
}

// ===========================================================================
// Train tab — the original Model Development content, unchanged.
// ===========================================================================

function TrainTab() {
  const [notebooks,   setNotebooks]  = useState<any[]>([]);
  const [libraries,   setLibraries]  = useState<any[]>([]);
  const [recentRuns,  setRecentRuns] = useState<any[]>([]);
  const [config,      setConfig]     = useState<any>(null);
  const [opening,     setOpening]    = useState<string | null>(null);
  const [showLibs,    setShowLibs]   = useState(false);
  const [showLibrary, setShowLibrary]= useState(false);

  useEffect(() => {
    api.getDevelopmentNotebooks().then((d: any) => {
      setNotebooks(d.notebooks || []);
      setLibraries(d.libraries || []);
    }).catch(() => {});
    api.getRecentMlflowRuns(10).then((d: any) => setRecentRuns(d.runs || [])).catch(() => {});
    api.getConfig().then(setConfig).catch(() => {});
  }, []);

  const featured   = notebooks.filter(n => n.is_featured);
  const moreBuilt  = notebooks.filter(n => !n.is_featured && n.status === 'built');
  const onRequest  = notebooks.filter(n => n.status === 'on_request');

  const openNotebook = async (id: string) => {
    setOpening(id);
    try {
      const r: any = await api.openNotebook(id);
      if (r?.workspace_url) window.open(r.workspace_url, '_blank', 'noopener,noreferrer');
    } finally {
      setOpening(null);
    }
  };

  const workspaceHost = config?.workspace_host || '';

  return (
    <div className="space-y-5">
      {/* Intro */}
      <p className="text-mut text-[13.5px] leading-relaxed max-w-3xl">
        Every notebook reads the Modelling Mart, runs on serverless ML compute, and logs to MLflow for governance. All experiments are named <code className="bg-slate-100 px-1.5 py-0.5 rounded text-[12px] text-ink font-mono">pricing_workbench_*</code> and appear below.
      </p>

      {/* Databricks features callout */}
      <Card className="bg-[#eff6ff] border-[#bfdbfe]">
        <CardTitle className="text-blue-800">Databricks features demonstrated</CardTitle>
        <div className="flex flex-wrap gap-1.5">
          {['MLflow experiment tracking', 'Unity Catalog Model Registry',
            'FeatureLookup (auto-binding at serving)', 'Serverless ML compute',
            'Delta-backed training sets', 'Unity Catalog governance'].map(f => (
            <Pill key={f} tone="blue">{f}</Pill>
          ))}
        </div>
      </Card>

      {/* Featured notebooks — 4 headline cards */}
      <div>
        <SectionHead>Start here — reference notebooks</SectionHead>
        <Grid cols={2}>
          {featured.map(nb => (
            <FeaturedCard key={nb.id} nb={nb} opening={opening === nb.id} onOpen={() => openNotebook(nb.id)} />
          ))}
        </Grid>
      </div>

      {/* Model library — "Can you also do this?" tiles */}
      <Card>
        <button onClick={() => setShowLibrary(v => !v)}
                className="w-full flex items-center justify-between hover:opacity-80 transition">
          <div className="text-left flex-1">
            <CardTitle>Can you also do…?</CardTitle>
            <p className="text-xs text-mut mt-1 leading-relaxed">
              Every pricing-model type an actuary asks about. <span className="text-green-600 font-bold">✓</span> runnable · <span className="text-amber-600 font-bold">🚧</span> supported.
            </p>
          </div>
          <ChevronDown className={`w-4 h-4 text-mut transition-transform shrink-0 ml-3 ${showLibrary ? 'rotate-180' : ''}`} />
        </button>
        {showLibrary && (
          <div className="mt-4 pt-4 border-t border-line grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {[...moreBuilt, ...onRequest].map(nb => (
              <ModelTile key={nb.id} nb={nb} opening={opening === nb.id} onOpen={() => openNotebook(nb.id)} />
            ))}
          </div>
        )}
      </Card>

      {/* Recent MLflow runs — live */}
      <Card>
        <CardTitle>Recent training runs</CardTitle>
        {recentRuns.length === 0 ? (
          <div className="text-xs text-mut italic py-2">
            No runs yet. Open one of the notebooks above and train a model — it'll appear here.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-mut uppercase tracking-wide border-b border-line">
                  <th className="text-left py-2 pr-3 font-medium">Run</th>
                  <th className="text-left py-2 pr-3 font-medium">Experiment</th>
                  <th className="text-left py-2 pr-3 font-medium">Started</th>
                  <th className="text-left py-2 pr-3 font-medium">User</th>
                  <th className="text-right py-2 pr-3 font-medium">Key metric</th>
                  <th className="text-right py-2 font-medium">&nbsp;</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((r: any) => (
                  <tr key={r.run_id} className="border-b border-line last:border-b-0 hover:bg-slate-50">
                    <td className="py-2 pr-3 font-medium text-ink">{r.run_name}</td>
                    <td className="py-2 pr-3 text-xs text-ink font-mono truncate max-w-xs">
                      {(r.experiment_name || '').split('/').pop()}
                    </td>
                    <td className="py-2 pr-3 text-xs text-ink">{formatRelative(r.start_time)}</td>
                    <td className="py-2 pr-3 text-xs text-ink">{(r.user || '—').split('@')[0]}</td>
                    <td className="py-2 pr-3 text-xs text-right">
                      {r.key_metric ? (
                        <span className="font-mono">
                          <span className="text-mut">{r.key_metric.name}:</span>{' '}
                          <span className="text-ink font-medium">{r.key_metric.value}</span>
                        </span>
                      ) : <span className="text-mut">—</span>}
                    </td>
                    <td className="py-2 text-xs text-right">
                      <a href={r.url} target="_blank" rel="noopener noreferrer"
                         className="inline-flex items-center gap-1 text-brand hover:text-blue-700 font-medium">
                        Open <ExternalLink className="w-3 h-3" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Libraries — collapsible */}
      <Card>
        <button onClick={() => setShowLibs(v => !v)}
                className="w-full flex items-center justify-between hover:opacity-80 transition">
          <CardTitle>Libraries &amp; runtime</CardTitle>
          <div className="flex items-center gap-3 text-xs text-mut">
            <span>{libraries.length} pinned</span>
            <ChevronDown className={`w-4 h-4 text-mut transition-transform ${showLibs ? 'rotate-180' : ''}`} />
          </div>
        </button>
        {showLibs && (
          <div className="mt-4 pt-4 border-t border-line space-y-3">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-mut uppercase tracking-wide border-b border-line">
                    <th className="text-left py-2 pr-3 font-medium">Library</th>
                    <th className="text-left py-2 pr-3 font-medium">Version</th>
                    <th className="text-left py-2 font-medium">Purpose</th>
                  </tr>
                </thead>
                <tbody>
                  {libraries.map((l: any) => (
                    <tr key={l.name} className="border-b border-line last:border-b-0 hover:bg-slate-50">
                      <td className="py-2 pr-3 font-mono text-xs text-ink">{l.name}</td>
                      <td className="py-2 pr-3 font-mono text-xs text-ink">{l.version}</td>
                      <td className="py-2 text-xs text-ink">{l.purpose}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-mut leading-relaxed">
              Target versions for the Databricks Serverless ML runtime. Any other library can be installed in a notebook via <code className="bg-slate-100 px-1.5 py-0.5 rounded border border-line text-[11px] font-mono text-ink">%pip install</code>; serverless compute isolates each run's environment.
            </p>
          </div>
        )}
      </Card>

      {/* Browse all experiments */}
      <div className="text-center mt-2">
        <a href={workspaceHost ? `${workspaceHost}/ml/experiments` : '#'}
           target="_blank" rel="noopener noreferrer"
           className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-line rounded-lg text-sm font-medium text-ink hover:bg-slate-50 transition">
          <ExternalLink className="w-4 h-4" /> Browse all MLflow experiments
        </a>
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// Featured card — the 4 headline notebooks
// -------------------------------------------------------------

function FeaturedCard({ nb, opening, onOpen }: { nb: any; opening: boolean; onOpen: () => void }) {
  return (
    <Card className="flex flex-col hover:shadow-[0_8px_22px_rgba(15,23,42,.1)] hover:-translate-y-0.5 transition">
      <div className="flex items-start justify-between mb-2 gap-3">
        <h4 className="font-semibold text-ink leading-tight">{nb.title}</h4>
        <FlaskConical className="w-4 h-4 text-brand shrink-0 mt-0.5" />
      </div>
      <p className="text-sm text-ink leading-relaxed flex-1 text-opacity-80">{nb.description}</p>
      <div className="flex flex-wrap gap-1 mt-3 mb-3">
        {(nb.tags || []).map((t: string) => (
          <Pill key={t} tone="slate">{t}</Pill>
        ))}
      </div>
      <div className="flex items-center gap-3 mt-auto pt-3 border-t border-line">
        <button onClick={onOpen} disabled={opening}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-brand text-white rounded-lg text-xs font-medium hover:bg-blue-700 disabled:opacity-50 transition">
          <ExternalLink className="w-3 h-3" /> {opening ? 'Opening…' : 'Open'}
        </button>
        <a href={`${GITHUB_REPO_URL}/blob/main/src/04_models/${nb.id}.py`}
           target="_blank" rel="noopener noreferrer"
           className="text-xs text-brand hover:text-blue-700 inline-flex items-center gap-1 font-medium">
          <Code className="w-3 h-3" /> GitHub
        </a>
      </div>
    </Card>
  );
}

// -------------------------------------------------------------
// Model library tile — compact "can you also do this?"
// -------------------------------------------------------------

function ModelTile({ nb, opening, onOpen }: { nb: any; opening: boolean; onOpen: () => void }) {
  const isBuilt = nb.status === 'built';
  return (
    <div className={`border rounded-lg p-3 ${isBuilt ? 'bg-white border-line' : 'bg-slate-50 border-line'}`}>
      <div className="flex items-start justify-between gap-2 mb-1">
        <h5 className="text-sm font-semibold text-ink leading-tight">{nb.title}</h5>
        <span className={`text-xs shrink-0 font-bold ${isBuilt ? 'text-emerald-600' : 'text-amber-600'}`}>
          {isBuilt ? '✓' : '🚧'}
        </span>
      </div>
      <p className="text-xs text-ink leading-relaxed mb-2 text-opacity-75">{nb.description}</p>
      <div className="flex flex-wrap gap-1 mb-2">
        {(nb.tags || []).map((t: string) => (
          <Pill key={t} tone="slate">{t}</Pill>
        ))}
      </div>
      {isBuilt && (
        <button onClick={onOpen} disabled={opening}
                className="text-xs text-brand hover:text-blue-700 font-medium disabled:opacity-50 inline-flex items-center gap-1 transition">
          {opening ? 'Opening…' : 'Open →'}
        </button>
      )}
    </div>
  );
}

// -------------------------------------------------------------
// Helpers
// -------------------------------------------------------------

function formatRelative(iso?: string): string {
  if (!iso) return '—';
  const t = new Date(iso).getTime();
  if (isNaN(t)) return '—';
  const diff = Date.now() - t;
  if (diff < 60_000) return 'just now';
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

