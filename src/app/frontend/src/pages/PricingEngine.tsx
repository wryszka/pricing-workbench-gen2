import { useEffect, useMemo, useState } from 'react';
import {
  Calculator, Loader2, PlayCircle, History, Sparkles, ShieldCheck, ExternalLink,
  ChevronDown, ChevronRight, GitCompareArrows, FileText, Calendar, RefreshCw, Tag,
} from 'lucide-react';
import { api } from '../lib/api';
import {
  Page, PageHeader, OnThisPage, Card, CardTitle, Section, Metric, Pill, AgentLead,
  UnderTheHood, Grid, SectionHead, Btn,
} from '../components/ui';

// ---------------------------------------------------------------------------
// Pricing Engine — organised around MONTHLY releases. One release bundles
// all 4 model versions + rating-engine config + narrative + approval.
// ---------------------------------------------------------------------------

type Release = {
  release_id: string;
  display_name: string;
  effective_date: string;
  status: 'champion' | 'previous_champion' | 'archived' | string;
  freq_glm_version: string;
  sev_glm_version: string;
  demand_gbm_version: string;
  fraud_gbm_version: string;
  rating_engine_version: string;
  approved_by?: string;
  narrative?: string;
};

type Section = 'quote' | 'mta' | 'history';

export default function PricingEngine() {
  const [section, setSection] = useState<Section>('quote');
  const [current, setCurrent] = useState<Release | null>(null);
  const [releases, setReleases] = useState<Release[]>([]);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getCurrentRelease().catch(() => null),
      api.listReleases().then(d => d?.releases || []).catch(() => []),
    ]).then(([c, all]) => { setCurrent(c); setReleases(all); })
      .finally(() => setLoading(false));
  }, []);

  return (
    <Page>
      <PageHeader
        eyebrow="Bricksurance SE · Pricing Engine"
        title="Pricing Engine"
        subtitle="The live monthly rate book and release history"
        icon={Calculator}
      />

      <AgentLead compact
        persona="rate_change"
        title="Rate-change analyst"
        subtitle="Reads the live rate book and models rate moves."
        seed="Describe this month's live rate book vs last month, and any rate-change considerations."
        examples={[
          'What changed in the current rate book?',
          'Who wins/loses if we raise rates 3%?',
          "What's the retention risk?",
        ]}
      />

      <OnThisPage>
        One monthly <em>release</em> bundles every model version, rating-engine configuration, and governance metadata.
        Live release is the active rate book pricing all new quotes. Quote this month's rates, re-price policies on historical
        releases, or browse the release timeline with comparison tools.
      </OnThisPage>

      {/* Current release headline */}
      {current && <CurrentReleaseCard release={current} />}
      {loading && <Card className="h-32 bg-slate-100 animate-pulse" />}

      {/* Sub-tabs */}
      <div className="flex gap-1 border-b border-line">
        <Tab active={section === 'quote'}   onClick={() => setSection('quote')}
             icon={<PlayCircle className="w-4 h-4" />}  label="Quote Runner" />
        <Tab active={section === 'mta'}     onClick={() => setSection('mta')}
             icon={<Sparkles className="w-4 h-4" />}    label="Mid-term Adjustment" />
        <Tab active={section === 'history'} onClick={() => setSection('history')}
             icon={<History className="w-4 h-4" />}     label="Release History" />
      </div>

      {section === 'quote'   && <QuoteRunner   current={current} />}
      {section === 'mta'     && <MtaSimulator  current={current} />}
      {section === 'history' && <ReleaseHistory releases={releases} />}

      <UnderTheHood
        title="Rate book architecture"
        lines={[
          { component: 'pricing_engine_releases', detail: 'Monthly bundles; effective_date + all 4 model versions' },
          { component: 'UC model aliases', detail: 'champion (live), previous_champion (rollback), archived' },
          { component: 'Governance packs', detail: 'PDF generated on release approval; linked to release_id' },
          { component: 'Inference tables', detail: 'Every quote scored on the live release is logged for audit' },
        ]}
      />
    </Page>
  );
}

function Tab({ active, onClick, icon, label }:
  { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button onClick={onClick}
            className={`inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition ${
              active ? 'border-brand text-brand' : 'border-transparent text-mut hover:text-ink'
            }`}>
      {icon} {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Current release — the big "April 2026 rate book" card
// ---------------------------------------------------------------------------

function CurrentReleaseCard({ release }: { release: Release }) {
  return (
    <Card className="bg-[linear-gradient(135deg,#eef2ff_0%,#faf5ff_100%)] border-[#ddd6fe]">
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-[0.08em] text-brand">
            Current release · effective {release.effective_date}
          </div>
          <div className="text-2xl font-bold text-ink mt-0.5 flex items-center gap-2">
            {release.display_name} rate book
            <ShieldCheck className="w-5 h-5 text-brand" />
          </div>
          {release.approved_by && (
            <div className="text-xs text-mut mt-0.5">
              Approved by {release.approved_by.split('@')[0]}
            </div>
          )}
        </div>
        <Pill tone="live">live</Pill>
      </div>

      {release.narrative && (
        <div className="mt-2 text-[13px] text-ink leading-relaxed max-w-3xl">
          {release.narrative}
        </div>
      )}

      <Grid cols={5} className="mt-4">
        <VersionChip label="Frequency GLM"   v={release.freq_glm_version} />
        <VersionChip label="Severity GLM"    v={release.sev_glm_version} />
        <VersionChip label="Demand GBM"      v={release.demand_gbm_version} />
        <VersionChip label="Fraud GBM"       v={release.fraud_gbm_version} />
        <VersionChip label="Rating engine"   v={release.rating_engine_version} highlight />
      </Grid>
    </Card>
  );
}

function VersionChip({ label, v, highlight }: { label: string; v: string; highlight?: boolean }) {
  return (
    <div className={`rounded-lg border px-2.5 py-1.5 ${
      highlight ? 'border-[#c7d2fe] bg-[#eef2ff]' : 'border-line bg-white'
    }`}>
      <div className="text-[10px] text-mut uppercase tracking-[0.05em] font-semibold">{label}</div>
      <div className="font-mono text-ink text-sm tabular-nums">{v}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Quote Runner — simplified: always runs on the current release
// ---------------------------------------------------------------------------

const DEFAULT_FEATURES: Record<string, any> = {
  sum_insured:                  2_500_000,
  annual_turnover:              850_000,
  current_premium:              1_200,
  industry_risk_tier:           'Medium',
  construction_type:            'Non-Combustible',
  region:                       'London',
  postcode_sector:              'EC1A',
  credit_score:                 620,
  ccj_count:                    1,
  years_trading:                12,
  flood_zone_rating:            3,
  proximity_to_fire_station_km: 2.4,
  crime_theft_index:            55,
  subsidence_risk:              2,
  composite_location_risk:      55,
  urban_score:                  0.9,
  is_coastal:                   0,
  population_density_per_km2:   12000,
  elevation_metres:             25,
  annual_rainfall_mm:           620,
  director_stability_score:     0.8,
  employee_count_est:           18,
  distance_to_coast_km:         12,
  neighbourhood_claim_frequency: 0.88,
  year_built:                   1985,
};

function QuoteRunner({ current }: { current: Release | null }) {
  const [features, setFeatures] = useState<Record<string, any>>(DEFAULT_FEATURES);
  const [status, setStatus]     = useState<any>(null);
  const [running, setRunning]   = useState(false);
  const [result, setResult]     = useState<any>(null);
  const [error, setError]       = useState<string | null>(null);
  const [releases, setReleases] = useState<Release[]>([]);
  const [releaseId, setReleaseId] = useState<string>('');      // '' = current
  const [batchState, setBatchState] = useState<{ runId?: number; url?: string; phase: string } | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const s = await api.getPricingStatus();
        if (!alive) return;
        setStatus(s);
        if (!s.ready) setTimeout(tick, 4000);
      } catch { if (alive) setTimeout(tick, 6000); }
    };
    tick();
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    api.listReleases().then(d => setReleases(d?.releases || [])).catch(() => {});
  }, []);

  const isHistorical = releaseId && releaseId !== '' && releaseId !== (current?.release_id || '');

  const run = async () => {
    setRunning(true); setError(null); setResult(null); setBatchState(null);

    // Current release → live serving endpoint, instant
    if (!isHistorical) {
      try {
        const r = await api.runQuote({ features, label: 'ui' });
        setResult(r);
      } catch (e: any) {
        setError(e.message || String(e));
      } finally {
        setRunning(false);
      }
      return;
    }

    // Historical → batch job; poll for completion
    try {
      const trigger = await api.scoreOnRelease(releaseId, features, 'ui');
      setBatchState({ runId: trigger.run_id, url: trigger.run_page_url, phase: 'queued' });
      // Poll
      for (let i = 0; i < 40; i++) {
        await new Promise(res => setTimeout(res, 8000));
        const s = await api.getHistoricalScoreStatus(trigger.run_id);
        setBatchState({ runId: trigger.run_id, url: trigger.run_page_url, phase: s.state });
        if (s.state === 'TERMINATED' && s.result_state === 'SUCCESS' && s.result) {
          // Shape the result like /quote/run so <QuoteResult/> can render it
          const rel = releases.find(r => r.release_id === releaseId);
          setResult({
            rating_engine: { version: s.result.model_versions?.rating_engine },
            quotes: [{
              model_versions: {
                freq_glm:   s.result.model_versions?.freq_glm,
                sev_glm:    s.result.model_versions?.sev_glm,
                demand_gbm: s.result.model_versions?.demand_gbm,
                fraud_gbm:  s.result.model_versions?.fraud_gbm,
              },
              predictions:  s.result.predictions,
              price_buildup: s.result.price_buildup,
              source:       'historical_batch',
            }],
            scored_at: new Date().toISOString(),
            scoring_engine: `historical_batch (${rel?.display_name})`,
          });
          break;
        }
        if (s.state === 'TERMINATED' || s.result_state === 'FAILED' || s.state === 'INTERNAL_ERROR') {
          setError(`Historical score failed — state=${s.state} result_state=${s.result_state}. See ${trigger.run_page_url}`);
          break;
        }
      }
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
      <Card className="lg:col-span-5">
        <CardTitle>Quote features</CardTitle>
        <p className="text-[13px] text-mut mb-3">
          Edit any field. These flow through {current?.display_name || 'the current'} release — the same rate
          book that prices real quotes on {current?.effective_date || 'today'}.
        </p>
        <div className="grid grid-cols-2 gap-3 max-h-[560px] overflow-y-auto pr-1">
          {Object.entries(features).map(([k, v]) => (
            <label key={k} className="block">
              <span className="text-[11px] text-mut font-semibold uppercase tracking-[0.05em]">{k}</span>
              <input
                value={v ?? ''}
                onChange={e => {
                  const raw = e.target.value;
                  const num = raw !== '' && !isNaN(Number(raw)) ? Number(raw) : raw;
                  setFeatures(f => ({ ...f, [k]: num }));
                }}
                className="w-full mt-0.5 px-2 py-1 rounded border border-line text-sm focus:outline-none focus:ring-2 focus:ring-brand/50"
              />
            </label>
          ))}
        </div>
      </Card>

      <div className="lg:col-span-7 space-y-4">
        <Card>
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1">
              <CardTitle className="mb-1">Score on release</CardTitle>
              <select value={releaseId}
                      onChange={e => setReleaseId(e.target.value)}
                      className="w-full px-3 py-1.5 rounded border border-line text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand/50">
                <option value="">{current?.display_name || 'Current release'} (live)</option>
                {releases.filter(r => r.release_id !== current?.release_id).map(r => (
                  <option key={r.release_id} value={r.release_id}>
                    {r.display_name} — {r.status === 'previous_champion' ? 'previous champion' : 'archived'}
                  </option>
                ))}
              </select>
              <div className="text-[11px] text-mut mt-1.5">
                {isHistorical
                  ? <>Historical release — scored via batch job. ~1–2 min.</>
                  : <>Current release — live through <code className="bg-slate-100 px-1 rounded text-[10px]">pricing_scorer</code> endpoint. Sub-second.</>}
              </div>
            </div>
            <Btn onClick={run}
                 disabled={running || (!isHistorical && status && !status.ready)}
                 title={!isHistorical && status && !status.ready ? 'Endpoint warming up…' : ''}>
              {running ? <Loader2 className="w-4 h-4 animate-spin" /> :
               (!isHistorical && status && !status.ready) ? <Loader2 className="w-4 h-4 animate-spin" /> :
               <PlayCircle className="w-4 h-4" />}
              {running ? 'Scoring…' :
               (!isHistorical && status && !status.ready) ? 'Warming…' :
               'Run quote'}
            </Btn>
          </div>

          {batchState && running && (
            <div className="mt-3 pt-3 border-t border-line text-[11px] text-mut flex items-center justify-between">
              <span>
                <Loader2 className="w-3 h-3 animate-spin inline mr-1" />
                Batch job <code className="bg-slate-100 px-1 rounded text-[10px]">{batchState.runId}</code> — state: <span className="font-medium">{batchState.phase}</span>
              </span>
              {batchState.url && (
                <a href={batchState.url} target="_blank" rel="noreferrer"
                   className="text-brand hover:underline inline-flex items-center gap-1">
                  open run <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          )}
        </Card>

        {error && <Card className="border-red-200 bg-red-50"><span className="text-sm text-red-700">{error}</span></Card>}
        {result && <QuoteResult result={result} release={
          releases.find(r => r.release_id === releaseId) || current
        } />}
      </div>
    </div>
  );
}

function QuoteResult({ result, release }: { result: any; release: Release | null }) {
  const q = (result.quotes || [])[0];
  if (!q) return null;
  const p = q.price_buildup || {};
  const rows = [
    { label: 'Base technical (freq × sev)',       amount: p.base_premium },
    { label: 'Fraud-risk loading',                 amount: p.fraud_loading },
    { label: 'Demand-elasticity adjustment',       amount: p.demand_adj },
    { label: 'Technical premium', amount: p.technical_premium, bold: true },
    { label: 'Expense loading',                    amount: p.expense_loading },
    { label: 'Broker commission',                  amount: p.commission },
    { label: 'Gross premium (to customer)',        amount: p.gross_premium, bold: true, highlight: true },
  ];

  return (
    <Card className="overflow-hidden bg-white">
      <div className="px-4 py-3 border-b border-line bg-[#eef2ff] flex items-center justify-between">
        <div className="text-sm">
          <span className="font-bold text-ink">
            £{p.gross_premium?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </span>
          <span className="ml-2 text-mut">gross premium · {release?.display_name}</span>
        </div>
        <div className="text-[11px] text-mut">
          Scored {new Date(result.scored_at).toLocaleTimeString()} · {result.scoring_engine}
        </div>
      </div>

      <Grid cols={4} className="p-4 border-b border-line">
        <Metric label="Freq" value={q.predictions?.freq_pred?.toFixed?.(4) ?? '—'} tone="plain" />
        <Metric label="Sev" value={q.predictions?.sev_pred != null ? `£${q.predictions.sev_pred.toLocaleString()}` : '—'} tone="plain" />
        <Metric label="Demand" value={q.predictions?.demand_pred?.toFixed?.(3) ?? '—'} tone="plain" />
        <Metric label="Fraud" value={q.predictions?.fraud_pred?.toFixed?.(3) ?? '—'} tone="plain" />
      </Grid>

      <div className="p-4">
        <SectionHead>Price build-up</SectionHead>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-y-0.5 text-[13px]">
          {rows.map((r, i) => (
            <div key={i} className={`flex justify-between px-3 py-1 rounded ${r.highlight ? 'bg-[#eef2ff]' : ''}`}>
              <span className={r.bold ? 'font-bold text-ink' : 'text-ink'}>{r.label}</span>
              <span className={`tabular-nums ${r.bold ? 'font-bold text-ink' : 'text-ink'}`}>
                £{(r.amount ?? 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded bg-gray-50 border border-gray-200 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-gray-500">{label}</div>
      <div className="text-base font-semibold tabular-nums text-gray-900">{value}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// MTA Simulator — unchanged flow, but references current release in copy
// ---------------------------------------------------------------------------

// MTA flow — policy-context-aware. Provide a policy ID, the app reads its
// inception date and auto-selects the release-of-record. We re-price on that
// release (the MTA invoice's consistent answer) AND on today's live release
// (for reference). The "simulate" wording is gone — this IS the MTA reprice;
// the audit-log step is de-emphasised so the demo flow stays clean.

function MtaSimulator({ current: _current }: { current: Release | null }) {
  const [policyId, setPolicyId]   = useState('POL-100009');
  const [change, setChange]       = useState<{ field: string; value: string }>({ field: 'annual_turnover', value: '1500000' });
  const [effective, setEffective] = useState(new Date().toISOString().slice(0,10));
  const [reason, setReason]       = useState('Post-acquisition turnover bump');
  const [running, setRunning]     = useState(false);
  const [result, setResult]       = useState<any>(null);
  const [error, setError]         = useState<string | null>(null);

  // Policy preview — fetched whenever policyId changes (debounced).
  const [ctx, setCtx]             = useState<any>(null);
  const [ctxErr, setCtxErr]       = useState<string | null>(null);
  const [ctxLoading, setCtxLoad]  = useState(false);

  useEffect(() => {
    const id = policyId.trim().toUpperCase();
    if (!id) { setCtx(null); setCtxErr(null); return; }
    let cancelled = false;
    setCtxLoad(true); setCtxErr(null);
    const t = setTimeout(async () => {
      try {
        const c = await api.getPolicyContext(id);
        if (!cancelled) setCtx(c);
      } catch (e: any) {
        if (!cancelled) { setCtx(null); setCtxErr(e.message || String(e)); }
      } finally {
        if (!cancelled) setCtxLoad(false);
      }
    }, 300);
    return () => { cancelled = true; clearTimeout(t); };
  }, [policyId]);

  const reprice = async () => {
    setRunning(true); setError(null); setResult(null);
    try {
      const parsed = Number(change.value);
      const v = !isNaN(parsed) && change.value !== '' ? parsed : change.value;
      const r = await api.simulateMta({
        policy_id: policyId,
        changes: { [change.field]: v },
        effective_date: effective,
        reason,
      });
      setResult(r);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setRunning(false);
    }
  };

  // Demo policies — each in a different release window so the auto-selection
  // is visibly different.
  const demoPolicies: { id: string; label: string }[] = [
    { id: 'POL-100001', label: 'Dec 2025 inception' },
    { id: 'POL-100009', label: 'Feb 2026 inception' },
    { id: 'POL-100011', label: 'Apr 2026 inception (live)' },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
      <Card className="lg:col-span-4 space-y-3">
        <CardTitle>Mid-term adjustment</CardTitle>
        <p className="text-[13px] text-mut">
          Re-prices the policy on the release at inception (release-of-record)
          and, for reference, on today's live release.
        </p>

        <label className="block text-sm">
          <span className="text-[11px] text-mut font-bold uppercase tracking-[0.05em]">Policy ID</span>
          <input value={policyId} onChange={e => setPolicyId(e.target.value.toUpperCase())}
                 className="w-full mt-0.5 px-3 py-1.5 rounded border border-line font-mono text-sm focus:outline-none focus:ring-2 focus:ring-brand/50" />
        </label>
        <div className="flex flex-wrap gap-1.5">
          {demoPolicies.map(d => (
            <Btn key={d.id}
                 tone={policyId === d.id ? 'primary' : 'ghost'}
                 onClick={() => setPolicyId(d.id)}
                 className="text-[10px]">
              {d.id} · {d.label}
            </Btn>
          ))}
        </div>

        <PolicyContextCard ctx={ctx} loading={ctxLoading} err={ctxErr} />

        <label className="block text-sm">
          <span className="text-[11px] text-mut font-bold uppercase tracking-[0.05em]">Field to change</span>
          <select value={change.field} onChange={e => setChange(c => ({ ...c, field: e.target.value }))}
                  className="w-full mt-0.5 px-3 py-1.5 rounded border border-line text-sm focus:outline-none focus:ring-2 focus:ring-brand/50">
            {['annual_turnover', 'sum_insured', 'current_premium', 'industry_risk_tier',
              'construction_type', 'ccj_count', 'flood_zone_rating', 'employee_count_est'].map(f => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="text-[11px] text-mut font-bold uppercase tracking-[0.05em]">New value</span>
          <input value={change.value} onChange={e => setChange(c => ({ ...c, value: e.target.value }))}
                 className="w-full mt-0.5 px-3 py-1.5 rounded border border-line text-sm focus:outline-none focus:ring-2 focus:ring-brand/50" />
        </label>
        <label className="block text-sm">
          <span className="text-[11px] text-mut font-bold uppercase tracking-[0.05em]">Effective date</span>
          <input type="date" value={effective} onChange={e => setEffective(e.target.value)}
                 className="w-full mt-0.5 px-3 py-1.5 rounded border border-line text-sm focus:outline-none focus:ring-2 focus:ring-brand/50" />
        </label>
        <label className="block text-sm">
          <span className="text-[11px] text-mut font-bold uppercase tracking-[0.05em]">Change reason</span>
          <input value={reason} onChange={e => setReason(e.target.value)}
                 className="w-full mt-0.5 px-3 py-1.5 rounded border border-line text-sm focus:outline-none focus:ring-2 focus:ring-brand/50" />
        </label>
        <Btn tone="primary" onClick={reprice}
             disabled={running || !ctx}
             className="w-full justify-center">
          {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {running ? 'Re-pricing…' : 'Re-price policy'}
        </Btn>
      </Card>

      <div className="lg:col-span-8 space-y-3">
        {error && <Card className="border-red-200 bg-red-50"><span className="text-sm text-red-700">{error}</span></Card>}
        {!result && !running && (
          <Card className="text-[13px] text-mut italic">
            {ctx
              ? <>Ready to re-price <code className="bg-slate-100 px-1 rounded text-[10px]">{ctx.policy_id}</code> on <strong>{ctx.inception_release?.display_name}</strong> (release-of-record).
                  Today's live release (<strong>{ctx.current_release?.display_name}</strong>) shown for reference.</>
              : <>Pick a policy ID — the system will auto-select the release the policy was bound on.</>}
          </Card>
        )}
        {result && <MtaResult r={result} />}
      </div>
    </div>
  );
}

function PolicyContextCard({ ctx, loading, err }: { ctx: any; loading: boolean; err: string | null }) {
  if (loading) return (
    <Card className="bg-slate-50 border-line">
      <Loader2 className="w-3.5 h-3.5 animate-spin inline mr-1.5" /> <span className="text-xs text-mut">Looking up policy…</span>
    </Card>
  );
  if (err) return (
    <Card className="bg-red-50 border-red-200"><span className="text-xs text-red-700">{err}</span></Card>
  );
  if (!ctx) return null;
  const ir = ctx.inception_release;
  const cr = ctx.current_release;
  const isLive = ir && cr && ir.release_id === cr.release_id;
  return (
    <Card className="bg-[#faf5ff] border-[#ddd6fe]">
      <CardTitle className="flex items-center gap-1 mb-2">
        <FileText className="w-3 h-3 text-purple-600" /> Policy context
      </CardTitle>
      <div className="text-xs text-ink space-y-0.5">
        <div className="flex items-center gap-1.5">
          <Calendar className="w-3 h-3 text-purple-600" />
          Bound <span className="font-semibold">{ctx.inception_date}</span>
          {' '}· renews <span className="font-semibold">{ctx.renewal_date}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Tag className="w-3 h-3 text-purple-600" />
          Premium <span className="font-semibold">£{Number(ctx.current_premium || 0).toLocaleString()}</span>
          {' '}· {ctx.industry_risk_tier || '—'} tier
          {ctx.region ? ` · ${ctx.region}` : ''}
        </div>
      </div>
      {ir && (
        <Card className="bg-white border-[#ddd6fe] mt-2 p-3">
          <div className="text-[10px] uppercase tracking-[0.08em] font-bold text-purple-700 mb-1">
            Auto-selected release-of-record
          </div>
          <div className="text-sm font-semibold text-ink flex items-center gap-2">
            {ir.display_name}
            {isLive && (
              <Pill tone="green">also live</Pill>
            )}
          </div>
          <div className="text-[10px] text-mut mt-0.5">
            effective {ir.effective_date} · {ir.status}
          </div>
          <div className="flex flex-wrap gap-1 mt-1.5">
            {Object.entries(ir.model_versions || {}).filter(([_, v]) => v).map(([k, v]) => (
              <Pill key={k} tone="slate" className="text-[10px]">
                {k}: v{String(v)}
              </Pill>
            ))}
          </div>
        </Card>
      )}
      {!isLive && cr && (
        <div className="text-[11px] text-mut mt-2">
          Live release <span className="font-semibold text-ink">{cr.display_name}</span> ({cr.effective_date})
          shown for reference.
        </div>
      )}
    </Card>
  );
}

function MtaResult({ r }: { r: any }) {
  const ir = r.inception_release;
  const cr = r.current_release;
  const onIncep = r.on_inception_release;
  const onCur   = r.on_current_release;
  const isLive  = ir && cr && ir.release_id === cr.release_id;

  const incepGross = onIncep?.after?.price_buildup?.gross_premium;
  const curGross   = onCur?.after?.price_buildup?.gross_premium;
  const crossDelta = (typeof incepGross === 'number' && typeof curGross === 'number')
    ? curGross - incepGross : null;
  const crossPct   = (typeof incepGross === 'number' && incepGross > 0 && crossDelta != null)
    ? (crossDelta / incepGross) * 100 : null;

  return (
    <div className="space-y-3">
      <Card>
        <div className="flex items-baseline justify-between flex-wrap gap-2 mb-3">
          <div className="text-sm font-bold text-ink">
            {r.policy_id} · effective {r.effective_date}
          </div>
          <div className="text-[11px] text-mut">
            inception {r.inception_date} · {r.remaining_days} / {r.term_days} days remaining · prorating {Math.round(r.remaining_frac * 100)}%
          </div>
        </div>

        <Grid cols={isLive ? 1 : 2} className="gap-3 mb-3">
          <RepricedCard
            heading="Release-of-record"
            sub={ir ? `${ir.display_name} · effective ${ir.effective_date}` : ''}
            block={onIncep}
            versions={ir?.model_versions}
            primary
          />
          {!isLive && (
            <RepricedCard
              heading="Live release (reference)"
              sub={cr ? `${cr.display_name} · effective ${cr.effective_date}` : ''}
              block={onCur}
              versions={cr?.model_versions}
            />
          )}
        </Grid>

        {!isLive && crossDelta != null && (
          <Card className="bg-slate-50 border-line text-xs text-ink">
            <span className="font-semibold">Cross-release reconciliation:</span>{' '}
            today's live release prices this policy{' '}
            <span className={`font-semibold ${crossDelta < 0 ? 'text-emerald-700' : 'text-red-700'}`}>
              {crossDelta > 0 ? '+' : ''}£{Math.abs(crossDelta).toLocaleString(undefined, {maximumFractionDigits: 0})}
              {crossPct != null && <> ({crossPct > 0 ? '+' : ''}{crossPct.toFixed(1)}%)</>}
            </span>
            {' '}vs release-of-record. MTA invoice uses release-of-record for consistency.
          </Card>
        )}
        {isLive && (
          <Card className="bg-emerald-50 border-emerald-200 text-xs text-emerald-900">
            <span className="font-semibold">Inception falls inside the live release window.</span>{' '}
            Live release IS the release-of-record — only one re-price needed.
          </Card>
        )}
      </Card>

      <Card>
        <SectionHead>Audit trail</SectionHead>
        <div className="text-[11px] text-mut">
          Recorded as <code className="bg-slate-100 px-1 rounded text-[10px]">mta_simulated</code> event
          with version chain; priced quote written to <code className="bg-slate-100 px-1 rounded text-[10px]">inference_logs</code> with <code className="bg-slate-100 px-1 rounded text-[10px]">is_mta=true</code>.
        </div>
      </Card>
    </div>
  );
}

function RepricedCard({ heading, sub, block, versions, primary }:
  { heading: string; sub: string; block: any; versions: any; primary?: boolean }) {
  const before = block?.before?.price_buildup;
  const after  = block?.after?.price_buildup;
  const prorated = block?.prorated_delta;
  const full = block?.full_delta;
  return (
    <Card className={primary ? 'bg-[#eef2ff] border-[#ddd6fe]' : 'bg-slate-50/50 border-line'}>
      <div className="flex items-baseline justify-between mb-2 gap-2">
        <div>
          <div className={`text-[10px] uppercase tracking-[0.08em] font-bold ${primary ? 'text-purple-700' : 'text-mut'}`}>
            {heading}
          </div>
          <div className="text-sm font-semibold text-ink">{sub}</div>
        </div>
        {primary && (
          <Pill tone="blue" className="text-[9px]">primary</Pill>
        )}
      </div>
      <Grid cols={3} className="gap-2 mb-2">
        <MiniTile label="Before"   value={`£${(before?.gross_premium || 0).toLocaleString()}`} />
        <MiniTile label="After"    value={`£${(after?.gross_premium  || 0).toLocaleString()}`} />
        <MiniTile
          label="Prorated"
          value={`${(prorated || 0) >= 0 ? '+' : ''}£${(prorated || 0).toLocaleString()}`}
          tone={(prorated || 0) > 0 ? 'up' : (prorated || 0) < 0 ? 'down' : 'neutral'}
          sub={`Annual ${(full || 0) >= 0 ? '+' : ''}£${(full || 0).toLocaleString()}`}
        />
      </Grid>
      {versions && (
        <div className="flex flex-wrap gap-1">
          {Object.entries(versions).filter(([_, v]) => v).map(([k, v]) => (
            <Pill key={k} tone="slate" className="text-[10px]">
              {k}: v{String(v)}
            </Pill>
          ))}
        </div>
      )}
    </Card>
  );
}

function MiniTile({ label, value, tone, sub }:
  { label: string; value: string; tone?: 'up' | 'down' | 'neutral'; sub?: string }) {
  const metricTone = tone === 'up'   ? 'amber' as const
                   : tone === 'down' ? 'green' as const
                   : 'plain' as const;
  return (
    <Metric label={label} value={value} sub={sub} tone={metricTone} />
  );
}

// ---------------------------------------------------------------------------
// Release History — timeline of monthly releases
// ---------------------------------------------------------------------------

function ReleaseHistory({ releases }: { releases: Release[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [comparing, setComparing] = useState<Record<string, any>>({});

  const triggerCompare = async (r: Release) => {
    setComparing(s => ({ ...s, [r.release_id]: { state: 'queuing' } }));
    try {
      const res = await api.compareReleases(r.release_id, 2000);
      setComparing(s => ({ ...s, [r.release_id]: { state: 'done', result: res } }));
    } catch (e: any) {
      setComparing(s => ({ ...s, [r.release_id]: { state: 'error', error: e.message || String(e) } }));
    }
  };

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between mb-3">
        <CardTitle className="mb-0">Releases</CardTitle>
        <span className="text-xs text-mut">{releases.length} total</span>
      </div>
      <div className="divide-y">
        {releases.map(r => {
          const open = expanded === r.release_id;
          const comp = comparing[r.release_id];
          const isChampion = r.status === 'champion';
          const isPrevious = r.status === 'previous_champion';
          return (
            <div key={r.release_id}>
              <button onClick={() => setExpanded(open ? null : r.release_id)}
                      className="w-full flex items-center justify-between px-3 py-3 hover:bg-slate-50 text-left transition">
                <div className="flex items-center gap-2">
                  {open ? <ChevronDown className="w-4 h-4 text-mut" /> : <ChevronRight className="w-4 h-4 text-mut" />}
                  <div>
                    <div className="font-medium text-ink">{r.display_name}</div>
                    <div className="text-[11px] text-mut">
                      Effective {r.effective_date} · approved by {(r.approved_by || '-').split('@')[0]}
                    </div>
                  </div>
                </div>
                <Pill tone={isChampion ? 'green' : isPrevious ? 'blue' : 'slate'} className="text-[10px]">
                  {r.status}
                </Pill>
              </button>
              {open && (
                <div className="px-3 pb-3 pt-2 bg-slate-50/50 space-y-3">
                  {r.narrative && (
                    <div className="text-[13px] text-ink italic leading-relaxed">{r.narrative}</div>
                  )}
                  <Grid cols={5}>
                    <VersionChip label="Frequency GLM" v={r.freq_glm_version} />
                    <VersionChip label="Severity GLM"  v={r.sev_glm_version} />
                    <VersionChip label="Demand GBM"    v={r.demand_gbm_version} />
                    <VersionChip label="Fraud GBM"     v={r.fraud_gbm_version} />
                    <VersionChip label="Rating engine" v={r.rating_engine_version} highlight />
                  </Grid>

                  {!isChampion && (
                    <div>
                      {comp?.state === 'done' ? (
                        <div className="flex flex-col gap-2">
                          <div className="text-xs font-semibold text-ink">Batch comparison queued — 4 runs</div>
                          <div className="flex flex-wrap gap-1">
                            {Object.entries(comp.result.run_page_urls || {}).map(([fam, url]: [string, any]) => (
                              <a key={fam} href={url as string} target="_blank" rel="noreferrer"
                                 className="text-[11px] px-2 py-0.5 rounded border border-brand bg-[#eef2ff] text-brand hover:bg-[#dbeafe] inline-flex items-center gap-1">
                                {fam} <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            ))}
                          </div>
                          <div className="text-[11px] text-mut">
                            Each run scores 2,000 policies. ~2 min per family. Results land in history.
                          </div>
                        </div>
                      ) : comp?.state === 'error' ? (
                        <div className="text-xs text-red-700">Failed: {comp.error}</div>
                      ) : (
                        <Btn tone="ghost" onClick={() => triggerCompare(r)}
                             disabled={comp?.state === 'queuing'}
                             className="text-xs">
                          {comp?.state === 'queuing' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <GitCompareArrows className="w-3.5 h-3.5" />}
                          {comp?.state === 'queuing' ? 'Queuing…' : `Compare ${r.display_name}`}
                        </Btn>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
