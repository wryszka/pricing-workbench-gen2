import { useEffect, useRef, useState } from 'react';
import { Boxes, Play, Loader2, ExternalLink } from 'lucide-react';
import { PageHeader, Section, Metric, Pill, Btn, Note, DemoDisclaimer } from '../components/ui';
import { api } from '../lib/api';

// Chapter 3 — choose a plan under uncertainty. Robust maximin of expected-margin uplift
// across worlds (demand model × market/cost scenario). Compares baseline / nominal / robust.

const gbp = (n: number | null | undefined) => (n == null ? '—' : '£' + Math.round(n).toLocaleString('en-GB'));
const num = (n: number | null | undefined) => (n == null ? '—' : Math.round(n).toLocaleString('en-GB'));
const pctf = (f: number) => (f >= 1 ? '+' : '−') + Math.round(Math.abs(f - 1) * 100) + '%';
const GRANDMA = '70+ · grp≥30';
const PLAN_ORDER = ['baseline', 'nominal', 'robust'];

export default function Chapter3() {
  const [pending, setPending] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const pollRef = useRef<any>(null);
  useEffect(() => () => { if (pollRef.current) clearTimeout(pollRef.current); }, []);

  const run = async () => {
    if (pending) return;
    setErr(null); setResult(null);
    try {
      const r = await api.optDemoCh3Run({ sales_ratio: 0.98 });
      const p = { app_run_id: r.app_run_id, job_run_id: r.job_run_id, status: 'running', run_page_url: null };
      setPending(p); poll(p, 0);
    } catch (e) { setErr(String(e)); }
  };
  const poll = (p: any, n: number) => {
    if (n > 90) { setPending({ ...p, status: 'failed' }); return; }
    pollRef.current = setTimeout(async () => {
      try {
        const s = await api.optDemoCh3Status(p.app_run_id, p.job_run_id);
        if (s.status === 'succeeded' && s.result) { setPending(null); setResult({ ...s.result, run_page_url: s.run_page_url, app_run_id: p.app_run_id }); }
        else if (s.status === 'failed') { setPending({ ...p, status: 'failed', run_page_url: s.run_page_url }); }
        else { setPending({ ...p, run_page_url: s.run_page_url }); poll(p, n + 1); }
      } catch { poll(p, n + 1); }
    }, 4000);
  };

  return (
    <>
      <PageHeader eyebrow="Pricing optimisation · Chapter 3" title="A plan that holds up under uncertainty"
        subtitle="Chapter 2 chose a plan under one demand estimate. Now we ask what happens if demand or market conditions differ, and choose a plan that performs better across those alternatives." icon={Boxes} />
      <DemoDisclaimer>
        Worlds are declared demand-model + market/cost <b>stress scenarios</b> — chosen magnitudes, not forecasts or
        probabilities. "Worst case" applies only to the included worlds and expected outcomes. Synthetic throughout.
      </DemoDisclaimer>

      <Section title="Run the robust decision" subtitle="Maximise the worst world's expected-margin uplift, holding the inherited 98% sales floor in every world.">
        <div className="flex items-center gap-3">
          <Btn tone="primary" disabled={!!pending} onClick={run}>
            {pending ? <><Loader2 className="w-4 h-4 animate-spin" /> Solving worlds…</> : <><Play className="w-4 h-4" /> Run robust decision</>}
          </Btn>
          {pending?.run_page_url && <a href={pending.run_page_url} target="_blank" rel="noopener noreferrer" className="text-brand inline-flex items-center gap-1 text-sm font-medium">Open run <ExternalLink className="w-3.5 h-3.5" /></a>}
          {pending?.status === 'failed' && <span className="text-[12px] text-amber-700">Run failed — see the Databricks run.</span>}
        </div>
        {err && <div className="mt-2"><Note>{err}</Note></div>}
      </Section>

      {result && <Compare result={result} />}
    </>
  );
}

function Compare({ result }: { result: any }) {
  const run = result.run || {};
  const worlds: any[] = result.worlds || [];
  const comp: any[] = result.comparison || [];
  const sel: any[] = result.selection || [];
  const plans = PLAN_ORDER.filter((p) => comp.some((c) => c.plan === p));

  // uplift[plan][world]
  const uplift: Record<string, Record<string, any>> = {};
  comp.forEach((c) => { (uplift[c.plan] ||= {})[c.world_id] = c; });
  const minUplift = (p: string) => Math.min(...worlds.map((w) => uplift[p]?.[w.world_id]?.uplift ?? 0));
  const grandmaFactor = (p: string) => { const r = sel.find((x) => x.plan === p && x.segment === GRANDMA); return r ? r.factor : null; };
  const maxMove = (p: string) => Math.max(...sel.filter((x) => x.plan === p).map((x) => Math.abs(x.factor - 1)));

  const cellTone = (c: any) => !c ? '' : (!c.meets_floor ? 'bg-amber-100 text-amber-800' : c.uplift >= 0 ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-700');

  return (
    <>
      <Section title="Robust vs nominal" subtitle="Minimum expected uplift across the included scenarios — with the nominal-objective trade-off beside it.">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Metric label="Robust — min uplift" value={gbp(run.robust_worst_uplift)} tone="green" sub="worst included world" />
          <Metric label="Nominal — min uplift" value={gbp(run.nominal_worst_uplift)} sub="same feasible set, nominal objective" />
          <Metric label="Worlds" value={num(run.n_worlds)} sub={`${num(run.n_models)} demand model(s)`} />
          <Metric label="Sales floor" value={`${Math.round((run.sales_ratio ?? 0.98) * 100)}%`} sub="held in every world" />
        </div>
        <Note>Robust maximises the worst included world's uplift; nominal maximises one world's margin over the same all-world feasible set. The gap is the price of insuring against the other scenarios — not certainty, and only over the worlds shown.</Note>
      </Section>

      <Section title="Plan comparison" subtitle="Each plan evaluated in every world. Amber = below that world's sales floor.">
        <div className="overflow-x-auto mb-3">
          <table className="w-full text-[13px]">
            <thead><tr className="text-left text-mut border-b border-line">
              <th className="py-1.5 pr-3">Plan</th><th className="pr-3">Min uplift</th><th className="pr-3">Grandma factor</th><th className="pr-3">Largest move</th>
              {worlds.map((w) => <th key={w.world_id} className="pr-2 text-[11px]">{w.label}<div className="text-mut font-normal">{w.model}</div></th>)}
            </tr></thead>
            <tbody>
              {plans.map((p) => (
                <tr key={p} className="border-b border-line/60">
                  <td className="py-1.5 pr-3 font-medium text-ink capitalize">{p}</td>
                  <td className="pr-3 font-medium">{gbp(minUplift(p))}</td>
                  <td className="pr-3">{grandmaFactor(p) != null ? pctf(grandmaFactor(p)) : '—'}</td>
                  <td className="pr-3">{isFinite(maxMove(p)) ? '±' + Math.round(maxMove(p) * 100) + '%' : '—'}</td>
                  {worlds.map((w) => {
                    const c = uplift[p]?.[w.world_id];
                    return <td key={w.world_id} className={`pr-2 ${cellTone(c)}`}>{c ? gbp(c.uplift) : '—'}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-mut">
          <span>run <span className="font-mono">{String(result.app_run_id).slice(0, 8)}</span></span>
          {result.run_page_url && <a href={result.run_page_url} target="_blank" rel="noopener noreferrer" className="text-brand inline-flex items-center gap-1">Open Databricks run <ExternalLink className="w-3 h-3" /></a>}
        </div>
        <Note>Worlds are the declared model × market/cost stresses; no probability weighting is applied. If the robust optimum equals the baseline, that itself is the finding — the safe move is to hold.</Note>
      </Section>
    </>
  );
}
