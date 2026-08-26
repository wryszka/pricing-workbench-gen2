import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Sparkles, ArrowRight, Calculator, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';
import { api } from '../lib/api';
import {
  Page, OnThisPage, Card, CardTitle, Metric, Pill, Prov, DemoDisclaimer, SectionHead, Grid, AgentLead,
} from '../components/ui';

export default function Home() {
  return (
    <Page>
      {/* Hero */}
      <div>
        <div className="text-[11px] font-bold uppercase tracking-[0.08em] text-brand">Bricksurance SE · Pricing Workbench</div>
        <h1 className="text-[32px] font-bold text-ink leading-tight mt-1">Commercial pricing. One governed control tower.</h1>
        <p className="text-mut text-[15px] leading-relaxed mt-2 max-w-3xl">
          The live rate book, the portfolio, and model &amp; service health at a glance — every stage of the
          flow traceable, governed and auditable, from ingestion through the live pricing engine to
          regulator-facing defence. Humans decide; everything is recorded.
        </p>
      </div>

      <ControlTower />

      <DemoDisclaimer>
        This is <strong>not a Databricks product</strong> — an example of commercial pricing built purely on
        Databricks (Unity Catalog, Delta, MLflow, Mosaic AI Agent Framework &amp; Model Serving, the Foundation
        Model API and Databricks Apps). Bricksurance SE is synthetic — policies, quotes, claims and
        demographics are generated; the UK postcode enrichment is real public data (OGL). Models, agents
        (Claude), governance packs, the audit log and scoring are real.
      </DemoDisclaimer>

      {/* Explore */}
      <div className="pt-2 flex items-end justify-between">
        <SectionHead>Explore the workbench</SectionHead>
        <Link to="/learn" className="text-[11px] text-brand hover:underline">New here? Start with Learn →</Link>
      </div>
      <FlowRibbon />

      <SectionHead>The three things this platform makes possible</SectionHead>
      <ThreePillars />
    </Page>
  );
}

// ---------------------------------------------------------------------------
// Three pillars — the standard Bricksurance landing section
// ---------------------------------------------------------------------------
function ThreePillars() {
  const pillars = [
    { e: '🏛️', t: 'One platform — one source of truth', to: '/pricing-table',
      borderCls: 'border-t-[3px] border-blue-600', textCls: 'text-blue-600',
      b: 'Ingestion, the modelling mart, models, champions, the rating engine and governance all read the same governed Delta tables — one platform instead of six systems and a swivel chair.' },
    { e: '🛡️', t: 'Governance & control', to: '/governance',
      borderCls: 'border-t-[3px] border-violet-600', textCls: 'text-violet-600',
      b: 'Real Unity Catalog lineage, versioned constraints in git, an immutable audit log, a bias monitor — every pricing decision reproducible exactly as it was made.' },
    { e: '🤖', t: 'AI agents that assist', to: '/pricing-ai',
      borderCls: 'border-t-[3px] border-green-600', textCls: 'text-green-600',
      b: 'A bench of specialists — Ask-the-Book, model validation, drift watch, rate-change — advising a named human who decides. Agents never set prices; a deterministic engine does, under versioned policy.' },
  ];
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {pillars.map((p) => (
        <Link key={p.to} to={p.to}
          className={`flex flex-col rounded-2xl border border-line bg-white p-5 hover:shadow-[0_8px_22px_rgba(15,23,42,.1)] transition ${p.borderCls}`}>
          <div className="text-[26px]">{p.e}</div>
          <h3 className="text-[15px] font-bold text-ink mt-2">{p.t}</h3>
          <p className="text-[13px] text-mut leading-relaxed mt-1.5 flex-1">{p.b}</p>
          <div className={`text-[13px] font-bold mt-2.5 ${p.textCls}`}>open →</div>
        </Link>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Control tower
// ---------------------------------------------------------------------------
function ControlTower() {
  const [ov, setOv] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.getOverview().then(setOv).catch((e) => setErr(e.message || String(e)));
  }, []);

  if (err) return <Card className="border-red-200"><span className="text-sm text-red-700">Couldn't load current state: {err.slice(0, 160)}</span></Card>;
  if (!ov) return <Card><span className="text-mut text-sm inline-flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Loading current state…</span></Card>;

  const live = ov.live_release || {};
  const k = ov.kpis || {};
  const gov = ov.governance || {};
  const stageRoute: Record<string, string> = {
    ingestion: '/datasets', mart: '/pricing-table', dev: '/development',
    deployment: '/deployment', pricing: '/pricing-engine', governance: '/governance',
  };

  return (
    <div className="space-y-4">
      {/* Lead with the agent — Ask the Book reads the current state, then answers follow-ups */}
      <AgentLead
        persona="ask_the_book"
        title="Ask the Book"
        subtitle="Your pricing analyst on the governed marts — rate adequacy, loss-ratio trend, mix and competitive position. It reads the book below, then answers follow-ups."
        seed="In 3 short sentences, give me the state of the book right now: overall loss ratio, which segments look underpriced, and what I should look at first."
        examples={[
          'Which trade segments are underpriced?',
          'Where is our loss ratio worst?',
          'How competitive are our quotes vs market?',
        ]}
      />

      <Grid cols={3}>
        {/* Live rate book */}
        <Link to="/pricing-engine" className="block">
          <Card drill className="h-full">
            <div className="flex items-center gap-2 mb-1">
              <Calculator className="w-4 h-4 text-emerald-600" />
              <CardTitle>Live rate book</CardTitle>
              <span className="ml-auto"><Pill tone="live">live</Pill></span>
            </div>
            <div className="text-[26px] font-extrabold text-ink leading-tight">{live.display_name || '—'}</div>
            <div className="text-[11px] text-mut mb-2">
              effective {live.effective_date || '—'} · rating engine {live.rating_engine_version || '—'}
              {ov.prev_release?.display_name && <> · prev {ov.prev_release.display_name}</>}
            </div>
            <div className="grid grid-cols-4 gap-1.5">
              {[['freq', live.freq_glm_version], ['sev', live.sev_glm_version], ['demand', live.demand_gbm_version], ['fraud', live.fraud_gbm_version]].map(([lbl, v]) => (
                <div key={lbl as string} className="rounded-lg bg-slate-50 border border-line px-1.5 py-1 text-center">
                  <div className="text-[9px] text-mut uppercase">{lbl}</div>
                  <div className="text-xs font-bold text-ink">v{(v as string) ?? '—'}</div>
                </div>
              ))}
            </div>
          </Card>
        </Link>

        {/* KPIs */}
        <div className="md:col-span-2">
          <Card className="h-full">
            <CardTitle>Portfolio</CardTitle>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <Metric label="Policies" value={fmtInt(k.book_size)} tone="blue" />
              <Metric label="GWP" value={fmtMoney(k.gwp)} tone="blue" />
              <Metric label="Loss ratio 5y" value={fmtPct(k.loss_ratio)} tone="amber" />
              <Metric label="Quotes 30d" value={fmtInt(k.quotes_30d)} tone="green" />
              <Metric label="Bind rate" value={fmtPct(k.bind_rate)} tone="violet" />
            </div>
          </Card>
        </div>
      </Grid>

      {/* Pipeline health ribbon */}
      <Card>
        <CardTitle>Pipeline health</CardTitle>
        <div className="flex items-stretch gap-2 overflow-x-auto min-w-0">
          {(ov.stages || []).map((s: any, i: number) => (
            <div key={s.key} className="flex items-stretch gap-2 flex-1">
              <Link to={stageRoute[s.key] || '/'} className="flex-1 rounded-xl border border-line bg-slate-50 hover:bg-blue-50 hover:border-blue-200 p-2.5 transition min-w-[120px]">
                <div className="flex items-center gap-1.5 mb-1">
                  {s.ok
                    ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                    : <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />}
                  <span className="text-xs font-bold text-ink">{s.label}</span>
                </div>
                <div className="text-[11px] text-mut leading-snug">{s.metric}</div>
              </Link>
              {i < ov.stages.length - 1 && <div className="flex items-center shrink-0"><ArrowRight className="w-3.5 h-3.5 text-slate-300" /></div>}
            </div>
          ))}
        </div>
      </Card>

      {/* Health */}
      <Grid cols={2}>
        <Card>
          <CardTitle>Serving endpoints</CardTitle>
          <div className="flex flex-wrap gap-2">
            {Object.entries(ov.endpoint_health || {}).map(([key, v]: [string, any]) => (
              <span key={key} className="inline-flex items-center gap-1.5 px-2 py-1 rounded border border-line bg-slate-50 text-[11px] text-slate-700">
                <span className={`w-1.5 h-1.5 rounded-full ${v.ready ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                {key.replace(/_/g, ' ')} <span className="text-slate-400">{v.ready ? 'warm' : 'idle'}</span>
              </span>
            ))}
            {(!ov.endpoint_health || Object.keys(ov.endpoint_health).length === 0) && <span className="text-xs text-mut">—</span>}
          </div>
          <p className="text-[10px] text-slate-400 mt-2">Scale-to-zero — "idle" endpoints cold-start on first call (~30s), then sub-second.</p>
        </Card>
        <Link to="/governance" className="block">
          <Card drill className="h-full">
            <CardTitle>Governance</CardTitle>
            <div className="text-[26px] font-extrabold text-ink leading-tight">{fmtInt(gov.packs)} packs</div>
            <div className="text-[11px] text-mut">latest {gov.latest ? String(gov.latest).slice(0, 10) : '—'} · immutable audit trail</div>
          </Card>
        </Link>
      </Grid>

      <Prov>Computed live from the governed marts — the live release is this month's rate book; every tile links to the page it comes from.</Prov>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Flow ribbon — the end-to-end spine (underwriting .lstage style)
// ---------------------------------------------------------------------------
function FlowRibbon() {
  const stages = [
    { n: '1 · Sources', t: 'Data Ingestion', b: 'Internal book + vendor feeds + real public data, through an actuary approval gate.', to: '/datasets', borderCls: 'border-t-[3px] border-blue-600', textCls: 'text-blue-600' },
    { n: '2 · Features', t: 'Modelling Mart', b: 'Every approved source joined on the active book — factor catalog with provenance + Genie.', to: '/pricing-table', borderCls: 'border-t-[3px] border-cyan-600', textCls: 'text-cyan-600' },
    { n: '3 · Models', t: 'Model Development', b: 'Train, compare, promote — pack generation on promotion.', to: '/development', borderCls: 'border-t-[3px] border-blue-600', textCls: 'text-blue-600' },
    { n: '4 · Champions', t: 'Deployment', b: 'UC alias-based versioning across all four families, one-click rollback.', to: '/deployment', borderCls: 'border-t-[3px] border-violet-600', textCls: 'text-violet-600' },
    { n: '5 · The price', t: 'Pricing Engine', b: 'The live rate book — rolling monthly releases; this month is live.', to: '/pricing-engine', borderCls: 'border-t-[3px] border-green-600', textCls: 'text-green-600' },
    { n: '6 · Defend', t: 'Governance', b: 'Browse packs by model / date / policy, grounded LLM assistant, immutable audit.', to: '/governance', borderCls: 'border-t-[3px] border-amber-600', textCls: 'text-amber-600' },
  ];
  return (
    <>
      <OnThisPage>
        The pricing flow, end to end. Each stage is a page — click any card to jump in. Data Ingestion enriches
        and gates sources; the Modelling Mart is the governed feature table; models are trained and promoted to
        champions; the Pricing Engine ships them as the live monthly rate book; Governance defends every decision.
      </OnThisPage>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {stages.map((s) => (
          <Link key={s.to} to={s.to}
            className={`flex flex-col rounded-xl border border-line bg-white p-3 hover:shadow-[0_8px_22px_rgba(15,23,42,.1)] hover:-translate-y-0.5 transition ${s.borderCls}`}>
            <div className="text-[10px] font-extrabold text-slate-400 uppercase tracking-wide">{s.n}</div>
            <div className="text-[13.5px] font-bold text-ink mt-0.5">{s.t}</div>
            <div className="text-[11px] text-mut leading-snug mt-1.5 flex-1">{s.b}</div>
            <div className={`text-[11px] font-bold mt-2 ${s.textCls}`}>open →</div>
          </Link>
        ))}
      </div>
    </>
  );
}

const fmtInt = (v: any) => (v == null ? '—' : Number(v).toLocaleString());
const fmtPct = (v: any) => (v == null ? '—' : `${(Number(v) * 100).toFixed(0)}%`);
const fmtMoney = (v: any) => {
  if (v == null) return '—';
  const n = Number(v);
  if (n >= 1e9) return `£${(n / 1e9).toFixed(1)}bn`;
  if (n >= 1e6) return `£${(n / 1e6).toFixed(1)}m`;
  if (n >= 1e3) return `£${(n / 1e3).toFixed(0)}k`;
  return `£${n.toLocaleString()}`;
};
