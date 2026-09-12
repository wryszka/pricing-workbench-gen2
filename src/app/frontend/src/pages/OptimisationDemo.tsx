import { useEffect, useRef, useState } from 'react';
import { Calculator, ArrowRight, Play, Loader2, CheckCircle2, ExternalLink } from 'lucide-react';
import { Page, PageHeader, Section, Metric, Pill, Btn, Note, DemoDisclaimer, Loading } from '../components/ui';
import { api } from '../lib/api';
import Chapter2 from './OptimisationDemoCh2';

// Chapter 1 — the honest teaching flow. Two connected parts:
//   • Explain (worked example, arithmetic from the shared core via /example)
//   • Run on Databricks (the SAME example run as a real job, read back by run id)
// The numbers are never re-implemented here; they come from the API.

const gbp = (n: number | null | undefined) => (n == null ? '—' : '£' + Math.round(n).toLocaleString('en-GB'));
const num = (n: number | null | undefined) => (n == null ? '—' : Math.round(n).toLocaleString('en-GB'));
const signed = (n: number) => (n >= 0 ? '+' : '−') + Math.abs(Math.round(n)).toLocaleString('en-GB');
const sgbp = (n: number) => (n >= 0 ? '+£' : '−£') + Math.abs(Math.round(n)).toLocaleString('en-GB');

export default function OptimisationDemo() {
  const [chapter, setChapter] = useState<'1' | '2'>('1');
  return (
    <Page>
      <div className="flex flex-wrap gap-1.5 mb-4">
        <Btn tone={chapter === '1' ? 'primary' : 'ghost'} onClick={() => setChapter('1')}>Chapter 1 · One segment</Btn>
        <Btn tone={chapter === '2' ? 'primary' : 'ghost'} onClick={() => setChapter('2')}>Chapter 2 · A portfolio</Btn>
      </div>
      {chapter === '1' ? <Chapter1 /> : <Chapter2 />}
    </Page>
  );
}

function Chapter1() {
  const [data, setData] = useState<any>(null);
  const [view, setView] = useState<'explain' | 'run'>('explain');
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { api.optDemoExample().then(setData).catch((e) => setErr(String(e))); }, []);

  if (err) return <Note>Couldn't load the example: {err}</Note>;
  if (!data) return <Loading label="Loading the worked example…" />;

  const ex = data.example;
  return (
    <>
      <PageHeader
        eyebrow="Pricing optimisation · Chapter 1"
        title="One segment — which price meets our goal?"
        subtitle="Explain optimisation on one synthetic segment, then run exactly that calculation on Databricks."
        icon={Calculator}
        actions={
          <div className="flex gap-1.5">
            <Btn tone={view === 'explain' ? 'primary' : 'ghost'} onClick={() => setView('explain')}>Explain</Btn>
            <Btn tone={view === 'run' ? 'primary' : 'ghost'} onClick={() => setView('run')}>Run on Databricks</Btn>
          </div>
        }
      />
      <DemoDisclaimer>
        Synthetic teaching example. Purchase probabilities are <b>supplied assumptions — not learned from real
        customers</b>. "{ex.segment_mnemonic}" is a mnemonic for an invented segment ({ex.segment_label}); it is not a
        claim about real older drivers. The 1,000 are potential customers (opportunities), not sold policies.
      </DemoDisclaimer>

      {view === 'explain' ? <Explain data={data} onRun={() => setView('run')} /> : <RunOnDatabricks data={data} />}
    </>
  );
}

// --------------------------------------------------------------------------- //
// Part 1 — the explanation
// --------------------------------------------------------------------------- //
function Explain({ data, onRun }: { data: any; onRun: () => void }) {
  const ex = data.example;
  const rowsA: any[] = data.run_a.candidates;
  const rowsB: any[] = data.run_b.candidates;          // same rows, marked for the 830 requirement
  const [showMargin, setShowMargin] = useState(false);
  const [sel, setSel] = useState<number | null>(null);
  const [requireSales, setRequireSales] = useState(false);
  const rows = requireSales ? rowsB : rowsA;
  const winner = requireSales ? data.run_b.winner : data.run_a.winner;

  return (
    <div className="space-y-5">
      {/* Screen 1 */}
      <Section title="1 · The question" subtitle="We know what a policy is expected to cost. That doesn't tell us the best price — a higher price earns more per sale, but fewer people may buy.">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Metric label="Opportunities" value={num(ex.opportunities)} sub="potential customers, not sold policies" />
          <Metric label="Modelled cost / sale" value={gbp(ex.modelled_variable_cost_per_sale)} sub="the variable costs we choose to model" />
          <Metric label="Current price" value={gbp(ex.baseline_price)} sub="today's offered price" />
        </div>
      </Section>

      {/* Screen 2 */}
      <Section title="2 · Demand and margin"
        subtitle="For each candidate price: how many are expected to buy, and what margin that earns."
        actions={<Btn tone="ghost" onClick={() => setShowMargin((s) => !s)}>{showMargin ? 'Hide the margin' : 'Show the margin'}</Btn>}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-mut border-b border-line">
              <th className="py-1.5 pr-3">Candidate price</th><th className="pr-3">Purchase prob.</th><th className="pr-3">Expected customers</th>
              {showMargin && <><th className="pr-3">Margin / sale</th><th>Expected total margin</th></>}
            </tr></thead>
            <tbody>
              {rowsA.map((r) => (
                <tr key={r.price} onClick={() => setSel(sel === r.price ? null : r.price)}
                  className={`border-b border-line/60 cursor-pointer hover:bg-slate-50 ${sel === r.price ? 'bg-blue-50' : ''}`}>
                  <td className="py-1.5 pr-3 font-medium text-ink">{gbp(r.price)}</td>
                  <td className="pr-3">{Math.round(r.purchase_probability * 100)}%</td>
                  <td className="pr-3">{num(r.expected_customers)}</td>
                  {showMargin && <><td className="pr-3">{gbp(r.margin_per_sale)}</td><td className="font-medium">{gbp(r.expected_total_margin)}</td></>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {sel != null && (() => {
          const r = rowsA.find((x) => x.price === sel);
          return <div className="mt-2 text-[13px] text-ink bg-slate-50 border border-line rounded-lg px-3 py-2">
            At {gbp(r.price)}, we expect <b>{num(r.expected_customers)}</b> customers. We earn <b>{gbp(r.margin_per_sale)}</b> above modelled
            cost on each sale. {num(r.expected_customers)} × {gbp(r.margin_per_sale)} = <b>{gbp(r.expected_total_margin)}</b> expected margin.
          </div>;
        })()}
        <div className="mt-4"><ChartPair rows={rowsA} baseline={ex.baseline_price} /></div>
        <Note>These purchase probabilities are assumptions supplied for the demonstration. A real exercise would estimate and validate them from suitable quote-response data. Optimisation uses that demand estimate; it doesn't make it true.</Note>
      </Section>

      {/* Screen 3 */}
      <Section title="3 · The best answer, then the human requirement"
        subtitle="Objective: maximise expected margin. Then the human changes a sales requirement — and the best permitted price changes."
        actions={<Btn tone={requireSales ? 'warn' : 'ghost'} onClick={() => { setRequireSales((s) => !s); }}>{requireSales ? 'Remove the requirement' : 'Require at least 830 customers'}</Btn>}>
        <div className="flex flex-wrap gap-3 mb-3">
          <Metric label={requireSales ? 'Best permitted price' : 'Best price (no requirement)'} value={winner ? gbp(winner.price) : 'None'} tone={requireSales ? 'amber' : 'green'} sub={winner ? `${num(winner.expected_customers)} customers` : 'no feasible price'} />
          <Metric label="Expected total margin" value={winner ? gbp(winner.expected_total_margin) : '—'} />
          <Metric label="Expected premium" value={winner ? gbp(winner.expected_premium) : '—'} />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-mut border-b border-line">
              <th className="py-1.5 pr-3">Price</th><th className="pr-3">Expected customers</th><th className="pr-3">Expected margin</th><th>Status</th>
            </tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.price} className={`border-b border-line/60 ${r.selected ? 'bg-emerald-50' : (!r.feasible ? 'opacity-55' : '')}`}>
                  <td className="py-1.5 pr-3 font-medium text-ink">{gbp(r.price)}</td>
                  <td className="pr-3">{num(r.expected_customers)}</td>
                  <td className="pr-3">{gbp(r.expected_total_margin)}</td>
                  <td>{r.selected
                    ? <Pill tone="green">◄ winner</Pill>
                    : r.feasible ? <span className="text-mut text-[12px]">eligible</span>
                    : <span className="text-amber-700 text-[12px]">{r.feasibility_reason}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Note>
          {requireSales
            ? <>With the objective alone the answer was to <b>raise</b> the price to £1,100. Requiring at least 830 expected customers rules out the four higher prices, so the optimiser picks <b>£950</b> — a lower price, more customers, at a visible margin cost. Same calculation, different business requirement. "At least 830" is a floor on <b>expected</b> customers, not a guarantee that 830 people buy.</>
            : <>£1,100 wins even though £1,150 has the largest margin per sale (£350): at £1,150 the purchase probability falls to 45%, so 450 × £350 = £157,500 &lt; 700 × £300 = £210,000. Margin per sale isn't the goal — expected total margin is.</>}
        </Note>
        <div className="mt-3">
          <Btn tone="primary" onClick={onRun}>Run this example on Databricks <ArrowRight className="w-4 h-4" /></Btn>
        </div>
      </Section>
    </div>
  );
}

// Two small side-by-side charts: demand (prob vs price) and expected margin (vs price).
function ChartPair({ rows, baseline }: { rows: any[]; baseline: number }) {
  const prices = rows.map((r) => r.price);
  const pMin = Math.min(...prices), pMax = Math.max(...prices);
  const W = 300, H = 130, padL = 38, padB = 22, padT = 10, padR = 8;
  const x = (p: number) => padL + ((p - pMin) / (pMax - pMin || 1)) * (W - padL - padR);
  const mk = (vals: number[], color: string, fmt: (v: number) => string) => {
    const vMax = Math.max(...vals), vMin = Math.min(...vals);
    const y = (v: number) => padT + (1 - (v - vMin) / (vMax - vMin || 1)) * (H - padT - padB);
    const pts = rows.map((r, i) => `${x(r.price)},${y(vals[i])}`).join(' ');
    return { y, pts, vMax, vMin, color, fmt };
  };
  const demand = mk(rows.map((r) => r.purchase_probability), '#2D6CDF', (v) => `${Math.round(v * 100)}%`);
  const margin = mk(rows.map((r) => r.expected_total_margin), '#12805C', (v) => '£' + Math.round(v / 1000) + 'k');
  const chart = (title: string, vals: number[], c: any) => (
    <div className="flex-1 min-w-[260px]">
      <div className="text-[11px] font-bold uppercase tracking-wide text-mut mb-1">{title}</div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
        <polyline points={c.pts} fill="none" stroke={c.color} strokeWidth={2} />
        {rows.map((r, i) => <circle key={r.price} cx={x(r.price)} cy={c.y(vals[i])} r={3} fill={c.color} />)}
        {rows.map((r) => <text key={r.price} x={x(r.price)} y={H - 8} fontSize={8} textAnchor="middle" fill="#64748b">{r.price}</text>)}
        <text x={4} y={padT + 6} fontSize={8} fill="#64748b">{c.fmt(c.vMax)}</text>
        <text x={4} y={H - padB} fontSize={8} fill="#64748b">{c.fmt(c.vMin)}</text>
      </svg>
    </div>
  );
  return (
    <div className="flex flex-wrap gap-4">
      {chart('Demand — P(buy) vs price', rows.map((r) => r.purchase_probability), demand)}
      {chart('Expected total margin vs price', rows.map((r) => r.expected_total_margin), margin)}
      <div className="w-full text-[11px] text-mut">Points are the six candidate prices; lines are visual guides, not extra prices the solver searched. Baseline £{baseline}.</div>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Part 2 — run it on Databricks
// --------------------------------------------------------------------------- //
function RunOnDatabricks({ data }: { data: any }) {
  const ex = data.example;
  const rowsA: any[] = data.run_a.candidates;
  const [minCustomers, setMinCustomers] = useState<string>('');
  const [pending, setPending] = useState<any>(null);      // { app_run_id, job_run_id, status, run_page_url }
  const [runs, setRuns] = useState<any[]>([]);            // completed runs (keep last 2 for comparison)
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<any>(null);

  useEffect(() => () => { if (pollRef.current) clearTimeout(pollRef.current); }, []);

  const start = async () => {
    if (pending) return;                                  // no duplicate submissions
    setError(null);
    const min = minCustomers.trim() === '' ? null : Number(minCustomers);
    if (min != null && (!isFinite(min) || min < 0)) { setError('Minimum expected customers must be a non-negative number.'); return; }
    try {
      const r = await api.optDemoRun({ min_expected_customers: min });
      const p = { app_run_id: r.app_run_id, job_run_id: r.job_run_id, status: 'running', run_page_url: null, requirement: min };
      setPending(p);
      poll(p, 0);
    } catch (e) { setError(String(e)); }
  };

  const poll = (p: any, n: number) => {
    if (n > 75) { setPending({ ...p, status: 'failed' }); return; }   // ~5 min ceiling
    pollRef.current = setTimeout(async () => {
      try {
        const s = await api.optDemoStatus(p.app_run_id, p.job_run_id);
        if (s.status === 'succeeded' && s.result) {
          setPending(null);
          setRuns((prev) => [{ ...s.result, requirement: p.requirement, run_page_url: s.run_page_url, app_run_id: p.app_run_id }, ...prev].slice(0, 2));
        } else if (s.status === 'failed') {
          setPending({ ...p, status: 'failed', run_page_url: s.run_page_url });
        } else {
          setPending({ ...p, status: 'running', run_page_url: s.run_page_url });
          poll(p, n + 1);
        }
      } catch { poll(p, n + 1); }
    }, 4000);
  };

  return (
    <div className="space-y-5">
      {/* Panel A */}
      <Section title="A · Inputs & requirement" subtitle="The same example, run as a real Databricks job. Objective is fixed; you set the sales requirement.">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
          <Metric label="Opportunities" value={num(ex.opportunities)} />
          <Metric label="Modelled cost / sale" value={gbp(ex.modelled_variable_cost_per_sale)} />
          <Metric label="Baseline price" value={gbp(ex.baseline_price)} />
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div><div className="text-[11px] font-bold uppercase tracking-wide text-mut mb-1">Objective</div><Pill tone="blue">Maximise expected margin</Pill></div>
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wide text-mut mb-1">Minimum expected customers</div>
            <input value={minCustomers} onChange={(e) => setMinCustomers(e.target.value)} placeholder="none"
              className="border border-line rounded-md px-3 py-1.5 text-sm w-40" />
          </div>
          <Btn tone="ghost" onClick={() => setMinCustomers('830')}>Require 830 customers</Btn>
          <Btn tone="primary" onClick={start} disabled={!!pending}>
            {pending ? <><Loader2 className="w-4 h-4 animate-spin" /> Running…</> : <><Play className="w-4 h-4" /> Run on Databricks</>}
          </Btn>
        </div>
        <div className="mt-2 text-[11px] text-mut">Input table: <span className="font-mono">optimisation_demo_inputs</span> (Unity Catalog) · candidate prices are the six shown; the search considers those six, not every possible price.</div>
        {error && <div className="mt-2"><Note>{error}</Note></div>}
      </Section>

      {/* Panel B */}
      <Section title="B · The job">
        {!pending && runs.length === 0 && <div className="text-sm text-mut">No run yet. Set a requirement (or leave it blank) and press <b>Run on Databricks</b>.</div>}
        {pending && (
          <div className="flex items-center gap-3 text-sm">
            <Pill tone={pending.status === 'failed' ? 'red' : 'amber'}>{pending.status === 'failed' ? 'Failed' : 'Running'}</Pill>
            <span className="text-mut">Submitted a Python job to Databricks — it reads the input table, evaluates the six prices, applies the requirement, and writes the results back.</span>
            {pending.run_page_url && <a href={pending.run_page_url} target="_blank" rel="noopener noreferrer" className="text-brand inline-flex items-center gap-1 font-medium">Open Databricks run <ExternalLink className="w-3.5 h-3.5" /></a>}
          </div>
        )}
        {!pending && runs.length > 0 && <div className="text-sm text-mut inline-flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-600" /> Last run complete — see the result below. Run again with a different requirement to compare.</div>}
      </Section>

      {/* Panel C */}
      <Section title="C · Result & comparison" subtitle="Read from the exact completed run, not a cached or ‘latest’ value.">
        {runs.length === 0
          ? <div className="text-sm text-mut">Results appear here once a run completes.</div>
          : <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">{runs.map((r) => <RunResult key={r.app_run_id} r={r} baseline={ex.baseline_price} />)}</div>}
      </Section>

      <DemoDisclaimer>This proves the calculation can run on Databricks and be inspected. It does not validate real-world demand or deploy a production price.</DemoDisclaimer>
    </div>
  );
}

function RunResult({ r, baseline }: { r: any; baseline: number }) {
  const run = r.run || {};
  const cands: any[] = r.candidates || [];
  const noFeasible = run.status === 'no_feasible';
  const base = cands.find((c) => Number(c.candidate_price) === Number(baseline));
  const win = cands.find((c) => c.selected);
  const reqLabel = r.requirement == null ? 'No sales requirement' : `≥ ${num(r.requirement)} expected customers`;
  return (
    <div className="rounded-xl border border-line p-4">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="font-semibold text-ink text-sm">{reqLabel}</div>
        <Pill tone={noFeasible ? 'amber' : 'green'}>{noFeasible ? 'No feasible price' : 'Completed Databricks run'}</Pill>
      </div>
      {noFeasible
        ? <Note>No candidate meets the requirement. The requirement was not relaxed.</Note>
        : <>
          <div className="grid grid-cols-3 gap-2 mb-2">
            <Metric label="Offered price" value={gbp(win?.candidate_price)} tone="green" />
            <Metric label="Expected customers" value={num(win?.expected_customers)} />
            <Metric label="Expected margin" value={gbp(win?.expected_total_margin)} />
          </div>
          {base && win && (
            <div className="text-[12px] text-mut mb-2">
              vs baseline ({gbp(baseline)}): price {sgbp(win.candidate_price - base.candidate_price)} ·
              customers {signed(win.expected_customers - base.expected_customers)} ·
              margin {sgbp(win.expected_total_margin - base.expected_total_margin)} ·
              premium {sgbp(win.expected_premium - base.expected_premium)}
            </div>
          )}
        </>}
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead><tr className="text-left text-mut border-b border-line"><th className="py-1 pr-2">Price</th><th className="pr-2">Cust.</th><th className="pr-2">Margin</th><th>Status</th></tr></thead>
          <tbody>
            {cands.map((c) => (
              <tr key={c.candidate_price} className={`border-b border-line/60 ${c.selected ? 'bg-emerald-50' : (!c.feasible ? 'opacity-55' : '')}`}>
                <td className="py-1 pr-2 font-medium text-ink">{gbp(c.candidate_price)}</td>
                <td className="pr-2">{num(c.expected_customers)}</td>
                <td className="pr-2">{gbp(c.expected_total_margin)}</td>
                <td>{c.selected ? '◄ winner' : c.feasible ? <span className="text-mut">eligible</span> : <span className="text-amber-700">{c.feasibility_reason}</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-2 flex items-center gap-3 text-[11px] text-mut">
        <span>run <span className="font-mono">{String(r.app_run_id).slice(0, 8)}</span></span>
        {r.run_page_url && <a href={r.run_page_url} target="_blank" rel="noopener noreferrer" className="text-brand inline-flex items-center gap-1">Open Databricks run <ExternalLink className="w-3 h-3" /></a>}
        <span>input v{run.input_delta_version ?? '—'}</span>
      </div>
    </div>
  );
}
