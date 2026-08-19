import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, GitCompare, TrendingUp, ShieldCheck, CheckCircle2, XCircle, Loader2, Download, Upload } from 'lucide-react';
import { api } from '../lib/api';
import {
  Page, PageHeader, OnThisPage, Card, Section, Pill, Metric, AskBox, UnderTheHood, Skeleton, Loading,
} from '../components/ui';

type Tab = 'diff' | 'impact' | 'quality' | 'upload' | 'approval';

export default function DatasetDetail() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const [tab, setTab] = useState<Tab>('diff');
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDatasets().then(setDatasets).finally(() => setLoading(false));
  }, []);

  // When the dataset category doesn't support the current tab (e.g. switching
  // from an external feed to a claims dataset that only has Data Quality), drop
  // back to the first available tab.
  useEffect(() => {
    if (!datasets.length || !datasetId) return;
    const cur = datasets.find((d) => d.id === datasetId);
    if (!cur) return;
    const cat = cur.category || 'external_vendor';
    const valid =
      cat === 'internal'       ? ['quality']
    : cat === 'reference_data' ? ['quality', 'upload']
    :                            ['diff', 'quality', 'impact', 'upload', 'approval'];
    if (!valid.includes(tab)) setTab(valid[0] as Tab);
  }, [datasets, datasetId, tab]);

  const ds = datasets.find((d) => d.id === datasetId);

  if (loading) return <div className="p-8 text-center text-gray-500">Loading...</div>;
  if (!ds) return <div className="p-8 text-center text-red-500">Dataset not found</div>;

  const category = ds.category || 'external_vendor';
  const isInternal = category === 'internal';
  const isReference = category === 'reference_data';

  // Internal datasets are the source of truth — no version-to-version diff,
  // no shadow-pricing impact (they ARE the policies being priced), no approval flow.
  // They just show the data-quality view so an actuary can verify freshness + completeness.
  const tabs: { id: Tab; label: string; icon: any }[] = isInternal
    ? [{ id: 'quality', label: 'Data Quality', icon: ShieldCheck }]
    : isReference
    ? [
        { id: 'quality', label: 'Data Quality', icon: ShieldCheck },
        { id: 'upload',  label: 'Download',     icon: Upload },
      ]
    : [
        { id: 'diff',    label: 'Data Changes',     icon: GitCompare },
        { id: 'quality', label: 'Data Quality',     icon: ShieldCheck },
        { id: 'impact',  label: 'Impact Analysis',  icon: TrendingUp },
        { id: 'upload',  label: 'Upload / Download', icon: Upload },
        { id: 'approval',label: 'Approve / Reject', icon: CheckCircle2 },
      ];

  return (
    <Page>
      <Link to="/datasets" className="inline-flex items-center gap-1.5 text-[12.5px] text-brand hover:underline mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to datasets
      </Link>

      <PageHeader
        eyebrow="Bricksurance SE · Data Ingestion"
        title={ds.display_name}
        subtitle={`${ds.description} — Source: ${ds.source} · Join key: ${ds.join_key}`}
        icon={GitCompare}
      />

      <OnThisPage>
        Inspect the data changes since the last approval, see the impact on your portfolio, check data quality, and approve or reject before it enters pricing.
      </OnThisPage>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-line mb-5">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-[13px] font-medium border-b-2 transition-colors ${
              tab === t.id
                ? 'border-brand text-brand'
                : 'border-transparent text-mut hover:text-ink hover:border-line'
            }`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'diff' && <DiffTab datasetId={datasetId!} />}
      {tab === 'impact' && <ImpactTab datasetId={datasetId!} />}
      {tab === 'quality' && <QualityTab datasetId={datasetId!} />}
      {tab === 'upload' && <UploadDownloadTab datasetId={datasetId!} datasetName={ds.display_name} />}
      {tab === 'approval' && <ApprovalTab datasetId={datasetId!} />}

      <UnderTheHood
        title="Dataset Detail"
        lines={[
          { component: 'Data diff', detail: 'Row-by-row comparison between pending (raw/bronze) and current approved (silver)' },
          { component: 'Impact analysis', detail: 'Shadow pricing on 100% of affected policies to show exact premium impact' },
          { component: 'Data quality', detail: 'DLT expectations + completeness metrics + freshness checks' },
          { component: 'Approval workflow', detail: 'HITL gate with actuary notes; audit trail immutable' },
        ]}
      />
    </Page>
  );
}

// ---------------------------------------------------------------------------
// Tab 1: Data Changes (Diff)
// ---------------------------------------------------------------------------

function DiffTab({ datasetId }: { datasetId: string }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDatasetDiff(datasetId).then(setData).finally(() => setLoading(false));
  }, [datasetId]);

  if (loading) return <Loading />;
  if (!data) return <Card className="border-red-200 text-red-600 text-sm">Failed to load diff</Card>;

  const s = data.summary;

  return (
    <div className="space-y-5">
      {/* Summary metrics */}
      <div className="grid grid-cols-4 gap-3">
        <Metric label="Raw (Pending)" value={Number(s.raw_total).toLocaleString()} tone="blue" />
        <Metric label="Silver (Current)" value={Number(s.silver_total).toLocaleString()} tone="plain" />
        <Metric label="New Rows" value={Number(s.new_rows).toLocaleString()} tone="green" />
        <Metric label="Removed Rows" value={Number(s.removed_rows).toLocaleString()} tone="amber" />
      </div>

      {/* Changed rows */}
      {data.changed_rows.length > 0 && (
        <Section title={`Changed Records (${data.changed_rows.length} shown)`}>
          <Card className="overflow-x-auto p-0">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-line">
                  <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">{data.key_column}</th>
                  {data.compare_columns.map((col: string) => (
                    <th key={col} colSpan={2} className="px-3 py-2 text-center font-medium text-mut text-xs uppercase">{col}</th>
                  ))}
                </tr>
                <tr className="bg-slate-50 border-b border-line">
                  <th></th>
                  {data.compare_columns.map((col: string) => (
                    <>
                      <th key={`old_${col}`} className="px-3 py-1 text-center text-[11px] text-mut">Old</th>
                      <th key={`new_${col}`} className="px-3 py-1 text-center text-[11px] text-brand">New</th>
                    </>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.changed_rows.slice(0, 20).map((row: any, i: number) => (
                  <tr key={i} className="border-b border-line hover:bg-blue-50/30">
                    <td className="px-3 py-2 font-mono text-xs text-mut">{row[data.key_column]}</td>
                    {data.compare_columns.map((col: string) => {
                      const oldVal = row[`old_${col}`];
                      const newVal = row[`new_${col}`];
                      const changed = String(oldVal) !== String(newVal);
                      return (
                        <>
                          <td key={`old_${col}_${i}`} className="px-3 py-2 text-center text-mut text-sm">{formatVal(oldVal)}</td>
                          <td key={`new_${col}_${i}`} className={`px-3 py-2 text-center font-medium text-sm ${changed ? 'text-brand bg-blue-50' : 'text-ink'}`}>
                            {formatVal(newVal)}
                          </td>
                        </>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </Section>
      )}

      {/* New rows */}
      {data.new_rows.length > 0 && (
        <Section title={`New Records (${data.new_rows.length} shown)`}>
          <SimpleTable rows={data.new_rows} />
        </Section>
      )}

      {/* Removed rows */}
      {data.removed_rows.length > 0 && (
        <Section title={`Removed Records (${data.removed_rows.length} shown)`}>
          <SimpleTable rows={data.removed_rows} />
        </Section>
      )}

      {data.changed_rows.length === 0 && data.new_rows.length === 0 && data.removed_rows.length === 0 && (
        <Card className="bg-emerald-50 border-emerald-200 text-center p-6">
          <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
          <p className="text-emerald-700 font-medium">No differences detected between raw and silver versions.</p>
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 2: Impact Analysis
// ---------------------------------------------------------------------------

// AI overview + ask-anything box — leads the Impact tab. Uses the
// ingestion-impact explainability agent (Claude on the Databricks FM API).
function AiImpactLead({ datasetId, pi }: { datasetId: string; pi: any }) {
  const label = datasetId.replace(/_/g, ' ');
  const ctx = pi?.affected_policies
    ? `${pi.affected_policies} of ${pi.total_policies} policies affected (${pi.affected_pct}%).`
    : '';

  const onAsk = async (q: string) => {
    const r = await api.runExplainability(`${q} (Context: ${label} data update. ${ctx})`);
    return r?.explanation?.explanation || r?.transparency?.raw_response ||
      (r?.success === false ? `Agent error: ${r?.error || r?.transparency?.error || 'unavailable'}` : 'No answer returned.');
  };

  const seedQ = `In 3 short sentences, summarise the pricing impact of the ${label} data update and say what a pricing actuary should look at first. ${ctx}`;

  return (
    <AskBox
      title="Impact Analysis"
      subtitle="Why did premiums change? Ask AI to trace data updates to pricing impact."
      examples={[
        'Why did premiums change for this update?',
        'Which risk segments are most affected?',
        'Is the premium impact significant or noise?',
      ]}
      onAsk={onAsk}
      placeholder="Ask a detailed question about this impact…"
      seedQuestion={seedQ}
    />
  );
}

function ImpactTab({ datasetId }: { datasetId: string }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDatasetImpact(datasetId).then(setData).finally(() => setLoading(false));
  }, [datasetId]);

  if (loading) return <Loading />;
  if (!data) return <Card className="border-red-200 text-red-600 text-sm">Failed to load impact analysis</Card>;

  const dd = data.data_diff || {};
  const pi = data.portfolio_impact || {};
  const rs = data.risk_summary || {};

  return (
    <div className="space-y-5">
      {/* Lead with the AI overview + an ask-anything box */}
      <AiImpactLead datasetId={datasetId} pi={pi} />

      {/* ── Section 1: Data Diff Summary ── */}
      <Section title="Data Change Summary">
        <div className="grid grid-cols-4 gap-3 mb-4">
          <Metric label="Incoming Rows" value={dd.raw_count?.toLocaleString() || '0'} tone="blue" />
          <Metric label="Current Rows" value={dd.silver_count?.toLocaleString() || '0'} tone="plain" />
          <Metric label="New Rows" value={dd.new_rows?.toLocaleString() || '0'} tone="green" />
          <Metric label="Removed Rows" value={dd.removed_rows?.toLocaleString() || '0'} tone="amber" />
        </div>
        {dd.column_shifts?.length > 0 && (
          <Card className="overflow-x-auto p-0">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-line">
                  <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Column</th>
                  <th className="px-3 py-2 text-right font-medium text-mut text-xs uppercase">Old Mean</th>
                  <th className="px-3 py-2 text-right font-medium text-mut text-xs uppercase">New Mean</th>
                  <th className="px-3 py-2 text-right font-medium text-mut text-xs uppercase">Shift</th>
                  <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Direction</th>
                </tr>
              </thead>
              <tbody>
                {dd.column_shifts.map((s: any, i: number) => (
                  <tr key={i} className="border-b border-line hover:bg-slate-50">
                    <td className="px-3 py-2 font-mono text-xs text-mut">{s.column}</td>
                    <td className="px-3 py-2 text-right text-mut text-sm">{s.old_mean}</td>
                    <td className="px-3 py-2 text-right font-medium text-ink text-sm">{s.new_mean}</td>
                    <td className={`px-3 py-2 text-right font-semibold text-sm ${
                      s.severity === 'high' ? 'text-red-600' : s.severity === 'medium' ? 'text-amber-600' : 'text-emerald-600'
                    }`}>{s.shift_pct > 0 ? '+' : ''}{s.shift_pct}%</td>
                    <td className="px-3 py-2">
                      <div className="w-20 h-3 bg-slate-100 rounded-full overflow-hidden relative">
                        <div className={`absolute top-0 h-full rounded-full ${s.shift_pct >= 0 ? 'bg-red-400 left-1/2' : 'bg-emerald-400 right-1/2'}`}
                             style={{ width: `${Math.min(50, Math.abs(s.shift_pct) * 2.5)}%` }} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </Section>

      {/* ── Section 2: Portfolio Impact ── */}
      {pi.affected_policies > 0 ? (
        <>
          <Section title="Portfolio Impact — Affected Policies">
            <div className="grid grid-cols-4 gap-3 mb-4">
              <Metric label="Affected Policies" value={`${pi.affected_policies?.toLocaleString()} of ${pi.total_policies?.toLocaleString()}`} sub={`(${pi.affected_pct}%)`} tone="blue" />
              <Metric label="Total Premium Delta" value={`£${formatGwp(pi.premium_delta_total)}`} tone={pi.premium_delta_total > 0 ? 'amber' : 'green'} />
              <Metric label="Avg Delta / Policy" value={`£${pi.premium_delta_avg?.toLocaleString()}`} tone="plain" />
              <Metric label="Flagged (>10%)" value={pi.flagged_count?.toLocaleString() || '0'} tone={pi.flagged_count > 0 ? 'amber' : 'green'} />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <Card className="bg-red-50 border-red-200 text-center p-3">
                <div className="text-2xl font-bold text-red-700">{pi.policies_increase?.toLocaleString()}</div>
                <div className="text-[11px] text-red-600 mt-1 font-bold uppercase">Premium Increase</div>
              </Card>
              <Card className="bg-emerald-50 border-emerald-200 text-center p-3">
                <div className="text-2xl font-bold text-emerald-700">{pi.policies_decrease?.toLocaleString()}</div>
                <div className="text-[11px] text-emerald-600 mt-1 font-bold uppercase">Premium Decrease</div>
              </Card>
              <Card className="bg-slate-50 border-slate-200 text-center p-3">
                <div className="text-2xl font-bold text-slate-700">{pi.policies_unchanged?.toLocaleString()}</div>
                <div className="text-[11px] text-slate-600 mt-1 font-bold uppercase">Unchanged</div>
              </Card>
            </div>
          </Section>

          {/* Histogram */}
          {pi.histogram?.length > 0 && (
            <Section title="Premium Change Distribution">
              <div className="flex items-end gap-1.5 h-40">
                {pi.histogram.map((h: any, i: number) => {
                  const maxCount = Math.max(...pi.histogram.map((x: any) => x.count || 0));
                  const heightPct = maxCount > 0 ? (h.count / maxCount) * 100 : 0;
                  const isNegative = h.bucket.includes('-');
                  const isExtreme = h.bucket.includes('10');
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center">
                      <div className="text-xs font-medium text-ink mb-1">{h.count}</div>
                      <div className={`w-full rounded-t transition-all ${
                        isExtreme ? (isNegative ? 'bg-emerald-500' : 'bg-red-500')
                        : isNegative ? 'bg-emerald-300' : h.bucket === '0%' ? 'bg-slate-300' : 'bg-red-300'
                      }`} style={{ height: `${heightPct}%`, minHeight: h.count > 0 ? '4px' : '0' }} />
                      <div className="text-[10px] text-mut mt-1 text-center leading-tight">{h.bucket}</div>
                    </div>
                  );
                })}
              </div>
            </Section>
          )}

          {/* By Industry */}
          {pi.by_industry?.length > 0 && (
            <Section title="Impact by Class of Business">
              <Card className="overflow-x-auto p-0">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="bg-slate-50 border-b border-line">
                      <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Industry Tier</th>
                      <th className="px-3 py-2 text-right font-medium text-mut text-xs uppercase">Policies</th>
                      <th className="px-3 py-2 text-right font-medium text-mut text-xs uppercase">GWP</th>
                      <th className="px-3 py-2 text-right font-medium text-mut text-xs uppercase">Total Delta</th>
                      <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Impact</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pi.by_industry.map((row: any, i: number) => {
                      const maxDelta = Math.max(...pi.by_industry.map((x: any) => Math.abs(x.total_delta || 0)));
                      const barPct = maxDelta > 0 ? Math.abs(row.total_delta) / maxDelta * 100 : 0;
                      return (
                        <tr key={i} className="border-b border-line hover:bg-slate-50">
                          <td className="px-3 py-2 font-medium text-ink">{row.industry}</td>
                          <td className="px-3 py-2 text-right text-ink">{row.policies?.toLocaleString()}</td>
                          <td className="px-3 py-2 text-right text-ink">£{formatGwp(row.gwp)}</td>
                          <td className={`px-3 py-2 text-right font-semibold ${row.total_delta > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                            {row.total_delta > 0 ? '+' : ''}£{formatGwp(row.total_delta)}
                          </td>
                          <td className="px-3 py-2">
                            <div className="w-24 h-3 bg-slate-100 rounded-full overflow-hidden">
                              <div className={`h-full rounded-full ${row.total_delta > 0 ? 'bg-red-400' : 'bg-emerald-400'}`}
                                   style={{ width: `${barPct}%` }} />
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </Card>
            </Section>
          )}

          {/* By Region */}
          {pi.by_region?.length > 0 && (
            <Section title="Geographic Distribution of Impact">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
                {pi.by_region.map((row: any, i: number) => (
                  <Card key={i} className={`text-center p-3 ${
                    row.total_delta > 0 ? 'bg-red-50 border-red-200' : row.total_delta < 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <div className="font-bold text-ink">{row.region}</div>
                    <div className="text-[11px] text-mut">{row.policies} policies</div>
                    <div className={`text-sm font-semibold mt-1 ${row.total_delta > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                      {row.total_delta > 0 ? '+' : ''}£{formatGwp(row.total_delta)}
                    </div>
                  </Card>
                ))}
              </div>
            </Section>
          )}

          {/* Flagged Policies */}
          {pi.flagged_policies?.length > 0 && (
            <Section title={`Policies Requiring Attention (${pi.flagged_count} with >10% change)`}>
              <Card className="overflow-x-auto p-0">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="bg-slate-50 border-b border-line">
                      <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Policy ID</th>
                      <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Postcode</th>
                      <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Industry</th>
                      <th className="px-3 py-2 text-right font-medium text-mut text-xs uppercase">Current Premium</th>
                      <th className="px-3 py-2 text-right font-medium text-mut text-xs uppercase">Delta</th>
                      <th className="px-3 py-2 text-right font-medium text-mut text-xs uppercase">Change %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pi.flagged_policies.slice(0, 15).map((row: any, i: number) => (
                      <tr key={i} className="border-b border-line hover:bg-red-50/30">
                        <td className="px-3 py-2 font-mono text-xs text-mut">{row.policy_id}</td>
                        <td className="px-3 py-2 text-ink">{row.postcode}</td>
                        <td className="px-3 py-2 text-ink">{row.industry}</td>
                        <td className="px-3 py-2 text-right text-ink">£{row.current_premium?.toLocaleString()}</td>
                        <td className={`px-3 py-2 text-right font-semibold ${row.premium_delta > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                          {row.premium_delta > 0 ? '+' : ''}£{row.premium_delta?.toLocaleString()}
                        </td>
                        <td className="px-3 py-2 text-right">
                          <Pill tone={Math.abs(row.delta_pct) > 20 ? 'red' : 'amber'}>{row.delta_pct > 0 ? '+' : ''}{row.delta_pct}%</Pill>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </Section>
          )}
        </>
      ) : (
        <Card className="bg-emerald-50 border-emerald-200 text-center p-6">
          <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
          <p className="text-emerald-700 font-medium">No pricing impact detected — the new data matches current values.</p>
        </Card>
      )}

      {/* ── Section 3: Risk Summary ── */}
      {rs.score_type && (
        <Section title={`Risk Score Analysis — ${rs.score_type}`}>
          {rs.score_shift && (
            <div className="grid grid-cols-5 gap-3 mb-4">
              <Metric label={`Old Avg ${rs.score_type}`} value={String(rs.score_shift.old_avg_score ?? '—')} tone="plain" />
              <Metric label={`New Avg ${rs.score_type}`} value={String(rs.score_shift.new_avg_score ?? '—')} tone="blue" />
              <Metric label="Worsened" value={String(rs.score_shift.worsened ?? 0)} tone="amber" />
              <Metric label="Improved" value={String(rs.score_shift.improved ?? 0)} tone="green" />
              <Metric label="Unchanged" value={String(rs.score_shift.unchanged ?? 0)} tone="plain" />
            </div>
          )}
          {rs.tier_migration?.length > 0 && (
            <Card className="overflow-x-auto p-0">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-line">
                    <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">From Tier</th>
                    <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">To Tier</th>
                    <th className="px-3 py-2 text-right font-medium text-mut text-xs uppercase">Count</th>
                    <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Direction</th>
                  </tr>
                </thead>
                <tbody>
                  {rs.tier_migration.map((row: any, i: number) => {
                    const from = row.old_tier;
                    const to = row.new_tier;
                    const key = Object.keys(row).find(k => k !== 'old_tier' && k !== 'new_tier') || '';
                    const count = row[key] || 0;
                    const worsened = (from === 'Low' && to !== 'Low') || (from === 'Medium' && to === 'High') ||
                                     (from === 'Prime' && to !== 'Prime') || (from === 'Standard' && (to === 'Sub-Standard' || to === 'High Risk'));
                    const improved = (to === 'Low' && from !== 'Low') || (to === 'Medium' && from === 'High') ||
                                     (to === 'Prime' && from !== 'Prime');
                    return (
                      <tr key={i} className={`border-b border-line ${worsened ? 'bg-red-50/40' : improved ? 'bg-emerald-50/40' : ''}`}>
                        <td className="px-3 py-2 font-medium text-ink">{from}</td>
                        <td className="px-3 py-2 font-medium text-ink">{to}</td>
                        <td className="px-3 py-2 text-right text-ink">{Number(count).toLocaleString()}</td>
                        <td className="px-3 py-2">
                          {from === to ? <Pill tone="slate">No change</Pill> :
                           worsened ? <Pill tone="red">Risk increased</Pill> :
                           improved ? <Pill tone="green">Risk decreased</Pill> :
                           <Pill tone="amber">Shifted</Pill>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Card>
          )}
        </Section>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 3: Data Quality
// ---------------------------------------------------------------------------

function QualityTab({ datasetId }: { datasetId: string }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDatasetQuality(datasetId).then(setData).finally(() => setLoading(false));
  }, [datasetId]);

  if (loading) return <Loading />;
  if (!data) return <Card className="border-red-200 text-red-600 text-sm">Failed to load quality metrics</Card>;

  const passRateTone = data.dq_pass_rate >= 95 ? 'green' : data.dq_pass_rate >= 85 ? 'amber' : 'plain';

  return (
    <div className="space-y-5">
      {/* Top-line metrics */}
      <div className="grid grid-cols-4 gap-3">
        <Metric label="Raw Rows" value={Number(data.raw_row_count).toLocaleString()} tone="blue" />
        <Metric label="Silver Rows (passed DQ)" value={Number(data.silver_row_count).toLocaleString()} tone="green" />
        <Metric label="Rows Dropped" value={Number(data.rows_dropped).toLocaleString()} tone="amber" />
        <Metric
          label="DQ Pass Rate"
          value={`${data.dq_pass_rate}%`}
          tone={passRateTone}
        />
      </div>

      {/* Freshness */}
      <Card className={`border-l-4 ${data.freshness_status === 'fresh' ? 'bg-emerald-50 border-l-emerald-500' : 'bg-amber-50 border-l-amber-500'} p-4`}>
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-semibold text-ink">Data Freshness</h4>
            <p className="text-[13px] text-mut">Last ingested: {data.last_ingested || 'Never'}</p>
          </div>
          <Pill tone={data.freshness_status === 'fresh' ? 'green' : 'amber'}>
            {data.freshness_status === 'fresh' ? 'Fresh' : 'Stale'}
          </Pill>
        </div>
      </Card>

      {/* DQ Expectations */}
      <Section title="Data Quality Expectations">
        <Card className="overflow-x-auto p-0">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-line">
                <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Expectation</th>
                <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Rule</th>
                <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Action</th>
                <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.expectations?.map((exp: any, i: number) => (
                <tr key={i} className="border-b border-line hover:bg-slate-50">
                  <td className="px-3 py-2 font-mono text-xs text-mut">{exp.name}</td>
                  <td className="px-3 py-2 text-ink text-sm">{exp.rule}</td>
                  <td className="px-3 py-2">
                    <Pill tone="red">{exp.action}</Pill>
                  </td>
                  <td className="px-3 py-2">
                    <Pill tone="green">{exp.status}</Pill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </Section>

      {/* Column completeness */}
      <Section title="Column Completeness (% non-null in Silver)">
        <div className="grid grid-cols-3 gap-3">
          {Object.entries(data.completeness || {}).map(([col, pct]: [string, any]) => (
            <Card key={col} className="flex items-center justify-between p-3">
              <span className="text-[13px] font-mono text-ink">{col}</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${Number(pct) >= 99 ? 'bg-emerald-500' : Number(pct) >= 90 ? 'bg-amber-400' : 'bg-red-400'}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className={`text-[11px] font-bold w-12 text-right ${Number(pct) >= 99 ? 'text-emerald-600' : Number(pct) >= 90 ? 'text-amber-600' : 'text-red-600'}`}>
                  {pct}%
                </span>
              </div>
            </Card>
          ))}
        </div>
      </Section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 4: Approve / Reject
// ---------------------------------------------------------------------------

function ApprovalTab({ datasetId }: { datasetId: string }) {
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    api.getApprovalHistory(datasetId).then(setHistory).catch(() => {});
  }, [datasetId, result]);

  const handleDecision = async (decision: string) => {
    setSubmitting(true);
    try {
      const res = await api.approveDataset(datasetId, decision, notes);
      setResult(res);
      setNotes('');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-5">
      {result && (
        <Card className={`border-l-4 ${result.decision === 'approved' ? 'bg-emerald-50 border-l-emerald-500' : 'bg-red-50 border-l-red-500'} p-4`}>
          <p className={`font-semibold ${result.decision === 'approved' ? 'text-emerald-800' : 'text-red-800'}`}>
            {result.message}
          </p>
          <p className="text-[13px] text-mut mt-1">Reviewer: {result.reviewer}</p>
        </Card>
      )}

      <Section title="Review Decision">
        <div className="mb-4">
          <label className="block text-[13px] font-semibold text-ink mb-2">Reviewer Notes</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder="Optional: add notes about this review decision…"
            className="w-full border border-line rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand focus:border-brand outline-none"
          />
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => handleDecision('approved')}
            disabled={submitting}
            className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            Approve & Merge
          </button>
          <button
            onClick={() => handleDecision('rejected')}
            disabled={submitting}
            className="flex items-center gap-2 px-6 py-2.5 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
            Reject
          </button>
        </div>
      </Section>

      {/* Approval history */}
      {history.length > 0 && (
        <Section title="Approval History">
          <Card className="overflow-x-auto p-0">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-line">
                  <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Date</th>
                  <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Decision</th>
                  <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Reviewer</th>
                  <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Notes</th>
                  <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Raw/Silver</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h: any, i: number) => (
                  <tr key={i} className="border-b border-line hover:bg-slate-50">
                    <td className="px-3 py-2 text-mut text-sm">{h.reviewed_at}</td>
                    <td className="px-3 py-2">
                      <Pill tone={h.decision === 'approved' ? 'green' : 'red'}>
                        {h.decision}
                      </Pill>
                    </td>
                    <td className="px-3 py-2 text-ink text-sm">{h.reviewer}</td>
                    <td className="px-3 py-2 text-mut text-sm">{h.reviewer_notes || '—'}</td>
                    <td className="px-3 py-2 text-ink text-sm">{h.raw_row_count} / {h.silver_row_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </Section>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 5: Upload / Download
// ---------------------------------------------------------------------------

function UploadDownloadTab({ datasetId, datasetName }: { datasetId: string; datasetName: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [validation, setValidation] = useState<any>(null);
  const [validating, setValidating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [mode, setMode] = useState<'replace' | 'append'>('replace');
  const [uploadHistory, setUploadHistory] = useState<any[]>([]);

  useEffect(() => {
    api.getUploadHistory(datasetId).then(setUploadHistory).catch(() => {});
  }, [datasetId, uploadResult]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setValidation(null);
    setUploadResult(null);
    setValidating(true);
    try {
      const result = await api.validateUpload(datasetId, f);
      setValidation(result);
    } catch (err: any) {
      setValidation({ valid: false, error: err.message });
    } finally {
      setValidating(false);
    }
  };

  const handleConfirm = async () => {
    if (!file) return;
    setUploading(true);
    try {
      const result = await api.confirmUpload(datasetId, file, mode);
      setUploadResult(result);
      setFile(null);
      setValidation(null);
    } catch (err: any) {
      setUploadResult({ error: err.message });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Download section */}
      <Section title="Download Current Data">
        <p className="text-[13px] text-mut mb-4">
          Export the current version as CSV for offline review. Downloads are logged in the audit trail.
        </p>
        <div className="flex gap-3">
          <a
            href={api.downloadDataset(datasetId, 'silver')}
            className="flex items-center gap-2 px-4 py-2 bg-brand text-white rounded-lg text-[13px] font-medium hover:bg-blue-700 transition-colors"
          >
            <Download className="w-4 h-4" /> Download Silver (Cleansed)
          </a>
          <a
            href={api.downloadDataset(datasetId, 'raw')}
            className="flex items-center gap-2 px-4 py-2 bg-slate-600 text-white rounded-lg text-[13px] font-medium hover:bg-slate-700 transition-colors"
          >
            <Download className="w-4 h-4" /> Download Raw (Bronze)
          </a>
        </div>
      </Section>

      {/* Upload section */}
      <Section title="Upload New Data">
        <p className="text-[13px] text-mut mb-4">
          Upload a CSV to replace or append data in the bronze layer. File must match the expected schema. After upload, the ingestion pipeline promotes to silver.
        </p>

        {/* Upload result banner */}
        {uploadResult && !uploadResult.error && (
          <Card className="mb-4 bg-emerald-50 border-emerald-200 p-4">
            <p className="font-semibold text-emerald-800">Upload successful</p>
            <p className="text-[13px] text-emerald-600 mt-1">
              {uploadResult.row_count} rows → {uploadResult.target_table} ({uploadResult.mode} mode)
            </p>
          </Card>
        )}
        {uploadResult?.error && (
          <Card className="mb-4 bg-red-50 border-red-200 p-4">
            <p className="font-semibold text-red-800">Upload failed: {uploadResult.error}</p>
          </Card>
        )}

        <div className="mb-4">
          <label className="block text-[13px] font-semibold text-ink mb-2">Upload Mode</label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="radio" checked={mode === 'replace'} onChange={() => setMode('replace')}
                className="text-brand" />
              <span className="text-[13px]"><strong>Replace</strong> — overwrite all existing rows</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="radio" checked={mode === 'append'} onChange={() => setMode('append')}
                className="text-brand" />
              <span className="text-[13px]"><strong>Append</strong> — add rows to existing data</span>
            </label>
          </div>
        </div>

        <div className="mb-4">
          <input
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            className="block w-full text-sm text-mut file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-brand hover:file:bg-blue-100"
          />
        </div>

        {validating && <Loading label="Validating schema…" />}

        {validation && !validation.error && (
          <div className="space-y-4">
            <Card className={`border-l-4 p-4 ${validation.valid ? 'bg-emerald-50 border-l-emerald-500' : 'bg-red-50 border-l-red-500'}`}>
              <div className="flex items-center gap-2 mb-2">
                {validation.valid
                  ? <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  : <XCircle className="w-5 h-5 text-red-600" />}
                <span className={`font-semibold ${validation.valid ? 'text-emerald-800' : 'text-red-800'}`}>
                  {validation.valid ? 'Schema validated' : 'Schema mismatch'}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-4 text-[13px] mt-2">
                <div><span className="text-mut">Filename:</span> {validation.filename}</div>
                <div><span className="text-mut">Rows:</span> {validation.row_count?.toLocaleString()}</div>
                <div><span className="text-mut">Hash:</span> <code className="text-xs">{validation.file_hash?.slice(0, 16)}…</code></div>
              </div>
              {validation.missing_columns?.length > 0 && (
                <div className="mt-2 text-sm text-red-600">
                  Missing columns: <strong>{validation.missing_columns.join(', ')}</strong>
                </div>
              )}
              {validation.extra_columns?.length > 0 && (
                <div className="mt-2 text-sm text-amber-600">
                  Extra columns (will be ignored): {validation.extra_columns.join(', ')}
                </div>
              )}
            </Card>

            {validation.preview?.length > 0 && (
              <Section title={`Preview (first ${validation.preview.length} of ${validation.row_count} rows)`}>
                <SimpleTable rows={validation.preview} />
              </Section>
            )}

            {validation.valid && (
              <button
                onClick={handleConfirm}
                disabled={uploading}
                className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
              >
                {uploading
                  ? <><Loader2 className="w-4 h-4 animate-spin" /> Uploading…</>
                  : <><Upload className="w-4 h-4" /> Confirm Upload ({mode})</>
                }
              </button>
            )}
          </div>
        )}
        {validation?.error && (
          <Card className="bg-red-50 border-red-200 p-4 text-red-700 text-sm">
            {validation.error}
          </Card>
        )}
      </Section>

      {/* Upload history */}
      {uploadHistory.length > 0 && (
        <Section title="Upload History">
          <Card className="overflow-x-auto p-0">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-line">
                  <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Date</th>
                  <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">User</th>
                  <th className="px-3 py-2 text-left font-medium text-mut text-xs uppercase">Details</th>
                </tr>
              </thead>
              <tbody>
                {uploadHistory.map((h: any, i: number) => {
                  let details: any = {};
                  try { details = typeof h.details === 'string' ? JSON.parse(h.details) : h.details; } catch {}
                  return (
                    <tr key={i} className="border-b border-line hover:bg-slate-50">
                      <td className="px-3 py-2 text-mut whitespace-nowrap text-[13px]">{h.timestamp}</td>
                      <td className="px-3 py-2 text-ink text-[13px]">{h.user_id}</td>
                      <td className="px-3 py-2 text-mut text-[12px]">
                        {details.original_filename} — {details.row_count} rows ({details.upload_mode}) — <code className="text-[11px]">{details.file_hash?.slice(0, 12)}…</code>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        </Section>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared components (local overrides for backward compat)
// ---------------------------------------------------------------------------

function SimpleTable({ rows }: { rows: any[] }) {
  if (!rows.length) return <p className="text-mut text-[13px]">No data</p>;
  const cols = Object.keys(rows[0]).filter((c) => !c.startsWith('_'));
  return (
    <Card className="overflow-x-auto p-0">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="bg-slate-50 border-b border-line">
            {cols.map((c) => (
              <th key={c} className="px-3 py-2 text-left font-medium text-mut text-xs uppercase whitespace-nowrap">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 20).map((row, i) => (
            <tr key={i} className="border-b border-line hover:bg-slate-50">
              {cols.map((c) => (
                <td key={c} className="px-3 py-2 text-ink text-[13px] whitespace-nowrap">{formatVal(row[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function formatVal(v: any): string {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'number') return v.toLocaleString();
  return String(v);
}

function formatGwp(v: any): string {
  const num = Number(v);
  if (isNaN(num)) return String(v);
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(0)}K`;
  return num.toLocaleString();
}
