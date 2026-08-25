import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Target, ChevronDown, ChevronUp, ShieldCheck, Info, Cpu, Database,
         Layers, GitBranch, LineChart, ExternalLink, Play, Loader2, CheckCircle2,
         Activity, Zap, AlertTriangle, ScrollText, TrendingUp, Gauge, Bot } from 'lucide-react';
import { api } from '../lib/api';

// Price Optimisation — the motor offline spine (§3–§9, §13). Every surface reads
// a governed table the notebooks wrote; the numbers trace to open code and a
// versioned constraint YAML. Objective front door → efficient frontier →
// per-segment waterfall → approve-and-deploy (HITL, corridor enforced server-side),
// plus the demand curves, the two red-team validity panels, and live monitoring.

const gbp = (v: any, dp = 0) =>
  v === null || v === undefined ? '—' : `£${Number(v).toLocaleString('en-GB', { maximumFractionDigits: dp })}`;
const gbpM = (v: any) => (v === null || v === undefined ? '—' : `£${(Number(v) / 1e6).toFixed(2)}m`);
const pct = (v: any, dp = 1) => (v === null || v === undefined ? '—' : `${(Number(v) * 100).toFixed(dp)}%`);
const signPct = (v: any) => (v === null || v === undefined ? '—' : `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);

function Section({ title, icon, children, sub }: { title: string; icon?: ReactNode; children: ReactNode; sub?: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 mb-5">
      <div className="flex items-center gap-2 mb-1">{icon}<h3 className="font-semibold text-gray-900">{title}</h3></div>
      {sub && <p className="text-xs text-gray-500 mb-3">{sub}</p>}
      <div className={sub ? '' : 'mt-3'}>{children}</div>
    </div>
  );
}

function Kpi({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: 'good' | 'warn' }) {
  const c = tone === 'good' ? 'text-emerald-700' : tone === 'warn' ? 'text-amber-700' : 'text-gray-900';
  return (
    <div className="bg-gray-50 rounded-lg border border-gray-200 px-4 py-3">
      <div className="text-[11px] uppercase tracking-wide text-gray-500">{label}</div>
      <div className={`text-xl font-semibold ${c}`}>{value}</div>
      {hint && <div className="text-[11px] text-gray-500 mt-0.5">{hint}</div>}
    </div>
  );
}

function LinkChip({ href, children }: { href?: string | null; children: ReactNode }) {
  if (!href) return null;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
       className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700 hover:text-emerald-900 hover:underline bg-emerald-50 border border-emerald-200 rounded-full px-3 py-1">
      {children}<ExternalLink className="w-3 h-3" />
    </a>
  );
}

// --- tiny SVG chart helpers (no external libs) ------------------------------
function LineChartSvg({ series, w = 560, h = 200, xlab, ylab, yFmt }: {
  series: { name: string; color: string; pts: [number, number][] }[];
  w?: number; h?: number; xlab?: string; ylab?: string; yFmt?: (v: number) => string;
}) {
  const all = series.flatMap((s) => s.pts);
  if (!all.length) return <div className="text-sm text-gray-400">No data.</div>;
  const xs = all.map((p) => p[0]), ys = all.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const pad = 38, sx = (x: number) => pad + ((x - x0) / (x1 - x0 || 1)) * (w - pad - 12);
  const sy = (y: number) => h - 26 - ((y - y0) / (y1 - y0 || 1)) * (h - 26 - 12);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ maxHeight: h }}>
      <line x1={pad} y1={h - 26} x2={w - 12} y2={h - 26} stroke="#e5e7eb" />
      <line x1={pad} y1={12} x2={pad} y2={h - 26} stroke="#e5e7eb" />
      <text x={pad} y={h - 8} className="fill-gray-400" fontSize="10">{yFmt ? yFmt(y0) : x0.toFixed(2)}</text>
      <text x={w - 40} y={h - 8} className="fill-gray-400" fontSize="10">{x1.toFixed(2)}{xlab ? ` ${xlab}` : ''}</text>
      <text x={6} y={16} className="fill-gray-400" fontSize="10">{yFmt ? yFmt(y1) : y1.toFixed(2)}</text>
      {ylab && <text x={6} y={h - 30} className="fill-gray-400" fontSize="10">{ylab}</text>}
      {series.map((s) => (
        <polyline key={s.name} fill="none" stroke={s.color} strokeWidth={2}
          points={s.pts.map((p) => `${sx(p[0])},${sy(p[1])}`).join(' ')} />
      ))}
      {series.length > 1 && (
        <g>
          {series.map((s, i) => (
            <g key={s.name} transform={`translate(${pad + 8},${18 + i * 15})`}>
              <rect width="10" height="3" y="-3" fill={s.color} />
              <text x="14" y="1" fontSize="10" className="fill-gray-600">{s.name}</text>
            </g>
          ))}
        </g>
      )}
    </svg>
  );
}

export default function PriceOptimisation() {
  const [tab, setTab] = useState<'optimise' | 'decisions' | 'demand' | 'monitor' | 'act2' | 'heavy' | 'how'>('optimise');
  const [showHelp, setShowHelp] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [scen, setScen] = useState<any>(null);
  const [elast, setElast] = useState<any>(null);
  const [mon, setMon] = useState<any>(null);
  const [redteam, setRedteam] = useState<any>(null);
  const [fairness, setFairness] = useState<any>(null);
  const [decisions, setDecisions] = useState<any>(null);
  const [constraints, setConstraints] = useState<any>(null);
  const [assets, setAssets] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  // objective front door + live re-solve
  const [objective, setObjective] = useState('expected_profit');
  const [grid, setGrid] = useState(3000);
  const [run, setRun] = useState<{ state?: string; url?: string; error?: string } | null>(null);
  const [busy, setBusy] = useState(false);
  // HITL deploy
  const [deployMsg, setDeployMsg] = useState<{ ok?: boolean; text: string } | null>(null);
  const [segSel, setSegSel] = useState('');
  // closed-loop advance-month
  const [advBusy, setAdvBusy] = useState(false);
  const [advState, setAdvState] = useState<string | null>(null);
  const [advResult, setAdvResult] = useState<any>(null);

  const loadAll = () => {
    api.optimisationSummary().then(setSummary).catch((e) => setErr(String(e)));
    api.optScenarios().then(setScen).catch(() => {});
    api.optElasticity().then((d) => { setElast(d); if (d?.curves?.length) setSegSel((p) => p || d.curves[0].segment); }).catch(() => {});
    api.optMonitoring().then(setMon).catch(() => {});
    api.optRedteam().then(setRedteam).catch(() => {});
    api.optFairness().then(setFairness).catch(() => {});
    api.optDecisions().then(setDecisions).catch(() => {});
    api.optConstraints().then(setConstraints).catch(() => {});
    api.optAssets().then(setAssets).catch(() => {});
  };
  useEffect(loadAll, []);

  const factors: any[] = summary?.factors || [];
  const rollup = summary?.rollup;
  const meta = scen?.meta || summary?.scenario_meta;

  const doResolve = async () => {
    setBusy(true); setRun({ state: 'PENDING' });
    try {
      // Solver-only (full:false) — re-solves the factor table under the chosen
      // objective in ~1 min, safe for a live room. (The full data→elasticity→
      // simulation rebuild is the standalone `optimisation_full` job, run offline.)
      const r = await api.optRun({ objective, grid_points: grid, full: false });
      if (!r?.ok) { setRun({ error: r?.error || 'run failed' }); setBusy(false); return; }
      let polls = 0;
      const poll = async () => {
        if (++polls > 80) { setRun({ state: 'TIMEOUT', url: run?.url }); setBusy(false); return; }
        const s = await api.optRunStatus(r.run_id);
        setRun({ state: s.result_state || s.life_cycle_state, url: s.run_page_url });
        if (s.life_cycle_state && !['TERMINATED', 'SKIPPED', 'INTERNAL_ERROR'].includes(s.life_cycle_state)) {
          setTimeout(poll, 5000);
        } else { setBusy(false); loadAll(); }
      };
      setTimeout(poll, 5000);
    } catch (e) { setRun({ error: String(e) }); setBusy(false); }
  };

  const doAdvance = async () => {
    setAdvBusy(true); setAdvState('PENDING'); setAdvResult(null);
    try {
      const r = await api.optAdvance();
      if (!r?.ok) { setAdvState('error: ' + (r?.error || 'failed')); setAdvBusy(false); return; }
      let polls = 0;
      const poll = async () => {
        if (++polls > 80) { setAdvState('TIMEOUT'); setAdvBusy(false); return; }
        const s = await api.optRunStatus(r.run_id);
        setAdvState(s.result_state || s.life_cycle_state);
        if (s.life_cycle_state && !['TERMINATED', 'SKIPPED', 'INTERNAL_ERROR'].includes(s.life_cycle_state)) {
          setTimeout(poll, 5000);
        } else {
          setAdvBusy(false);
          api.optAdvanceResult().then(setAdvResult).catch(() => {});
          api.optMonitoring().then(setMon).catch(() => {});
        }
      };
      setTimeout(poll, 5000);
    } catch (e) { setAdvState('error: ' + String(e)); setAdvBusy(false); }
  };

  const doDeploy = async () => {
    setDeployMsg(null);
    const r = await api.optDeploy({ approver: 'app_user', note: `objective=${objective}` });
    setDeployMsg({ ok: r?.ok, text: r?.ok ? r.message : (r?.error || 'deploy failed') });
  };

  const TabBtn = ({ id, label }: { id: typeof tab; label: string }) => (
    <button onClick={() => setTab(id)}
      className={`px-4 py-2 text-sm font-medium rounded-md ${tab === id ? 'bg-white shadow text-gray-900' : 'text-gray-600 hover:text-gray-900'}`}>
      {label}
    </button>
  );

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-start justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Target className="w-6 h-6 text-emerald-600" /> Price Optimisation
          </h1>
          <p className="text-gray-600 mt-1">Personal motor · open code, versioned constraints, governed deploy — the offline spine.</p>
        </div>
        <button onClick={() => setShowHelp((v) => !v)} className="text-sm text-emerald-700 inline-flex items-center gap-1">
          <Info className="w-4 h-4" /> What am I seeing?{showHelp ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {showHelp && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-sm text-gray-700 mb-4 space-y-2">
          <p><b>The wedge against a black-box optimiser:</b> demand is a governed, monotone model; price enters as a
            ratio to the technically-correct (break-even) price, never raw; the solver is boring scipy bound by a
            constraint file you can open and <code>git log</code>; and nothing deploys without passing a corridor check
            server-side. Turn the objective, run the real governed DAG, watch the whole book move, then approve.</p>
          <p className="text-xs text-emerald-800"><b>About this demo:</b> synthetic, illustrative motor data in a
            Databricks sandbox — it demonstrates the end-to-end capability, not a real book.</p>
        </div>
      )}

      <div className="bg-gray-100 rounded-lg p-1 inline-flex gap-1 mb-5">
        <TabBtn id="optimise" label="Optimiser" />
        <TabBtn id="decisions" label="Decisions" />
        <TabBtn id="demand" label="Demand & red-team" />
        <TabBtn id="monitor" label="Monitoring" />
        <TabBtn id="act2" label="Aggregator squeeze" />
        <TabBtn id="heavy" label="Heavy mode" />
        <TabBtn id="how" label="How it works" />
      </div>

      {err && <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm mb-4">{err}</div>}
      {summary && !summary.available && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-lg p-4 text-sm mb-4">
          {summary.message || 'Optimisation not solved yet on this workspace.'}
        </div>
      )}

      {/* ------------------------------------------------------- OPTIMISER */}
      {tab === 'optimise' && summary?.available && (
        <>
          <Section title="Objective front door" icon={<Gauge className="w-4 h-4 text-emerald-600" />}
            sub="Pick what the book should maximise and how many candidate price sets to explore, then run the real governed DAG (data → elasticity → simulate → solve → monitor). The solver is bound by the versioned constraint set.">
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <div className="text-xs text-gray-500 mb-1">Objective</div>
                <div className="inline-flex rounded-md border border-gray-200 overflow-hidden">
                  {[['expected_profit', 'Expected profit'], ['expected_gwp', 'Expected GWP'], ['retention_weighted_profit', 'Retention-weighted']].map(([v, l]) => (
                    <button key={v} onClick={() => setObjective(v)}
                      className={`px-3 py-1.5 text-sm ${objective === v ? 'bg-emerald-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'}`}>{l}</button>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Candidate price sets (N)</div>
                <select value={grid} onChange={(e) => setGrid(Number(e.target.value))}
                  className="border border-gray-200 rounded-md px-3 py-1.5 text-sm">
                  <option value={1000}>1,000</option><option value={3000}>3,000</option><option value={10000}>10,000</option>
                </select>
              </div>
              <button onClick={doResolve} disabled={busy}
                className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white text-sm font-medium rounded-md px-4 py-2">
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {busy ? 'Running governed DAG…' : 'Re-solve (live job)'}
              </button>
              {run?.state && <span className="text-xs text-gray-500">run: <b>{run.state}</b>{run.url && <> · <a className="text-emerald-700 underline" href={run.url} target="_blank" rel="noreferrer">open</a></>}</span>}
              {run?.error && <span className="text-xs text-red-600">{run.error}</span>}
            </div>
            {meta && (
              <p className="text-xs text-gray-500 mt-3">
                <b>{Number(meta.grid_points || meta.candidates || 0).toLocaleString()}</b> candidate price sets evaluated in
                <b> {Number(meta.wallclock_s || 0).toFixed(1)}s</b> — N is your choice, not a licence tier.
              </p>
            )}
          </Section>

          {rollup && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
              <Kpi label="Expected profit (opt)" value={gbpM(rollup.expected_profit_opt)} hint={`hold ${gbpM(rollup.expected_profit_hold)}`} tone="good" />
              <Kpi label="Profit uplift" value={gbpM(rollup.profit_uplift)} hint={signPct(rollup.profit_uplift_pct)} tone="good" />
              <Kpi label="Book" value={`${Number(rollup.policies).toLocaleString()}`} hint={`${rollup.segments} segments · ${gbpM(rollup.gwp_current)} GWP`} />
              <Kpi label="Constraint corridor" value={rollup.all_within_corridor ? 'All within' : 'Breach!'}
                hint={`policy set ${summary?.constraint?.version || 'v1'}`} tone={rollup.all_within_corridor ? 'good' : 'warn'} />
            </div>
          )}

          <Section title="Efficient frontier" icon={<TrendingUp className="w-4 h-4 text-emerald-600" />}
            sub="Every Pareto-optimal candidate (expected volume vs expected profit). Hold = today's book. The solver picks the objective-optimal point within the constraint corridor.">
            <FrontierChart frontier={scen?.frontier || []} />
          </Section>

          <Section title="Per-segment decision (waterfall)" icon={<Layers className="w-4 h-4 text-emerald-600" />}
            sub="What the solver did to each age·vehicle segment and why it stopped there (interior optimum, segment cap, or corridor edge).">
            <Waterfall factors={factors} />
          </Section>

          <Section title="Solved factor table" icon={<ScrollText className="w-4 h-4 text-emerald-600" />}
            sub="The deployable artifact — the per-segment factor the rating config consumes.">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-gray-500 border-b">
                  <th className="py-1.5 pr-3">Segment</th><th className="pr-3">Policies</th><th className="pr-3">Factor</th>
                  <th className="pr-3">Conv hold→opt</th><th className="pr-3">Profit uplift</th><th className="pr-3">Binding</th><th>Corridor</th>
                </tr></thead>
                <tbody>
                  {factors.map((f) => (
                    <tr key={f.segment} className="border-b border-gray-100">
                      <td className="py-1.5 pr-3 font-medium text-gray-800">{f.segment}</td>
                      <td className="pr-3">{Number(f.policies).toLocaleString()}</td>
                      <td className={`pr-3 font-medium ${f.factor_pct >= 0 ? 'text-emerald-700' : 'text-amber-700'}`}>{signPct(f.factor_pct)}</td>
                      <td className="pr-3 text-gray-600">{pct(f.conversion_hold, 0)} → {pct(f.conversion_opt, 0)}</td>
                      <td className="pr-3">{gbp(f.profit_uplift)}</td>
                      <td className="pr-3"><span className="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">{f.binding}</span></td>
                      <td>{f.within_corridor ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <AlertTriangle className="w-4 h-4 text-amber-600" />}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>

          <Section title="Approve → deploy" icon={<ShieldCheck className="w-4 h-4 text-emerald-600" />}
            sub="The human sets policy; the gate enforces it. On approve, the corridor is re-checked SERVER-SIDE (a future agent cannot bypass it), then the factor set is stamped to optimisation_deployment + the immutable audit log.">
            <div className="flex items-center gap-3 flex-wrap">
              <button onClick={doDeploy}
                className="inline-flex items-center gap-2 bg-gray-900 hover:bg-black text-white text-sm font-medium rounded-md px-4 py-2">
                <CheckCircle2 className="w-4 h-4" /> Approve &amp; deploy factor set {summary?.constraint?.version || 'v1'}
              </button>
              {deployMsg && (
                <span className={`text-sm ${deployMsg.ok ? 'text-emerald-700' : 'text-amber-700'}`}>
                  {deployMsg.ok ? <CheckCircle2 className="w-4 h-4 inline mr-1" /> : <AlertTriangle className="w-4 h-4 inline mr-1" />}
                  {deployMsg.text}
                </span>
              )}
            </div>
          </Section>

          <ExplainPrice />
        </>
      )}

      {/* -------------------------------------------------- DEMAND & RED-TEAM */}
      {tab === 'demand' && (
        <>
          <Section title="Elasticity curves (monotone demand)" icon={<LineChart className="w-4 h-4 text-emerald-600" />}
            sub="Per-segment price→conversion, read off the governed conversion_elasticity_motor champion. Monotonicity in price is ENFORCED (monotone_constraints) — conversion can only fall as price rises, so the solver can't exploit a spurious wrinkle.">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs text-gray-500">Segment</span>
              <select value={segSel} onChange={(e) => setSegSel(e.target.value)} className="border border-gray-200 rounded-md px-3 py-1.5 text-sm">
                {[...new Set((elast?.curves || []).map((c: any) => c.segment))].map((s: any) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <LineChartSvg xlab="× price" ylab="P(convert)" yFmt={(v) => `${(v * 100).toFixed(0)}%`}
              series={[{ name: 'conversion', color: '#059669',
                pts: (elast?.curves || []).filter((c: any) => c.segment === segSel).map((c: any) => [c.price_multiplier, c.conversion_prob]) }]} />
          </Section>

          <Section title="Red-team A — why raw price gives the WRONG elasticity" icon={<AlertTriangle className="w-4 h-4 text-amber-600" />}
            sub="Naive model: conversion ~ raw price. Correct model: conversion ~ price ÷ technical. Expensive risks carry a high price AND a high market benchmark, so raw price barely tracks competitiveness — the naive model reads demand as nearly price-insensitive. That's the dangerous, over-flat elasticity a black box can hide.">
            <LineChartSvg xlab="% price" ylab="P(convert)" yFmt={(v) => `${(v * 100).toFixed(0)}%`}
              series={[
                { name: 'naive (raw price)', color: '#d97706', pts: (redteam?.endogeneity || []).map((r: any) => [r.price_change_pct, r.naive_rawprice_conversion]) },
                { name: 'correct (÷ technical)', color: '#059669', pts: (redteam?.endogeneity || []).map((r: any) => [r.price_change_pct, r.correct_vs_technical_conversion]) },
              ]} />
            <EndoHeadline rows={redteam?.endogeneity || []} />
          </Section>

          <Section title="Red-team B — parameter recovery" icon={<CheckCircle2 className="w-4 h-4 text-emerald-600" />}
            sub="The generator injected a known month-by-month elasticity; the pipeline should recover it. True vs recovered slope, per month — the standard 'get back what you put in' validity check on synthetic data.">
            <LineChartSvg xlab="month" ylab="slope"
              series={[
                { name: 'true (injected)', color: '#6b7280', pts: (redteam?.param_recovery || []).map((r: any) => [r.month_idx, r.true_slope]) },
                { name: 'recovered (fit)', color: '#059669', pts: (redteam?.param_recovery || []).map((r: any) => [r.month_idx, r.recovered_slope]) },
              ]} />
          </Section>
        </>
      )}

      {/* -------------------------------------------------------- MONITORING */}
      {tab === 'monitor' && (
        <>
          <Section title="Did it work? — advance the month" icon={<Zap className="w-4 h-4 text-emerald-600" />}
            sub="Close the loop live: roll the synthetic book forward one month under the prices you just deployed, then compare what the solver predicted to what the book realized.">
            <div className="flex items-center gap-3 flex-wrap">
              <button onClick={doAdvance} disabled={advBusy}
                className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white text-sm font-medium rounded-md px-4 py-2">
                {advBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {advBusy ? 'Advancing the month…' : 'Advance one month'}
              </button>
              {advState && <span className="text-xs text-gray-500">run: <b>{advState}</b></span>}
              {advResult?.rollup && (
                <div className="flex gap-3 flex-wrap">
                  <Kpi label="Predicted profit" value={gbpM(advResult.rollup.predicted_profit)} />
                  <Kpi label="Realized profit" value={gbpM(advResult.rollup.realized_profit)} tone="good"
                    hint={advResult.rollup.delta_pct != null ? `${signPct(advResult.rollup.delta_pct)} vs predicted` : undefined} />
                  <Kpi label="Advanced to" value={String(advResult.rollup.advanced_month || '—')} />
                </div>
              )}
            </div>
            {advResult?.segments?.length > 0 && (
              <div className="overflow-x-auto mt-3">
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-gray-500 border-b">
                    <th className="py-1.5 pr-3">Segment</th><th className="pr-3">Factor</th>
                    <th className="pr-3">Conv pred→real</th><th className="pr-3">Profit pred</th>
                    <th className="pr-3">Profit real</th><th>Δ</th>
                  </tr></thead>
                  <tbody>
                    {advResult.segments.map((s: any) => (
                      <tr key={s.segment} className="border-b border-gray-100">
                        <td className="py-1.5 pr-3 font-medium text-gray-800">{s.segment}</td>
                        <td className="pr-3">{signPct(s.factor != null ? (s.factor - 1) * 100 : null)}</td>
                        <td className="pr-3 text-gray-600">{pct(s.predicted_conversion, 0)} → {pct(s.realized_conversion, 0)}</td>
                        <td className="pr-3">{gbp(s.predicted_profit)}</td>
                        <td className="pr-3">{gbp(s.realized_profit)}</td>
                        <td className={s.profit_delta_pct >= 0 ? 'text-emerald-700' : 'text-amber-700'}>{signPct(s.profit_delta_pct)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          <Section title="Conversion drift" icon={<Activity className="w-4 h-4 text-emerald-600" />}
            sub="Actual vs model-expected conversion over the rolling months — the elasticity-drift sentinel's signal. Small, moving drift = a calibrated model that still needs watching.">
            <LineChartSvg xlab="month idx" ylab="P(convert)" yFmt={(v) => `${(v * 100).toFixed(0)}%`}
              series={[
                { name: 'actual', color: '#059669', pts: (mon?.months || []).map((m: any, i: number) => [i, m.actual_conversion]) },
                { name: 'expected', color: '#6b7280', pts: (mon?.months || []).map((m: any, i: number) => [i, m.expected_conversion]) },
              ]} />
          </Section>

          <Section title="Deviation from the technical price" icon={<Gauge className="w-4 h-4 text-emerald-600" />}
            sub="Distribution of price ÷ technically-correct price across the book. Bands outside the ±15% corridor are flagged.">
            <DeviationBars rows={mon?.deviation || []} />
          </Section>

          <Section title="Constraint & fair-value tile" icon={<ShieldCheck className="w-4 h-4 text-emerald-600" />}
            sub="Corridor breaches and the UK GIPP check (renewal never above equivalent new business).">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {(mon?.breaches || []).map((b: any) => (
                <div key={b.check} className="bg-gray-50 rounded-lg border border-gray-200 p-3">
                  <div className="text-xs text-gray-500">{b.note}</div>
                  <div className="text-lg font-semibold text-gray-900">{pct(b.rate)}</div>
                  <div className="text-[11px] text-gray-500">{Number(b.breaches).toLocaleString()} / {Number(b.total).toLocaleString()}</div>
                </div>
              ))}
            </div>
          </Section>

          <Section title="Fair-value evidence (§11)" icon={<ShieldCheck className="w-4 h-4 text-emerald-600" />}
            sub="Generated on every solve, before deploy: proxy-correlation of the price factor with forbidden signals, disparate impact across protected groups, and a vulnerability screen. This is the pack a Consumer-Duty / GIPP review asks for.">
            {fairness?.summary && (
              <div className={`rounded-lg border p-3 mb-3 text-sm ${fairness.summary.overall_pass ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-amber-50 border-amber-200 text-amber-900'}`}>
                <b>{fairness.summary.overall_pass ? 'PASS' : 'REVIEW'}</b> · worst proxy-correlation {Number(fairness.summary.worst_proxy_corr).toFixed(2)} vs 0.35 ceiling. {fairness.summary.evidence}
              </div>
            )}
            {fairness?.checks?.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-gray-500 border-b">
                    <th className="py-1.5 pr-3">Check</th><th className="pr-3">Dimension</th><th className="pr-3">Group</th>
                    <th className="pr-3">Value</th><th className="pr-3">Threshold</th><th>Result</th>
                  </tr></thead>
                  <tbody>
                    {fairness.checks.map((c: any, i: number) => (
                      <tr key={i} className="border-b border-gray-100">
                        <td className="py-1.5 pr-3 text-gray-700">{c.check}</td>
                        <td className="pr-3 text-gray-600">{c.dimension}</td>
                        <td className="pr-3 text-gray-600">{c.group}</td>
                        <td className="pr-3">{Number(c.value).toFixed(3)}</td>
                        <td className="pr-3 text-gray-500">{Number(c.threshold).toFixed(2)}</td>
                        <td>{c.pass ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <AlertTriangle className="w-4 h-4 text-amber-600" />}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>
        </>
      )}

      {/* ------------------------------------------------------------ DECISIONS */}
      {tab === 'decisions' && <DecisionRecords records={decisions?.records || []} available={decisions?.available} />}

      {/* ------------------------------------------------- ACT 2 (aggregator) */}
      {tab === 'act2' && <AggregatorSqueeze />}

      {/* --------------------------------------------------------- HEAVY MODE */}
      {tab === 'heavy' && <HeavyMode />}

      {/* --------------------------------------------------------- HOW IT WORKS */}
      {tab === 'how' && (
        <>
          <Section title="The governed loop" icon={<GitBranch className="w-4 h-4 text-emerald-600" />}>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              {['Quote & renewal data', 'Monotone elasticity', 'Simulation (N sets)', 'Constrained solver', 'Factor table', 'Monitoring'].map((s, i, a) => (
                <span key={s} className="inline-flex items-center gap-2">
                  <span className="bg-emerald-50 border border-emerald-200 rounded-full px-3 py-1 text-emerald-800">{s}</span>
                  {i < a.length - 1 && <span className="text-gray-300">→</span>}
                </span>
              ))}
            </div>
          </Section>

          <Section title="The constraint set IS the pricing policy" icon={<ScrollText className="w-4 h-4 text-emerald-600" />}
            sub="Versioned in the repo; the solver is bound by it; its git history is the auditable record of how the policy evolved. Open it live in the room.">
            {constraints?.available
              ? <pre className="bg-gray-900 text-gray-100 text-[11px] rounded-lg p-3 overflow-x-auto max-h-96">{constraints.yaml}</pre>
              : <p className="text-sm text-gray-400">Constraint file not reachable in this workspace.</p>}
          </Section>

          <Section title="Open the real assets" icon={<Database className="w-4 h-4 text-emerald-600" />}>
            <div className="flex flex-wrap gap-2">
              {assets?.tables && Object.entries(assets.tables).map(([t, u]: any) => <LinkChip key={t} href={u}>{t}</LinkChip>)}
              {assets?.models && Object.entries(assets.models).map(([m, u]: any) => <LinkChip key={m} href={u}>{m}</LinkChip>)}
              <LinkChip href={assets?.notebook_url}>solver notebook</LinkChip>
              <LinkChip href={assets?.job_url}>governed job</LinkChip>
              <LinkChip href={assets?.agent_url}>rate-change agent</LinkChip>
            </div>
          </Section>

          <Section title="Agent-callable — one MCP surface (Principle 8)" icon={<Bot className="w-4 h-4 text-emerald-600" />}
            sub="Every stage and read is a tool on the same MCP server the app and notebooks use — an external agent can drive the whole loop. The deploy tool stays gated server-side (RBAC + corridor); no prompt bypasses it.">
            <div className="flex flex-wrap gap-2">
              {['opt_run_simulation', 'opt_run_solver', 'opt_run_fairness', 'opt_advance_month',
                'opt_deploy_factors ⛨', 'opt_read_scenarios', 'opt_read_factors', 'opt_read_monitoring',
                'opt_read_fairness', 'opt_read_constraints'].map((t) => (
                <span key={t} className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-700 bg-gray-100 border border-gray-200 rounded-full px-3 py-1 font-mono">{t}</span>
              ))}
            </div>
          </Section>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Section title="Data" icon={<Database className="w-4 h-4 text-gray-500" />}>
              <p className="text-sm text-gray-600">Motor quote-response + renewal events manufactured on the real risk models, with injected price variation and month-over-month elasticity drift so demand is learnable and monitoring moves.</p>
            </Section>
            <Section title="Model & method" icon={<Cpu className="w-4 h-4 text-gray-500" />}>
              <p className="text-sm text-gray-600">Monotone LightGBM conversion + retention (price as a ratio to technical, never raw). scipy solver, arg-max within the corridor ∩ segment caps. Everything open code.</p>
            </Section>
            <Section title="Platform" icon={<Zap className="w-4 h-4 text-gray-500" />}>
              <p className="text-sm text-gray-600">Serverless jobs (scale-to-zero), UC-governed tables + registered @champion models, run-now via the app service principal (no PAT), immutable audit log.</p>
            </Section>
          </div>
        </>
      )}
    </div>
  );
}

// --- frontier scatter -------------------------------------------------------
function FrontierChart({ frontier }: { frontier: any[] }) {
  if (!frontier.length) return <div className="text-sm text-gray-400">Run the simulation to see the frontier.</div>;
  const w = 560, h = 240, pad = 44;
  const xs = frontier.map((f) => Number(f.expected_volume)), ys = frontier.map((f) => Number(f.expected_profit));
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const sx = (x: number) => pad + ((x - x0) / (x1 - x0 || 1)) * (w - pad - 12);
  const sy = (y: number) => h - 28 - ((y - y0) / (y1 - y0 || 1)) * (h - 28 - 12);
  const line = frontier.filter((f) => f.scenario_id !== 'hold').sort((a, b) => a.expected_volume - b.expected_volume);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ maxHeight: h }}>
      <line x1={pad} y1={h - 28} x2={w - 12} y2={h - 28} stroke="#e5e7eb" />
      <line x1={pad} y1={12} x2={pad} y2={h - 28} stroke="#e5e7eb" />
      <text x={pad} y={h - 10} fontSize="10" className="fill-gray-400">expected volume →</text>
      <text x={6} y={16} fontSize="10" className="fill-gray-400">profit ↑</text>
      <polyline fill="none" stroke="#a7f3d0" strokeWidth={2} points={line.map((f) => `${sx(f.expected_volume)},${sy(f.expected_profit)}`).join(' ')} />
      {frontier.map((f) => {
        const hold = f.scenario_id === 'hold';
        return <circle key={f.scenario_id} cx={sx(f.expected_volume)} cy={sy(f.expected_profit)} r={hold ? 5 : 3}
          fill={hold ? '#111827' : '#059669'} />;
      })}
      <text x={sx(frontier.find((f) => f.scenario_id === 'hold')?.expected_volume ?? x0) + 7}
            y={sy(frontier.find((f) => f.scenario_id === 'hold')?.expected_profit ?? y0)} fontSize="10" className="fill-gray-700">hold</text>
    </svg>
  );
}

// --- per-segment waterfall --------------------------------------------------
function Waterfall({ factors }: { factors: any[] }) {
  if (!factors.length) return <div className="text-sm text-gray-400">No solved factors.</div>;
  const max = Math.max(...factors.map((f) => Math.abs(Number(f.factor_pct))), 1);
  return (
    <div className="space-y-1.5">
      {factors.map((f) => {
        const up = Number(f.factor_pct) >= 0;
        const wpc = (Math.abs(Number(f.factor_pct)) / max) * 46;
        return (
          <div key={f.segment} className="flex items-center gap-2 text-xs">
            <div className="w-28 text-gray-700 truncate">{f.segment}</div>
            <div className="flex-1 flex items-center">
              <div className="w-1/2 flex justify-end">{!up && <div className="h-4 rounded-l bg-amber-400" style={{ width: `${wpc}%` }} />}</div>
              <div className="w-px h-5 bg-gray-300" />
              <div className="w-1/2">{up && <div className="h-4 rounded-r bg-emerald-500" style={{ width: `${wpc}%` }} />}</div>
            </div>
            <div className={`w-14 text-right font-medium ${up ? 'text-emerald-700' : 'text-amber-700'}`}>{signPct(f.factor_pct)}</div>
            <div className="w-24 text-right text-gray-500">{gbp(f.profit_uplift)}</div>
            <div className="w-24 text-[11px] text-gray-400">{f.binding}</div>
          </div>
        );
      })}
    </div>
  );
}

function EndoHeadline({ rows }: { rows: any[] }) {
  if (!rows.length) return null;
  const base = rows.find((r) => Number(r.price_change_pct) === 0);
  const hi = rows.find((r) => Math.abs(Number(r.price_change_pct) - 10) < 0.01);
  if (!base || !hi) return null;
  const naive = (Number(base.naive_rawprice_conversion) - Number(hi.naive_rawprice_conversion)) * 100;
  const correct = (Number(base.correct_vs_technical_conversion) - Number(hi.correct_vs_technical_conversion)) * 100;
  return (
    <p className="text-xs text-gray-600 mt-2">
      At <b>+10%</b> price: the naive raw-price model predicts only a <b>{naive.toFixed(1)}pp</b> conversion drop;
      the correct ratio model predicts <b>{correct.toFixed(1)}pp</b>. Price the book on the naive model and you'd
      systematically over-raise.
    </p>
  );
}

// --- Explain-this-price (§11): decompose any quote, plain-language ----------
function ExplainPrice() {
  const [qid, setQid] = useState('');
  const [dec, setDec] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [plain, setPlain] = useState<{ busy?: boolean; text?: string } | null>(null);

  const run = async (id?: string) => {
    const q = (id ?? qid).trim(); if (!q) return;
    setBusy(true); setDec(null); setPlain(null);
    try { const r = await api.optExplain(q); setDec(r); } finally { setBusy(false); }
  };
  const loadGrandma = async () => {
    const r = await api.optExplainDemo(); if (r?.quote_id) { setQid(r.quote_id); run(r.quote_id); }
  };
  const explainPlain = async () => {
    if (!dec?.quote_id) return;
    setPlain({ busy: true });
    try { const r = await api.agentLead({ persona: 'price_explainer', question: `Explain the price for quote ${dec.quote_id} in plain language.` });
      setPlain({ text: r?.answer || r?.error || '(no answer)' }); }
    catch (e) { setPlain({ text: String(e) }); }
  };
  const d = dec?.decomposition;
  return (
    <Section title="Explain this price" icon={<ScrollText className="w-4 h-4 text-emerald-600" />}
      sub="Decompose any quote into technical price + optimisation factor + corridor clamp — the governed explain_price function. The closing beat: 'here's exactly why this grandma pays what she pays.'">
      <div className="flex items-center gap-2 flex-wrap mb-3">
        <input value={qid} onChange={(e) => setQid(e.target.value)} placeholder="quote id (e.g. MQ-000…)"
          className="border border-gray-200 rounded-md px-3 py-1.5 text-sm font-mono w-64" />
        <button onClick={() => run()} disabled={busy}
          className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white text-sm font-medium rounded-md px-3 py-1.5">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Info className="w-4 h-4" />} Explain
        </button>
        <button onClick={loadGrandma} className="text-sm text-emerald-700 hover:underline">use the grandma-in-a-BMW demo case</button>
      </div>
      {dec && dec.available === false && <div className="text-sm text-amber-700">Quote not found.</div>}
      {d && (
        <div className="text-sm text-gray-700 space-y-1 bg-gray-50 border border-gray-200 rounded-lg p-3">
          <div><b>{d.quote_id}</b> · segment <b>{d.segment}</b> (age {d.driver_age}, vehicle group {d.vehicle_group})</div>
          <div>Technical (risk) price {gbp(d.technical_premium)} → +{d.expense_commission_loading_pct}% expense/commission → break-even {gbp(d.loaded_premium)}</div>
          <div>Optimisation factor <b>{signPct(d.optimisation_factor_pct)}</b> ({d.factor_binding}) → indicated {gbp(d.indicated_after_factor)}</div>
          <div>Offered {gbp(d.offered_premium)} · vs-technical {Number(d.vs_technical).toFixed(2)} · corridor clamp: <b>{d.corridor_clamped ? 'yes' : 'no'}</b> ({d.corridor})</div>
          <div className="text-[11px] text-gray-500">{d.models}</div>
          <div className="pt-1">
            <button onClick={explainPlain} disabled={plain?.busy}
              className="inline-flex items-center gap-2 bg-gray-900 hover:bg-black disabled:opacity-60 text-white text-xs font-medium rounded-md px-3 py-1.5">
              {plain?.busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Bot className="w-3.5 h-3.5" />} Explain in plain language
            </button>
            {plain?.text && <div className="mt-2 text-xs text-gray-700 bg-white border border-gray-200 rounded-lg p-3 whitespace-pre-wrap">{plain.text}</div>}
          </div>
        </div>
      )}
    </Section>
  );
}

// --- Heavy mode (§11a): the big-hammer second gear --------------------------
function HeavyMode() {
  const [dis, setDis] = useState<any>(null);
  const [stoch, setStoch] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [run, setRun] = useState<string | null>(null);
  const load = () => {
    api.optHeavyDisagreement().then(setDis).catch(() => {});
    api.optHeavyStochastic().then(setStoch).catch(() => {});
  };
  useEffect(load, []);
  const go = async (preset: string) => {
    setBusy(preset); setRun('PENDING');
    try {
      const r = await api.optHeavyRun({ preset });
      if (!r?.ok) { setRun('error: ' + (r?.error || 'failed')); setBusy(null); return; }
      let n = 0;
      const poll = async () => {
        if (++n > 100) { setRun('TIMEOUT'); setBusy(null); return; }
        const s = await api.optRunStatus(r.run_id);
        setRun(s.result_state || s.life_cycle_state);
        if (s.life_cycle_state && !['TERMINATED', 'SKIPPED', 'INTERNAL_ERROR'].includes(s.life_cycle_state)) setTimeout(poll, 6000);
        else { setBusy(null); load(); }
      };
      setTimeout(poll, 6000);
    } catch (e) { setRun(String(e)); setBusy(null); }
  };
  const meta = stoch?.meta;
  const disRows: any[] = dis?.segments || [];
  const cands: any[] = stoch?.candidates || [];

  return (
    <div>
      <div className="bg-slate-900 text-gray-100 rounded-lg p-4 text-sm mb-4">
        <b>The second gear.</b> The default optimiser is deliberately light. Heavy mode is what you run
        <b> because you can</b>: refit demand as an ensemble of candidate models and re-solve under each, and
        score the whole book per-policy with Monte-Carlo demand draws for the full risk distribution.
        <span className="text-emerald-300"> Smart when you can, exhaustive when it matters — the appliance has one gear.</span>
      </div>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <button onClick={() => go('live')} disabled={!!busy}
          className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white text-sm font-medium rounded-md px-4 py-2">
          {busy === 'live' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />} Re-run live (small)
        </button>
        <button onClick={() => go('default')} disabled={!!busy}
          className="inline-flex items-center gap-2 bg-gray-900 hover:bg-black disabled:opacity-60 text-white text-sm font-medium rounded-md px-4 py-2">
          {busy === 'default' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />} Full heavy run
        </button>
        {run && <span className="text-xs text-gray-500">run: <b>{run}</b></span>}
      </div>

      {meta && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-sm text-gray-800 mb-4">
          <b>Measured, not claimed:</b> {Number(meta.total_evaluations).toLocaleString()} evaluations
          ({Number(meta.policies).toLocaleString()} policies × {meta.grid_points} price sets × {meta.n_draws} draws,
          {meta.n_models} demand models) in <b>{meta.wallclock_s}s</b> · ~<b>${meta.est_cost_usd}</b> compute (est.) · preset <b>{meta.preset}</b>.
          <span className="text-gray-500"> Now ask an appliance to show you the distribution across your candidate models.</span>
        </div>
      )}

      <Section title="Ensemble disagreement map" icon={<Layers className="w-4 h-4 text-emerald-600" />}
        sub="Per-segment factor spread across the candidate demand models. Tight = high decision confidence; wide = treat the factor as uncertain (widen corridor or hold).">
        {disRows.length ? (
          <div className="space-y-1.5">
            {disRows.map((d) => {
              const wpc = Math.min(100, Number(d.factor_spread_pp) * 4);
              const good = Number(d.agreement) >= 0.7;
              return (
                <div key={d.segment} className="flex items-center gap-2 text-xs">
                  <div className="w-28 text-gray-700 truncate">{d.segment}</div>
                  <div className="flex-1 h-4 bg-gray-100 rounded"><div className={`h-4 rounded ${good ? 'bg-emerald-500' : 'bg-amber-400'}`} style={{ width: `${wpc}%` }} /></div>
                  <div className="w-40 text-right text-gray-500">spread {Number(d.factor_spread_pp).toFixed(1)}pp · agree {Number(d.agreement).toFixed(2)} · {d.n_models} models</div>
                </div>
              );
            })}
          </div>
        ) : <div className="text-sm text-gray-400">Run heavy mode to build the disagreement map.</div>}
      </Section>

      <Section title="Uncertainty-banded frontier" icon={<TrendingUp className="w-4 h-4 text-emerald-600" />}
        sub="Per-candidate expected profit with its P5–P95 band from the Monte-Carlo draws — not a point estimate. Hold baseline marked.">
        {cands.length ? <StochFrontier cands={cands} /> : <div className="text-sm text-gray-400">Run heavy mode to see the distribution.</div>}
      </Section>
    </div>
  );
}

function StochFrontier({ cands }: { cands: any[] }) {
  const w = 560, h = 260, pad = 46;
  const xs = cands.map((c) => Number(c.mean_volume)), lo = cands.map((c) => Number(c.p5_profit)), hi = cands.map((c) => Number(c.p95_profit));
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...lo), y1 = Math.max(...hi);
  const sx = (x: number) => pad + ((x - x0) / (x1 - x0 || 1)) * (w - pad - 12);
  const sy = (y: number) => h - 28 - ((y - y0) / (y1 - y0 || 1)) * (h - 28 - 12);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ maxHeight: h }}>
      <line x1={pad} y1={h - 28} x2={w - 12} y2={h - 28} stroke="#e5e7eb" />
      <line x1={pad} y1={12} x2={pad} y2={h - 28} stroke="#e5e7eb" />
      <text x={pad} y={h - 10} fontSize="10" className="fill-gray-400">expected volume →</text>
      <text x={6} y={16} fontSize="10" className="fill-gray-400">profit (P5–P95) ↑</text>
      {cands.map((c) => {
        const hold = c.candidate_id === 'hold'; const x = sx(Number(c.mean_volume));
        return (
          <g key={c.candidate_id}>
            <line x1={x} y1={sy(Number(c.p5_profit))} x2={x} y2={sy(Number(c.p95_profit))} stroke={hold ? '#111827' : '#a7f3d0'} strokeWidth={hold ? 2 : 1.5} />
            <circle cx={x} cy={sy(Number(c.mean_profit))} r={hold ? 5 : 2.5} fill={hold ? '#111827' : '#059669'} />
          </g>
        );
      })}
    </svg>
  );
}

// --- Decision records (§11): immutable, reproducible deploy records ---------
function DecisionRecords({ records, available }: { records: any[]; available?: boolean }) {
  const [open, setOpen] = useState<string | null>(records[0]?.decision_id || null);
  const [paper, setPaper] = useState<Record<string, { busy?: boolean; text?: string }>>({});
  const jparse = (s: any) => { try { return JSON.parse(s); } catch { return null; } };

  const draftPaper = async (rec: any) => {
    setPaper((p) => ({ ...p, [rec.decision_id]: { busy: true } }));
    try {
      const r = await api.agentLead({ persona: 'committee_scribe', question:
        `Draft the pricing-committee paper for decision record ${rec.decision_id} (deployment ${rec.deployment_id}). Use the decision record's chosen scenario, rejected alternatives, fairness evidence and monitoring plan.` });
      setPaper((p) => ({ ...p, [rec.decision_id]: { text: r?.answer || r?.error || '(no answer)' } }));
    } catch (e) { setPaper((p) => ({ ...p, [rec.decision_id]: { text: String(e) } })); }
  };

  if (available === false || !records.length) {
    return <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-lg p-4 text-sm">
      No decision records yet — deploy a factor set (Optimiser → Approve &amp; deploy) or run the decision-record job.</div>;
  }
  return (
    <div>
      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-sm text-gray-700 mb-4">
        <b>Every deployment leaves an immutable, reproducible record.</b> Data snapshot, elasticity model
        versions, constraint version, the chosen scenario <b>and the alternatives we passed on</b>, the
        fairness review, approver + time, and a pointer to re-run the exact solve. This is what a regulator
        or an internal audit asks to see.
      </div>
      {records.map((r) => {
        const chosen = jparse(r.chosen_json) || {}; const rej = jparse(r.rejected_json) || [];
        const facs = jparse(r.factors_json) || []; const isOpen = open === r.decision_id;
        const pp = paper[r.decision_id];
        return (
          <div key={r.decision_id} className="bg-white rounded-lg border border-gray-200 mb-3">
            <button onClick={() => setOpen(isOpen ? null : r.decision_id)}
              className="w-full flex items-center justify-between px-5 py-3 text-left">
              <div className="flex items-center gap-3">
                <ScrollText className="w-4 h-4 text-emerald-600" />
                <div>
                  <div className="font-medium text-gray-900 text-sm">Deployment {String(r.deployment_id).slice(0, 8)} · {r.objective}</div>
                  <div className="text-[11px] text-gray-500">{r.created_at} · {r.approver} · constraints {r.constraint_version} · uplift {gbpM(chosen.profit_uplift)}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {r.fairness_pass != null && <span className={`text-[11px] px-2 py-0.5 rounded-full ${r.fairness_pass ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>{r.fairness_pass ? 'fair-value ✓' : 'fair-value review'}</span>}
                {isOpen ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
              </div>
            </button>
            {isOpen && (
              <div className="px-5 pb-5 border-t border-gray-100 pt-3 text-sm space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div><div className="text-[11px] uppercase tracking-wide text-gray-500 mb-1">Reproducibility</div>
                    <div className="text-xs text-gray-700 space-y-0.5">
                      <div>Data: {r.data_snapshot}</div>
                      <div>Conversion model: <span className="font-mono">{r.conversion_model}{r.conversion_model_version ? ` v${r.conversion_model_version}` : ''}</span></div>
                      <div>Retention model: <span className="font-mono">{r.retention_model}{r.retention_model_version ? ` v${r.retention_model_version}` : ''}</span></div>
                      <div>Re-run: <span className="font-mono">{r.rerun_pointer}</span></div>
                    </div></div>
                  <div><div className="text-[11px] uppercase tracking-wide text-gray-500 mb-1">Chosen</div>
                    <div className="text-xs text-gray-700">Objective <b>{chosen.objective}</b> · {chosen.segments} segments · expected profit {gbpM(chosen.expected_profit_opt)} (hold {gbpM(chosen.expected_profit_hold)}) · uplift <b>{gbpM(chosen.profit_uplift)}</b> · volume {Number(chosen.expected_volume || 0).toLocaleString()}</div>
                    <div className="text-[11px] uppercase tracking-wide text-gray-500 mt-2 mb-1">Rejected alternatives</div>
                    <div className="text-xs text-gray-700 space-y-0.5">
                      {rej.map((a: any, i: number) => <div key={i}>• <b>{a.label}</b> — profit {gbpM(a.expected_profit)}, volume {Number(a.expected_volume || 0).toLocaleString()}{a.note ? ` (${a.note})` : ''}</div>)}
                    </div></div>
                </div>
                {r.fairness_summary && <div><div className="text-[11px] uppercase tracking-wide text-gray-500 mb-1">Fairness review</div><div className="text-xs text-gray-600">{r.fairness_summary}</div></div>}
                {facs.length > 0 && <div className="text-[11px] text-gray-500">Factors: {facs.map((f: any) => `${f.segment} ${signPct(f.factor_pct)}`).join(' · ')}</div>}
                <div className="pt-1">
                  <button onClick={() => draftPaper(r)} disabled={pp?.busy}
                    className="inline-flex items-center gap-2 bg-gray-900 hover:bg-black disabled:opacity-60 text-white text-xs font-medium rounded-md px-3 py-1.5">
                    {pp?.busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Bot className="w-3.5 h-3.5" />}
                    Draft committee paper
                  </button>
                  {pp?.text && <div className="mt-2 text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded-lg p-3 whitespace-pre-wrap max-h-96 overflow-y-auto">{pp.text}</div>}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// --- Act 2: the reactive aggregator-squeeze walkthrough ---------------------
// Drives the real agents + governed jobs end to end: an external event → the
// drift sentinel detects → the planner designs → the solver decides → the
// recommender assembles the pack → the gate routes → deploy → did-it-work.
function AggregatorSqueeze() {
  const [res, setRes] = useState<Record<string, any>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const set = (k: string, v: any) => setRes((p) => ({ ...p, [k]: v }));

  const pollRun = (runId: any): Promise<string> => new Promise((resolve) => {
    let n = 0;
    const t = async () => {
      if (++n > 80) return resolve('TIMEOUT');
      const s = await api.optRunStatus(runId);
      if (s.life_cycle_state && !['TERMINATED', 'SKIPPED', 'INTERNAL_ERROR'].includes(s.life_cycle_state)) {
        setTimeout(t, 5000);
      } else resolve(s.result_state || s.life_cycle_state || 'done');
    };
    setTimeout(t, 4000);
  });

  const agent = async (k: string, persona: string, question: string) => {
    setBusy(k);
    try { const r = await api.agentLead({ persona, question }); set(k, r?.answer || r?.error || '(no answer)'); }
    catch (e) { set(k, String(e)); } finally { setBusy(null); }
  };
  const solve = async () => {
    setBusy('solve'); set('solve', 'running the governed solver…');
    try {
      const r = await api.optRun({ objective: 'retention_weighted_profit', full: false });
      if (!r?.ok) { set('solve', 'error: ' + (r?.error || 'failed')); return; }
      const st = await pollRun(r.run_id); set('solve', `solver ${st} — factors re-solved for retention-weighted profit`);
    } finally { setBusy(null); }
  };
  const deploy = async () => {
    setBusy('deploy');
    try { const r = await api.optDeploy({ note: 'aggregator-squeeze response' });
      set('deploy', r?.ok ? `deployed & audited (${r.segments} segments, ${r.constraint_version})` : (r?.gated ? 'GATED: ' + r.error : r?.error)); }
    finally { setBusy(null); }
  };
  const advance = async () => {
    setBusy('advance'); set('advance', 'advancing the month…');
    try {
      const r = await api.optAdvance();
      if (!r?.ok) { set('advance', 'error: ' + (r?.error || 'failed')); return; }
      const st = await pollRun(r.run_id);
      const ar = await api.optAdvanceResult();
      const ro = ar?.rollup;
      set('advance', ro ? `${st} — predicted ${gbpM(ro.predicted_profit)} → realized ${gbpM(ro.realized_profit)} (${signPct(ro.delta_pct)})` : st);
    } finally { setBusy(null); }
  };

  const beats: { k: string; n: number; title: string; story: string; label: string; run: () => void }[] = [
    { k: 'detect', n: 1, title: 'An aggregator undercuts young drivers', label: 'Run the drift sentinel',
      story: 'A price-comparison site drops young-driver quotes. Our U25 conversion starts slipping. The drift sentinel watches the monitoring signal and decides if it is material.',
      run: () => agent('detect', 'drift_sentinel', 'Our young-driver conversion is slipping after an aggregator move. Is the drift material and should we re-optimise?') },
    { k: 'plan', n: 2, title: 'Plan the response', label: 'Run the planner',
      story: 'The planner designs the next run — objective, grid size, and which segments to watch — using the current book and frontier.',
      run: () => agent('plan', 'planner', 'Design a re-optimisation run to defend young-driver volume without walking the margin on the rest of the book.') },
    { k: 'solve', n: 3, title: 'Decide under constraints', label: 'Run the governed solver',
      story: 'The deterministic solver re-solves within the versioned corridor — retention-weighted this time, to defend volume.',
      run: solve },
    { k: 'recommend', n: 4, title: 'Assemble the decision pack', label: 'Run the recommender',
      story: 'The recommender reads the solved factors, the frontier and the fair-value evidence, and assembles the pack a pricing committee signs off.',
      run: () => agent('recommend', 'recommender', 'Assemble the decision pack for this re-optimisation: recommendation, uplift by segment, fair-value verdict, residual risks.') },
    { k: 'deploy', n: 5, title: 'The gate routes it', label: 'Approve & deploy',
      story: 'The deployment gate re-checks the corridor server-side (RBAC + ±15%). Within the pre-approved corridor it can auto-deploy; outside it needs human sign-off. Either way it is audited.',
      run: deploy },
    { k: 'advance', n: 6, title: 'Did it work?', label: 'Advance one month',
      story: 'Roll the book forward under the deployed prices and compare what the solver predicted to what the book realized.',
      run: advance },
  ];

  return (
    <div>
      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-sm text-gray-700 mb-4">
        <b>The reactive second act.</b> An external event happens; the system detects it, proposes a
        response, decides under policy, routes through the gate, deploys, and proves the result — the
        machine runs the pricing cycle, the human sets the policy for when it may act alone. Every button
        below fires the <b>real</b> agent or governed job.
      </div>
      {beats.map((b) => (
        <div key={b.k} className="bg-white rounded-lg border border-gray-200 p-5 mb-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-6 h-6 rounded-full bg-emerald-600 text-white text-xs flex items-center justify-center font-semibold">{b.n}</span>
            <h3 className="font-semibold text-gray-900">{b.title}</h3>
          </div>
          <p className="text-xs text-gray-500 mb-3 ml-8">{b.story}</p>
          <div className="ml-8">
            <button onClick={b.run} disabled={busy === b.k}
              className="inline-flex items-center gap-2 bg-gray-900 hover:bg-black disabled:opacity-60 text-white text-sm font-medium rounded-md px-4 py-2">
              {busy === b.k ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {b.label}
            </button>
            {res[b.k] && (
              <div className="mt-3 text-sm text-gray-700 bg-gray-50 border border-gray-200 rounded-lg p-3 whitespace-pre-wrap">{String(res[b.k])}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function DeviationBars({ rows }: { rows: any[] }) {
  if (!rows.length) return <div className="text-sm text-gray-400">No distribution.</div>;
  const max = Math.max(...rows.map((r) => Number(r.count)), 1);
  return (
    <div className="flex items-end gap-1 h-40">
      {rows.map((r) => (
        <div key={r.vs_technical_band} className="flex-1 flex flex-col items-center justify-end">
          <div className={`w-full rounded-t ${r.outside_corridor ? 'bg-amber-400' : 'bg-emerald-500'}`}
            style={{ height: `${(Number(r.count) / max) * 100}%` }} title={`${r.vs_technical_band}: ${Number(r.count).toLocaleString()}`} />
          <div className="text-[9px] text-gray-400 mt-1 rotate-45 origin-left whitespace-nowrap">{r.vs_technical_band}</div>
        </div>
      ))}
    </div>
  );
}
