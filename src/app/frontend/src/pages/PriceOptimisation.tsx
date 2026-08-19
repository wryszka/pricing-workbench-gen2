import { useEffect, useState } from 'react';
import { Target, ShieldCheck, GitBranch, TrendingUp, ChevronRight } from 'lucide-react';
import { api } from '../lib/api';
import {
  Page, PageHeader, OnThisPage, AgentLead, Card, CardTitle, Section, Metric, Pill,
  Grid, Note, Prov, UnderTheHood, Loading,
} from '../components/ui';

export default function PriceOptimisation() {
  const [ov, setOv] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.optOverview().then(setOv).catch(() => setOv({ ready: false })).finally(() => setLoading(false));
  }, []);

  const money = (v: any) => {
    if (v == null) return '—';
    const n = Number(v);
    if (Math.abs(n) >= 1e9) return `£${(n / 1e9).toFixed(1)}bn`;
    if (Math.abs(n) >= 1e6) return `£${(n / 1e6).toFixed(1)}m`;
    if (Math.abs(n) >= 1e3) return `£${(n / 1e3).toFixed(0)}k`;
    return `£${n.toLocaleString()}`;
  };

  return (
    <Page>
      <PageHeader eyebrow="Bricksurance SE · Price Optimisation" title="Price Optimisation"
        subtitle="Model demand, simulate the book, decide under versioned constraints — open code, elastic compute, agents that assist. A deterministic solver sets prices; the human sets the policy."
        icon={Target} />

      <AgentLead persona="rate_change" title="Rate-change analyst"
        subtitle="What a proposed rate move does to the book — winners/losers, retention risk, the fairness angle."
        seed="Summarise the current optimisation result: expected profit uplift vs holding, which segments move, and whether any breach the corridor."
        examples={['Who wins and who loses under the optimised factors?', 'What is the retention risk?', 'Is any segment outside the corridor?']} />

      <OnThisPage>
        The offline optimisation loop: <b>demand → simulate → decide under constraints → deploy → monitor</b>.
        The risk model is the floor (cost); optimisation shapes margin above it, only within a versioned
        deviation corridor. The solver run is always offline; execution mode (batch factor table vs. real-time
        endpoint) is a config flag.
      </OnThisPage>

      {loading ? <Loading label="Loading optimisation state…" />
        : !ov?.ready ? (
          <Note>
            No optimisation run yet. Run the flow to populate — <code>databricks bundle run opt_full</code>
            {' '}(data → elasticity → simulate → solve → monitor). This page then shows scenarios, the factor
            table, elasticity curves and monitoring.
          </Note>
        ) : (
          <>
            <Grid cols={4}>
              <Metric label="Best expected profit" value={money(ov.best_profit)} tone="green" />
              <Metric label="Hold (do nothing)" value={money(ov.hold_profit)} tone="plain" />
              <Metric label="Uplift" value={money((ov.factors || {}).total_uplift)} tone="blue"
                sub="vs holding, within corridor" />
              <Metric label="Corridor breaches" value={String((ov.factors || {}).breaches ?? '—')}
                tone={((ov.factors || {}).breaches ? 'red' : 'green')} sub="gate: must be 0" />
            </Grid>

            <ConstraintCard />
            <ElasticityCurves />
            <FactorTable money={money} />
            <ScenariosCard money={money} />
            <MonitoringCard />
          </>
        )}

      <UnderTheHood title="Price Optimisation" lines={[
        { component: 'opt_quote_response', detail: 'conversion/elasticity training set (derived from the quote stream)' },
        { component: 'pwg2_conversion_elasticity', detail: 'LightGBM, price-monotone (monotone_constraints)' },
        { component: 'opt_scenarios', detail: 'N candidate price sets scored via the elasticity curves' },
        { component: 'constraints/default.yaml', detail: 'versioned pricing policy (git history = audit trail)' },
        { component: 'scipy solver', detail: 'per-segment optimise within the corridor → opt_factor_table' },
        { component: 'audit_log', detail: 'every solve recorded; the deployment gate enforces the corridor server-side' },
      ]} />
    </Page>
  );
}

function ConstraintCard() {
  const [c, setC] = useState<any>(null);
  const [open, setOpen] = useState(false);
  useEffect(() => { api.optConstraints().then(setC).catch(() => setC({ ok: false })); }, []);
  return (
    <Section title="Constraint set — policy as code"
      subtitle={c?.ok ? `version ${c.version} · versioned in git (open its history live)` : 'the versioned pricing policy the solver is bound by'}
      actions={<button onClick={() => setOpen((v) => !v)} className="text-[11px] text-brand inline-flex items-center gap-1">
        <GitBranch className="w-3.5 h-3.5" /> {open ? 'hide' : 'show'} YAML <ChevronRight className={`w-3 h-3 transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>}>
      <p className="text-[13px] text-mut">
        Deviation corridor around technical price, GIPP renewal rule, per-segment caps, forbidden/proxy signal
        exclusions, monotonicity + jurisdiction toggle. The solver reads this; the gate enforces it — an agent
        cannot bypass it.
      </p>
      {open && c?.yaml && (
        <pre className="mt-3 text-[11px] leading-relaxed bg-slate-900 text-slate-100 rounded-lg p-3 overflow-x-auto max-h-96">{c.yaml}</pre>
      )}
    </Section>
  );
}

function ElasticityCurves() {
  const [curves, setCurves] = useState<any[]>([]);
  useEffect(() => { api.optCurves().then((d) => setCurves(d?.curves || [])).catch(() => setCurves([])); }, []);
  if (!curves.length) return null;
  const bySeg: Record<string, { x: number; y: number }[]> = {};
  curves.forEach((r) => { (bySeg[r.segment] ||= []).push({ x: Number(r.price_ratio), y: Number(r.p_convert) }); });
  const segs = Object.keys(bySeg).slice(0, 6);
  return (
    <Section title="Elasticity curves — price vs. conversion" subtitle="P(convert) falls as price rises (enforced monotone). Per top segment.">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {segs.map((s) => {
          const pts = bySeg[s].sort((a, b) => a.x - b.x);
          const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
          const x0 = Math.min(...xs), x1 = Math.max(...xs);
          const poly = pts.map((p) => `${((p.x - x0) / (x1 - x0 || 1)) * 100},${(1 - p.y) * 44 + 3}`).join(' ');
          return (
            <div key={s} className="rounded-xl border border-line p-3">
              <div className="text-[11px] font-semibold text-ink mb-1">SIC {s}</div>
              <svg viewBox="0 0 100 52" className="w-full h-16">
                <polyline points={poly} fill="none" stroke="#2563eb" strokeWidth="1.5" />
              </svg>
              <div className="flex justify-between text-[9px] text-mut"><span>-corridor</span><span>+corridor</span></div>
            </div>
          );
        })}
      </div>
    </Section>
  );
}

function FactorTable({ money }: { money: (v: any) => string }) {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => { api.optFactors().then((d) => setRows(d?.factors || [])).catch(() => setRows([])); }, []);
  if (!rows.length) return null;
  return (
    <Section title="Optimised factor table — the deploy artifact"
      subtitle="Per-segment factor within the corridor. Joins the existing rating-config / release rate-book path on deploy."
      actions={<Pill tone={rows.every((r) => r.within_corridor) ? 'green' : 'red'}>{rows.every((r) => r.within_corridor) ? 'all within corridor' : 'BREACH'}</Pill>}>
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead><tr className="text-[11px] uppercase tracking-wide text-mut border-b border-line">
            <th className="text-left py-1.5">Segment</th><th className="text-right">Policies</th>
            <th className="text-right">Factor</th><th className="text-right">GWP</th>
            <th className="text-right">Profit uplift</th><th className="text-center">Corridor</th>
          </tr></thead>
          <tbody>
            {rows.slice(0, 20).map((r, i) => (
              <tr key={i} className="border-b border-slate-50 hover:bg-slate-50">
                <td className="py-1.5 font-mono text-xs">SIC {r.segment}</td>
                <td className="text-right">{Number(r.policies).toLocaleString()}</td>
                <td className={`text-right font-semibold ${r.factor_pct > 0 ? 'text-emerald-600' : r.factor_pct < 0 ? 'text-red-600' : 'text-mut'}`}>{r.factor_pct > 0 ? '+' : ''}{r.factor_pct}%</td>
                <td className="text-right text-mut">{money(r.gwp_current)}</td>
                <td className="text-right font-medium">{money(r.profit_uplift)}</td>
                <td className="text-center">{r.within_corridor ? <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 inline" /> : <span className="text-red-600">✕</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

function ScenariosCard({ money }: { money: (v: any) => string }) {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => { api.optScenarios().then((d) => setRows(d?.scenarios || [])).catch(() => setRows([])); }, []);
  if (!rows.length) return null;
  return (
    <Section title="Scenario exploration"
      subtitle={`${rows.length} of N candidate price sets shown — N is a job parameter, not a licence tier.`}>
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead><tr className="text-[11px] uppercase tracking-wide text-mut border-b border-line">
            <th className="text-left py-1.5">Candidate</th><th className="text-right">Expected profit</th>
            <th className="text-right">Volume</th><th className="text-right">Loss ratio</th><th className="text-right">Avg factor</th>
          </tr></thead>
          <tbody>
            {rows.slice(0, 12).map((r, i) => (
              <tr key={i} className={`border-b border-slate-50 ${r.scenario_id === 'hold' ? 'bg-blue-50/40' : ''}`}>
                <td className="py-1.5 font-mono text-xs">{r.scenario_id}{r.scenario_id === 'hold' && <Pill tone="blue">baseline</Pill>}</td>
                <td className="text-right font-medium">{money(r.expected_profit)}</td>
                <td className="text-right text-mut">{Number(r.expected_volume).toLocaleString()}</td>
                <td className="text-right text-mut">{r.expected_loss_ratio != null ? `${(r.expected_loss_ratio * 100).toFixed(0)}%` : '—'}</td>
                <td className="text-right text-mut">{r.avg_factor}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

function MonitoringCard() {
  const [m, setM] = useState<any>(null);
  useEffect(() => { api.optMonitoring().then(setM).catch(() => setM(null)); }, []);
  const conv = m?.conversion || [];
  if (!conv.length) return null;
  return (
    <Section title="Monitoring — conversion + drift" subtitle="Actual conversion by month, month-over-month drift (the drift sentinel's signal).">
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead><tr className="text-[11px] uppercase tracking-wide text-mut border-b border-line">
            <th className="text-left py-1.5">Month</th><th className="text-right">Quotes</th>
            <th className="text-right">Conversion</th><th className="text-right">Drift MoM</th>
          </tr></thead>
          <tbody>
            {conv.slice(-8).map((r: any, i: number) => (
              <tr key={i} className="border-b border-slate-50">
                <td className="py-1.5">{String(r.month).slice(0, 7)}</td>
                <td className="text-right text-mut">{Number(r.quotes).toLocaleString()}</td>
                <td className="text-right">{(Number(r.actual_conversion) * 100).toFixed(1)}%</td>
                <td className={`text-right ${r.conversion_drift_mom > 0 ? 'text-emerald-600' : r.conversion_drift_mom < 0 ? 'text-red-600' : 'text-mut'}`}>
                  {r.conversion_drift_mom != null ? `${(Number(r.conversion_drift_mom) * 100).toFixed(1)}pp` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Prov>Moves with the rolling-month timeline — not a static snapshot. Feeds the drift sentinel + the fair-value evidence path.</Prov>
    </Section>
  );
}
