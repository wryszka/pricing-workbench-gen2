import { useEffect, useRef, useState } from 'react';
import { Layers, Play, Loader2, CheckCircle2, ExternalLink } from 'lucide-react';
import { PageHeader, Section, Metric, Pill, Btn, Note, DemoDisclaimer, Loading } from '../components/ui';
import { api } from '../lib/api';

// Chapter 2 — a portfolio. Learned demand, individual costs, coupled segment prices,
// a portfolio sales floor. Reads model-free summaries; runs the real MILP job.

const gbp = (n: number | null | undefined) => (n == null ? '—' : '£' + Math.round(n).toLocaleString('en-GB'));
const num = (n: number | null | undefined) => (n == null ? '—' : Math.round(n).toLocaleString('en-GB'));
const pct = (f: number) => (f >= 1 ? '+' : '−') + Math.round(Math.abs(f - 1) * 100) + '%';
const GRANDMA = '70+ · grp≥30';

export default function Chapter2() {
  const [prep, setPrep] = useState<any>(null);
  const [pf, setPf] = useState<any>(null);
  const [release, setRelease] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  const refreshRelease = () => api.optDemoCh2Release().then((r) => setRelease(r.active_release)).catch(() => {});
  useEffect(() => {
    api.optDemoCh2PrepareStatus().then(setPrep).catch((e) => setErr(String(e)));
    api.optDemoCh2Portfolio().then(setPf).catch(() => {});
    refreshRelease();
  }, []);

  if (err) return <Note>Couldn't load Chapter 2: {err}</Note>;
  if (!prep) return <Loading label="Loading the portfolio…" />;

  return (
    <>
      <PageHeader eyebrow="Pricing optimisation · Chapter 2" title="A portfolio — which prices meet the target together?"
        subtitle="The arithmetic is familiar. Now customers have different costs and purchase probabilities, and we choose prices for several segments at once while protecting total expected sales." icon={Layers} />
      <DemoDisclaimer>
        Synthetic, commercially illustrative demand — <b>not learned from real customers</b> and not a fairness
        certification. Nine age×vehicle segments; new-business motor only. "Expected margin" is over modelled cost,
        before fixed overhead/capital/tax — not net underwriting profit.
      </DemoDisclaimer>

      {/* Prepare status */}
      <Section title="Prepared model" subtitle="Trained + validated offline, frozen before recording — the Choose runs reuse it.">
        {prep.prepared ? (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <Pill tone={prep.manifest.passes ? 'green' : 'amber'}>{prep.manifest.passes ? 'validation passed' : 'validation FAILED — not eligible'}</Pill>
            <span className="text-mut">model <span className="font-mono">{prep.manifest.model_version}</span></span>
            {prep.validation?.weighted_calibration_error != null &&
              <span className="text-mut">calibration error {Number(prep.validation.weighted_calibration_error).toFixed(3)} (≤0.05)</span>}
            {prep.validation?.monotone_along_price != null &&
              <span className="text-mut">monotone {prep.validation.monotone_along_price ? '✓' : '✗'}</span>}
          </div>
        ) : <Note>Not prepared yet — run the "Chapter 2 prepare" job to train + validate the model.</Note>}
      </Section>

      {/* Portfolio */}
      {pf?.ready ? <Portfolio pf={pf} /> : <Section title="Portfolio"><Note>Portfolio summary not ready — run prepare.</Note></Section>}

      {/* Choose */}
      <Choose disabled={!prep.prepared || !prep.manifest?.passes} pf={pf} onApproved={refreshRelease} />

      {/* Review & release */}
      <Section title="Review & release" subtitle="Approval runs the plan through a deterministic recompute, then a Unity Catalog stored procedure called AS YOU — only an approver can release. Appended to an append-only record.">
        {release ? (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <Pill tone="green">active demo release</Pill>
            <span className="text-mut">release <span className="font-mono">{String(release.release_id).slice(0, 8)}</span></span>
            <span className="text-mut">run <span className="font-mono">{String(release.run_id).slice(0, 8)}</span></span>
            <span className="text-mut">approved by {release.approver}</span>
            <span className="text-mut">{release.released_at}</span>
            {release.previous_release_id && <span className="text-mut">← prev <span className="font-mono">{String(release.previous_release_id).slice(0, 8)}</span></span>}
          </div>
        ) : <div className="text-sm text-mut">No demo release yet. Run a plan, then Approve &amp; release it (approver only).</div>}
        <Note>The gate is a per-person Unity Catalog EXECUTE grant enforced over OBO — a non-approver's approval is denied by the platform, not the app. The consumer reads the approved release id; a new unapproved solve does not change it.</Note>
      </Section>

      {/* Check */}
      <Check hasRelease={!!release} />

      <DemoDisclaimer>The plan is a recommended factor table on a synthetic book. No real premiums are issued; nothing here is a deployed production price.</DemoDisclaimer>
    </>
  );
}

function Check({ hasRelease }: { hasRelease: boolean }) {
  const [mon, setMon] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<any>(null);
  const load = () => api.optDemoCh2Monitoring().then(setMon).catch(() => {});
  useEffect(() => { load(); return () => { if (pollRef.current) clearTimeout(pollRef.current); }; }, []);

  const advance = async () => {
    setBusy(true);
    const before = mon?.period ?? 0;
    try {
      await api.optDemoCh2Check();
      const poll = (n: number) => {
        if (n > 60) { setBusy(false); return; }
        pollRef.current = setTimeout(async () => {
          const m = await api.optDemoCh2Monitoring().catch(() => null);
          if (m && (m.period ?? 0) > before) { setMon(m); setBusy(false); }
          else poll(n + 1);
        }, 4000);
      };
      poll(0);
    } catch { setBusy(false); }
  };

  return (
    <Section title="Check — synthetic outcome" subtitle="Roll the released plan forward one synthetic period, drawing outcomes from the frozen generator (not the model). Expected vs observed, over modelled cost.">
      <div className="flex items-center gap-3 mb-3">
        <Btn tone="primary" disabled={!hasRelease || busy} onClick={advance}>
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />} Advance one synthetic period
        </Btn>
        {!hasRelease && <span className="text-[12px] text-amber-700">Approve & release a plan first.</span>}
        {mon?.period != null && <span className="text-[12px] text-mut">period {mon.period}</span>}
      </div>
      {mon?.rows?.length ? (
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead><tr className="text-left text-mut border-b border-line"><th className="py-1 pr-2">Segment</th><th className="pr-2">Exp. sales</th><th className="pr-2">Obs. sales</th><th className="pr-2">Exp. margin</th><th className="pr-2">Obs. margin</th><th>n</th></tr></thead>
            <tbody>
              {mon.rows.map((r: any) => (
                <tr key={r.segment} className={`border-b border-line/60 ${r.segment === GRANDMA ? 'bg-blue-50' : ''}`}>
                  <td className="py-1 pr-2 font-medium text-ink">{r.segment}</td>
                  <td className="pr-2">{num(r.expected_sales)}</td>
                  <td className="pr-2">{num(r.observed_sales)}</td>
                  <td className="pr-2">{gbp(r.expected_margin)}</td>
                  <td className="pr-2">{gbp(r.observed_margin)}</td>
                  <td>{num(r.n)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <div className="text-sm text-mut">No synthetic check yet.</div>}
      <Note>Synthetic outcome check: outcomes are drawn from the frozen generator, not the model's own predictions. It does not validate real demand or realised claims profitability.</Note>
    </Section>
  );
}

function Portfolio({ pf }: { pf: any }) {
  const t = pf.totals;
  const rep = pf.representative_opportunity;
  const repCost = rep ? rep.expected_claims + rep.per_sale_expenses + rep.commission_rate * rep.baseline_price : null;
  return (
    <Section title="The book today" subtitle="Baseline expected sales, premium and margin at current prices — learned estimates, per segment.">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
        <Metric label="Opportunities" value={num(t.opportunities)} />
        <Metric label="Baseline expected sales" value={num(t.baseline_sales)} />
        <Metric label="Baseline premium" value={gbp(t.baseline_premium)} />
        <Metric label="Baseline margin" value={gbp(t.baseline_margin)} />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-mut border-b border-line">
            <th className="py-1.5 pr-3">Segment</th><th className="pr-3">Opps</th><th className="pr-3">Avg baseline price</th>
            <th className="pr-3">Avg modelled cost</th><th className="pr-3">Baseline sales</th><th>Baseline margin</th>
          </tr></thead>
          <tbody>
            {pf.segments.map((s: any) => (
              <tr key={s.segment} className={`border-b border-line/60 ${s.segment === GRANDMA ? 'bg-blue-50' : ''}`}>
                <td className="py-1.5 pr-3 font-medium text-ink">{s.segment}{s.segment === GRANDMA && <span className="text-[11px] text-blue-700"> · grandma</span>}</td>
                <td className="pr-3">{num(s.opportunities)}</td>
                <td className="pr-3">{gbp(s.avg_baseline_price)}</td>
                <td className="pr-3">{gbp(s.avg_cost)}</td>
                <td className="pr-3">{num(s.baseline_sales)}</td>
                <td>{gbp(s.baseline_margin)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rep && (
        <Note>
          Representative <b>{GRANDMA}</b> opportunity #{rep.opportunity_id}: baseline price {gbp(rep.baseline_price)}, market {gbp(rep.market_premium)},
          modelled cost {gbp(repCost)} (claims {gbp(rep.expected_claims)} + expenses {gbp(rep.per_sale_expenses)} + {Math.round(rep.commission_rate * 100)}% commission).
          The model predicts a purchase probability at each candidate price; we sum individual probability-weighted margins — no median-customer shortcut.
        </Note>
      )}
    </Section>
  );
}

function Choose({ disabled, pf, onApproved }: { disabled: boolean; pf: any; onApproved: () => void }) {
  const [pending, setPending] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const pollRef = useRef<any>(null);
  useEffect(() => () => { if (pollRef.current) clearTimeout(pollRef.current); }, []);

  const baselineBySeg: Record<string, any> = {};
  (pf?.segments || []).forEach((s: any) => { baselineBySeg[s.segment] = s; });

  const start = async (ratio: number | null, label: string) => {
    if (pending) return;
    const r = await api.optDemoCh2Run({ min_portfolio_sales_ratio: ratio });
    const p = { app_run_id: r.app_run_id, job_run_id: r.job_run_id, label, ratio, status: 'running', run_page_url: null };
    setPending(p); poll(p, 0);
  };
  const poll = (p: any, n: number) => {
    if (n > 90) { setPending({ ...p, status: 'failed' }); return; }
    pollRef.current = setTimeout(async () => {
      try {
        const s = await api.optDemoCh2Status(p.app_run_id, p.job_run_id);
        if (s.status === 'succeeded' && s.result) {
          setPending(null);
          setRuns((prev) => [{ ...s.result, label: p.label, run_page_url: s.run_page_url, app_run_id: p.app_run_id }, ...prev].slice(0, 2));
        } else if (s.status === 'failed') { setPending({ ...p, status: 'failed', run_page_url: s.run_page_url }); }
        else { setPending({ ...p, run_page_url: s.run_page_url }); poll(p, n + 1); }
      } catch { poll(p, n + 1); }
    }, 4000);
  };

  return (
    <Section title="Choose the plan" subtitle="Same objective (maximise expected margin), same model and grid. Change the sales requirement; the answer changes.">
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <Btn tone="primary" disabled={disabled || !!pending} onClick={() => start(null, 'Margin first')}>
          {pending?.label === 'Margin first' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />} Margin first
        </Btn>
        <Btn tone="warn" disabled={disabled || !!pending} onClick={() => start(0.98, 'Protect sales ≥ 98%')}>
          {pending?.label?.startsWith('Protect') ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />} Protect sales ≥ 98%
        </Btn>
        {disabled && <span className="text-[12px] text-amber-700">Model not eligible — prepare + validation must pass first.</span>}
      </div>
      {pending && (
        <div className="flex items-center gap-3 text-sm mb-3">
          <Pill tone={pending.status === 'failed' ? 'red' : 'amber'}>{pending.status === 'failed' ? 'Failed' : 'Running'} · {pending.label}</Pill>
          <span className="text-mut">Solving the portfolio MILP on Databricks over the frozen model + snapshot…</span>
          {pending.run_page_url && <a href={pending.run_page_url} target="_blank" rel="noopener noreferrer" className="text-brand inline-flex items-center gap-1 font-medium">Open run <ExternalLink className="w-3.5 h-3.5" /></a>}
        </div>
      )}
      {runs.length === 0 && !pending && <div className="text-sm text-mut">Run a plan to compare it with the baseline.</div>}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {runs.map((r) => <Ch2Result key={r.app_run_id} r={r} baselineBySeg={baselineBySeg} onApproved={onApproved} />)}
      </div>
    </Section>
  );
}

function Ch2Result({ r, baselineBySeg, onApproved }: { r: any; baselineBySeg: Record<string, any>; onApproved: () => void }) {
  const run = r.run || {};
  const infeasible = run.status === 'infeasible';
  const [appr, setAppr] = useState<{ busy?: boolean; msg?: string; ok?: boolean }>({});
  const approve = async () => {
    setAppr({ busy: true });
    try {
      const res = await api.optDemoCh2Approve({ app_run_id: r.app_run_id });
      setAppr({ ok: true, msg: `approved by ${res.approved_by}` });
      onApproved();
    } catch (e) { setAppr({ msg: String(e).replace('Error: ', '') }); }
  };
  const dMargin = run.total_margin != null ? run.total_margin - run.baseline_margin : null;
  const dSales = run.total_sales != null ? run.total_sales - run.baseline_sales : null;
  return (
    <div className="rounded-xl border border-line p-4">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="font-semibold text-ink text-sm">{r.label}</div>
        <Pill tone={infeasible ? 'amber' : 'green'}>{infeasible ? 'No feasible plan' : 'Completed Databricks run'}</Pill>
      </div>
      {infeasible ? <Note>No plan meets the requirement; it was not relaxed.</Note> : <>
        <div className="grid grid-cols-3 gap-2 mb-2">
          <Metric label="Expected sales" value={num(run.total_sales)} sub={dSales != null ? `${dSales >= 0 ? '+' : '−'}${num(Math.abs(dSales))} vs baseline` : ''} />
          <Metric label="Expected margin" value={gbp(run.total_margin)} tone="green" sub={dMargin != null ? `${dMargin >= 0 ? '+' : '−'}${gbp(Math.abs(dMargin))} vs baseline` : ''} />
          <Metric label="Sales floor" value={run.min_portfolio_sales_ratio == null ? 'none' : Math.round(run.min_portfolio_sales_ratio * 100) + '%'} />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead><tr className="text-left text-mut border-b border-line"><th className="py-1 pr-2">Segment</th><th className="pr-2">Factor</th><th className="pr-2">Exp. sales</th><th>Exp. margin</th></tr></thead>
            <tbody>
              {r.selected.map((s: any) => {
                const base = baselineBySeg[s.segment];
                return (
                  <tr key={s.segment} className={`border-b border-line/60 ${s.segment === GRANDMA ? 'bg-blue-50' : ''}`}>
                    <td className="py-1 pr-2 font-medium text-ink">{s.segment}</td>
                    <td className="pr-2">{pct(s.factor)}</td>
                    <td className="pr-2">{num(s.expected_sales)}{base ? <span className="text-mut"> / {num(base.baseline_sales)}</span> : ''}</td>
                    <td>{gbp(s.expected_margin)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </>}
      {!infeasible && (
        <div className="mt-2 flex items-center gap-2">
          <Btn tone="primary" disabled={appr.busy || appr.ok} onClick={approve}>
            {appr.busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />} {appr.ok ? 'Approved & released' : 'Approve & release (approver)'}
          </Btn>
          {appr.msg && <span className={`text-[12px] ${appr.ok ? 'text-emerald-700' : 'text-amber-700'}`}>{appr.msg}</span>}
        </div>
      )}
      <div className="mt-2 flex items-center gap-3 text-[11px] text-mut">
        <span>run <span className="font-mono">{String(r.app_run_id).slice(0, 8)}</span></span>
        <span>model {run.model_version}</span>
        {r.run_page_url && <a href={r.run_page_url} target="_blank" rel="noopener noreferrer" className="text-brand inline-flex items-center gap-1">Open run <ExternalLink className="w-3 h-3" /></a>}
      </div>
    </div>
  );
}
