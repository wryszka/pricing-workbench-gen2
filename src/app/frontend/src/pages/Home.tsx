import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Database, Table2, Shield, ArrowRight, Code, Rocket, Sparkles,
  Calculator, Loader2, AlertCircle, Activity, Sparkle,
} from 'lucide-react';
import { api } from '../lib/api';

export default function Home() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Hero */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Pricing Workbench</h1>
        <p className="text-sm text-gray-500 mt-1 max-w-3xl">
          Control tower for a commercial pricing operation on Databricks — the live rate
          book, portfolio, model &amp; service health at a glance. Every stage of the flow is
          traceable, governed, and auditable.
        </p>
      </div>

      {/* Control tower — current state */}
      <ControlTower />

      {/* About this demo — compact disclaimer */}
      <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5">
        <span className="text-[11px] font-semibold text-amber-900 uppercase tracking-wide mr-2">About this demo</span>
        <span className="text-xs text-amber-900/90">
          Bricksurance SE is synthetic — policies, quotes, claims and demographics are generated;
          UK postcode enrichment is real public data. Models, agents (Claude via the Databricks
          Foundation Model API), governance packs, audit log and scoring are real. Not a Databricks product.
        </span>
      </div>

      {/* Explore the workbench */}
      <div className="mb-3 mt-10 flex items-end justify-between">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Explore the workbench</h2>
        <Link to="/learn" className="text-[11px] text-blue-600 hover:underline">New here? Start with Learn →</Link>
      </div>
      <FlowSpine />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8 mt-6">
        <SectionCard to="/datasets" icon={Database} color="blue" title="Data Ingestion"
          description="Internal book + vendor feeds + public reference data. Vendor data passes an actuary approval gate with DQ checks."
          features={['Internal + vendor + public', 'DQ expectations', 'Actuary approval gate']} />
        <SectionCard to="/pricing-table" icon={Table2} color="green" title="Modelling Mart"
          description="Engineered feature table — every approved source joined on the active book. Factor catalog with per-factor provenance and an embedded AI/BI Genie."
          features={['Contributing sources', 'Factor catalog + lineage', 'AI/BI Genie']} />
        <SectionCard to="/development" icon={Code} color="purple" title="Model Development"
          description="Train, compare, promote. Reference notebooks + model library, candidate vs champion comparison, pack generation on promotion."
          features={['Train', 'Compare & test', 'Promote → governance pack']} />
        <SectionCard to="/pricing-engine" icon={Calculator} color="emerald" title="Pricing Engine"
          description="The live rate book — monthly releases bundling the 4 champion families + rating-engine config, with full effective-dated history."
          features={['Rolling monthly releases', 'Live = current month', 'Committee narrative']} />
        <SectionCard to="/governance" icon={Shield} color="amber" title="Model Governance"
          description="Post-promotion defence for regulators. Browse by model, by date, or by policy — with an LLM assistant grounded in the governance pack."
          features={['By model / date / policy', 'Immutable audit trail', 'Agent-assisted review']} />
        <SectionCard to="/pricing-ai" icon={Sparkles} color="purple" title="Pricing AI"
          description="One chat surface fronting every agent — governance, bias, ingestion-impact, factory-review, plus AI/BI Genie. Auto-routes or pin a sub-agent."
          features={['Mosaic AI Agent Framework', 'AI/BI Genie', 'Auto-routing classifier']} />
      </div>

      <div className="mb-8">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Reference architecture · one platform, integrated</h2>
        <ArchBlock />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Control tower — live state dashboard
// ---------------------------------------------------------------------------

function ControlTower() {
  const [ov, setOv] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [ai, setAi] = useState<string | null>(null);

  useEffect(() => {
    api.getOverview().then(setOv).catch((e) => setErr(e.message || String(e)));
    api.getOverviewAiSummary().then((d) => setAi(d?.summary || null)).catch(() => setAi(null));
  }, []);

  if (err) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 flex items-center gap-2">
        <AlertCircle className="w-4 h-4" /> Couldn't load current state: {err.slice(0, 160)}
      </div>
    );
  }
  if (!ov) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white px-4 py-8 text-sm text-gray-500 flex items-center justify-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin" /> Loading current state…
      </div>
    );
  }

  const live = ov.live_release || {};
  const k = ov.kpis || {};
  const gov = ov.governance || {};

  return (
    <div className="space-y-4">
      {/* AI overview strip */}
      <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 flex items-start gap-3">
        <Sparkle className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
        <div className="flex-1">
          <div className="text-[10px] font-semibold text-blue-800 uppercase tracking-wide mb-0.5">Where we are</div>
          <p className="text-sm text-blue-900/90 leading-relaxed">
            {ai || <span className="inline-flex items-center gap-1.5 text-blue-700/70"><Loader2 className="w-3 h-3 animate-spin" /> summarising current state…</span>}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Live rate book */}
        <Link to="/pricing-engine" className="lg:col-span-1 block rounded-lg border border-emerald-200 bg-white hover:shadow-md transition p-4">
          <div className="flex items-center gap-2 mb-2">
            <Calculator className="w-4 h-4 text-emerald-600" />
            <span className="text-[10px] font-semibold text-emerald-700 uppercase tracking-wide">Live rate book</span>
            <span className="ml-auto flex items-center gap-1 text-[10px] text-emerald-700"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> live</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">{live.display_name || '—'}</div>
          <div className="text-[11px] text-gray-500 mb-3">
            effective {live.effective_date || '—'} · rating engine {live.rating_engine_version || '—'}
            {ov.prev_release?.display_name && <> · prev {ov.prev_release.display_name}</>}
          </div>
          <div className="grid grid-cols-4 gap-1.5">
            {[['freq', live.freq_glm_version], ['sev', live.sev_glm_version], ['demand', live.demand_gbm_version], ['fraud', live.fraud_glm_version ?? live.fraud_gbm_version]].map(([lbl, v]) => (
              <div key={lbl as string} className="rounded bg-gray-50 border border-gray-200 px-1.5 py-1 text-center">
                <div className="text-[9px] text-gray-500 uppercase">{lbl}</div>
                <div className="text-xs font-semibold text-gray-800">v{v ?? '—'}</div>
              </div>
            ))}
          </div>
        </Link>

        {/* KPIs */}
        <div className="lg:col-span-2 rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="w-4 h-4 text-gray-500" />
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Portfolio</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Kpi label="Policies" value={fmtInt(k.book_size)} />
            <Kpi label="GWP" value={fmtMoney(k.gwp)} />
            <Kpi label="Loss ratio (5y)" value={fmtPct(k.loss_ratio)} />
            <Kpi label="Quotes (30d)" value={fmtInt(k.quotes_30d)} />
            <Kpi label="Bind rate" value={fmtPct(k.bind_rate)} />
          </div>
        </div>
      </div>

      {/* Process ribbon */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 overflow-x-auto">
        <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-3">Pipeline health</div>
        <div className="flex items-stretch gap-2 min-w-[760px]">
          {(ov.stages || []).map((s: any, i: number) => (
            <div key={s.key} className="flex items-stretch gap-2 flex-1">
              <Link to={stageRoute(s.key)} className="flex-1 rounded-lg border border-gray-200 bg-gray-50 hover:bg-blue-50 hover:border-blue-300 p-2.5 transition">
                <div className="flex items-center gap-1.5 mb-1">
                  <span className={`w-2 h-2 rounded-full ${s.ok ? 'bg-emerald-500' : 'bg-amber-400'}`} />
                  <span className="text-xs font-semibold text-gray-900">{s.label}</span>
                </div>
                <div className="text-[11px] text-gray-500 leading-snug">{s.metric}</div>
              </Link>
              {i < ov.stages.length - 1 && <div className="flex items-center shrink-0"><ArrowRight className="w-3.5 h-3.5 text-gray-300" /></div>}
            </div>
          ))}
        </div>
      </div>

      {/* Service + governance health */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-2">Serving endpoints</div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(ov.endpoint_health || {}).map(([key, v]: [string, any]) => (
              <span key={key} className="inline-flex items-center gap-1.5 px-2 py-1 rounded border text-[11px] border-gray-200 bg-gray-50 text-gray-700">
                <span className={`w-1.5 h-1.5 rounded-full ${v.ready ? 'bg-emerald-500' : 'bg-gray-300'}`} />
                {key.replace(/_/g, ' ')}
                <span className="text-gray-400">{v.ready ? 'warm' : 'idle'}</span>
              </span>
            ))}
            {(!ov.endpoint_health || Object.keys(ov.endpoint_health).length === 0) && <span className="text-xs text-gray-400">—</span>}
          </div>
          <p className="text-[10px] text-gray-400 mt-2">Scale-to-zero — "idle" endpoints cold-start on first call (~30s), then sub-second.</p>
        </div>
        <Link to="/governance" className="rounded-lg border border-gray-200 bg-white hover:shadow-md transition p-4">
          <div className="flex items-center gap-2 mb-2">
            <Shield className="w-4 h-4 text-amber-600" />
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Governance</span>
          </div>
          <div className="text-xl font-bold text-gray-900">{fmtInt(gov.packs)} packs</div>
          <div className="text-[11px] text-gray-500">latest {gov.latest ? String(gov.latest).slice(0, 10) : '—'} · immutable audit trail</div>
        </Link>
      </div>
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-gray-50 border border-gray-200 px-3 py-2.5">
      <div className="text-[10px] text-gray-500 uppercase tracking-wide">{label}</div>
      <div className="text-lg font-bold text-gray-900 leading-tight mt-0.5">{value}</div>
    </div>
  );
}

const fmtInt = (v: any) => (v === null || v === undefined ? '—' : Number(v).toLocaleString());
const fmtPct = (v: any) => (v === null || v === undefined ? '—' : `${(Number(v) * 100).toFixed(0)}%`);
const fmtMoney = (v: any) => {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (n >= 1e9) return `£${(n / 1e9).toFixed(1)}bn`;
  if (n >= 1e6) return `£${(n / 1e6).toFixed(1)}m`;
  if (n >= 1e3) return `£${(n / 1e3).toFixed(0)}k`;
  return `£${n.toLocaleString()}`;
};
const stageRoute = (key: string) => ({
  ingestion: '/datasets', mart: '/pricing-table', dev: '/development',
  deployment: '/deployment', pricing: '/pricing-engine', governance: '/governance',
} as Record<string, string>)[key] || '/';

// ---------------------------------------------------------------------------
// Flow spine
// ---------------------------------------------------------------------------

function FlowSpine() {
  const steps = [
    { to: '/datasets',      icon: Database, label: 'Data Ingestion',    sub: 'approved sources' },
    { to: '/pricing-table', icon: Table2,   label: 'Modelling Mart',    sub: 'feature table' },
    { to: '/development',   icon: Code,     label: 'Model Development', sub: 'train · compare · promote' },
    { to: '/deployment',    icon: Rocket,   label: 'Deployment',        sub: 'UC champions · rollback' },
    { to: '/pricing-engine',icon: Calculator, label: 'Pricing Engine',  sub: 'the live rate book' },
    { to: '/governance',    icon: Shield,   label: 'Governance',        sub: 'defend to regulators' },
  ];
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 overflow-x-auto">
      <div className="flex items-stretch gap-2 min-w-[760px]">
        {steps.map((s, i) => (
          <div key={s.to} className="flex items-stretch gap-2 flex-1">
            <Link to={s.to} className="flex-1 rounded-lg border border-gray-200 bg-gray-50 hover:bg-blue-50 hover:border-blue-300 p-3 transition">
              <s.icon className="w-4 h-4 text-gray-600 mb-1.5" />
              <div className="text-sm font-semibold text-gray-900 leading-tight">{s.label}</div>
              <div className="text-[11px] text-gray-500 mt-0.5 leading-snug">{s.sub}</div>
            </Link>
            {i < steps.length - 1 && (
              <div className="flex items-center shrink-0 px-0.5"><ArrowRight className="w-4 h-4 text-gray-400" /></div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section card
// ---------------------------------------------------------------------------

function SectionCard({ to, icon: Icon, color, title, description, features, full }: {
  to: string; icon: any; color: string; title: string; description: string;
  features: string[]; full?: boolean;
}) {
  const colorMap: Record<string, { bg: string; border: string; icon: string; badge: string }> = {
    blue:    { bg: 'bg-blue-50',    border: 'border-blue-200',    icon: 'text-blue-600',    badge: 'bg-blue-100 text-blue-700' },
    purple:  { bg: 'bg-purple-50',  border: 'border-purple-200',  icon: 'text-purple-600',  badge: 'bg-purple-100 text-purple-700' },
    green:   { bg: 'bg-green-50',   border: 'border-green-200',   icon: 'text-green-600',   badge: 'bg-green-100 text-green-700' },
    emerald: { bg: 'bg-emerald-50', border: 'border-emerald-200', icon: 'text-emerald-600', badge: 'bg-emerald-100 text-emerald-700' },
    amber:   { bg: 'bg-amber-50',   border: 'border-amber-200',   icon: 'text-amber-600',   badge: 'bg-amber-100 text-amber-700' },
    red:     { bg: 'bg-red-50',     border: 'border-red-200',     icon: 'text-red-600',     badge: 'bg-red-100 text-red-700' },
    indigo:  { bg: 'bg-indigo-50',  border: 'border-indigo-200',  icon: 'text-indigo-600',  badge: 'bg-indigo-100 text-indigo-700' },
    gray:    { bg: 'bg-gray-50',    border: 'border-gray-200',    icon: 'text-gray-600',    badge: 'bg-gray-100 text-gray-700' },
  };
  const c = colorMap[color] || colorMap.blue;
  return (
    <Link to={to} className={`group block ${c.bg} border ${c.border} rounded-lg p-5 hover:shadow-md transition-all ${full ? 'col-span-full' : ''}`}>
      <div className="flex items-center gap-3 mb-2">
        <Icon className={`w-5 h-5 ${c.icon}`} />
        <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">{title}</h3>
        <ArrowRight className="w-4 h-4 text-gray-400 ml-auto group-hover:translate-x-1 transition-transform" />
      </div>
      <p className="text-sm text-gray-600 mb-3">{description}</p>
      <div className="flex flex-wrap gap-1.5">
        {features.map((f, i) => (
          <span key={i} className={`px-2 py-0.5 rounded text-[10px] font-medium ${c.badge}`}>{f}</span>
        ))}
      </div>
    </Link>
  );
}

// ---------------------------------------------------------------------------
// Reference architecture block
// ---------------------------------------------------------------------------

function ArchBlock() {
  const layers = [
    { title: 'Sources',        colour: 'blue',    items: ['Internal book (policies, claims)', 'Vendor feeds (geospatial, credit, market)', 'Public data (ONSPD, IMD)'] },
    { title: 'Bronze → Silver', colour: 'cyan',    items: ['DLT pipeline · expectations', 'HITL approval gate', 'Versioned, audited'] },
    { title: 'Modelling Mart',  colour: 'green',   items: ['Per-LOB feature tables (Delta)', 'Online Feature Store', 'AI/BI Genie over the mart'] },
    { title: 'Models',          colour: 'purple',  items: ['GLMs · GBMs (4 families)', 'MLflow + Unity Catalog registry', 'Model Factory · agent-narrated'] },
    { title: 'Champions',       colour: 'red',     items: ['UC alias-based versioning', 'One-click rollback', 'Mosaic AI Model Serving'] },
    { title: 'Rating engine',   colour: 'emerald', items: ['Real-time API · <500ms', 'Batch enrichment', 'Factor-table export'] },
  ];
  const colourMap: Record<string, { bg: string; border: string; pill: string; head: string }> = {
    blue:    { bg: 'bg-blue-50',    border: 'border-blue-200',    pill: 'bg-blue-200    text-blue-900',    head: 'text-blue-700' },
    cyan:    { bg: 'bg-cyan-50',    border: 'border-cyan-200',    pill: 'bg-cyan-200    text-cyan-900',    head: 'text-cyan-700' },
    green:   { bg: 'bg-green-50',   border: 'border-green-200',   pill: 'bg-green-200   text-green-900',   head: 'text-green-700' },
    purple:  { bg: 'bg-purple-50',  border: 'border-purple-200',  pill: 'bg-purple-200  text-purple-900',  head: 'text-purple-700' },
    red:     { bg: 'bg-red-50',     border: 'border-red-200',     pill: 'bg-red-200     text-red-900',     head: 'text-red-700' },
    emerald: { bg: 'bg-emerald-50', border: 'border-emerald-200', pill: 'bg-emerald-200 text-emerald-900', head: 'text-emerald-700' },
  };
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 overflow-x-auto">
      <div className="flex items-stretch gap-2 min-w-[860px]">
        {layers.map((l, i) => {
          const c = colourMap[l.colour];
          return (
            <div key={l.title} className="flex items-stretch gap-2 flex-1">
              <div className={`flex-1 rounded-lg border ${c.border} ${c.bg} p-3`}>
                <div className={`text-[10px] uppercase tracking-wider font-bold ${c.head} mb-1.5`}>Layer {i + 1}</div>
                <div className="text-sm font-semibold text-gray-900 mb-2">{l.title}</div>
                <div className="space-y-1">
                  {l.items.map(it => (<div key={it} className={`text-[11px] px-1.5 py-0.5 rounded ${c.pill}`}>{it}</div>))}
                </div>
              </div>
              {i < layers.length - 1 && (<div className="flex items-center shrink-0 px-0.5"><ArrowRight className="w-4 h-4 text-gray-400" /></div>)}
            </div>
          );
        })}
      </div>
      <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-2 text-[11px] text-gray-600">
        <div className="px-3 py-2 rounded bg-amber-50 border border-amber-200"><span className="font-semibold text-amber-900">Cross-cutting:</span> Unity Catalog lineage · audit log · governance packs · bias monitor</div>
        <div className="px-3 py-2 rounded bg-violet-50 border border-violet-200"><span className="font-semibold text-violet-900">Agents:</span> Claude via FM API · grounded over packs, audit log, mart</div>
        <div className="px-3 py-2 rounded bg-gray-50 border border-gray-200"><span className="font-semibold text-gray-800">Integration:</span> one scoring adapter to your rating engine — nothing else changes</div>
      </div>
    </div>
  );
}
