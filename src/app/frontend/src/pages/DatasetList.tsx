import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Database, CheckCircle2, XCircle, Clock, Building2, Globe } from 'lucide-react';
import { api } from '../lib/api';
import {
  Page, PageHeader, OnThisPage, Card, Section, Pill, AgentLead, UnderTheHood, Skeleton, SectionHead,
} from '../components/ui';

export default function DatasetList() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    // 1. Fast meta call — returns instantly so the cards draw immediately.
    // 2. Stats call in parallel — each card gets its row counts + approval
    //    state when it resolves a couple of seconds later.
    api.getDatasetsMeta().then(setDatasets).catch(() => {});
    api.getDatasets()
      .then(setDatasets)                      // overwrite with real stats
      .finally(() => setStatsLoading(false));
  }, []);

  const internalCount = datasets.filter(d => (d.category || 'external_vendor') === 'internal').length;
  const externalCount = datasets.filter(d => (d.category || 'external_vendor') === 'external_vendor').length;
  const refCount = datasets.filter(d => (d.category || 'external_vendor') === 'reference_data').length;
  const pendingCount = datasets.filter(d => (d.category || 'external_vendor') === 'external_vendor' && d.approval?.decision === 'pending').length;

  return (
    <Page>
      <PageHeader
        eyebrow="Bricksurance SE · Data Ingestion"
        title="Data Ingestion"
        subtitle="Every dataset that feeds pricing — internal book, vendor feeds awaiting review, and public reference data. Actuaries review pricing impact before approval."
        icon={Database}
      />

      {/* Lead with the agent — Ingestion Impact explains the current state then answers follow-ups */}
      <AgentLead
        persona="explain"
        title="Ingestion impact"
        subtitle="Ask why premiums move when data changes. Your data scientist reads the pending approvals and recent uploads, then answers your questions."
        seed="In 3 sentences: what data sources feed pricing, is anything pending review, and what's the pricing impact of the latest change?"
        examples={[
          'Why did premiums change after the last data update?',
          'Which segments are most affected?',
          'Is the new vendor data safe to approve?',
        ]}
      />

      <OnThisPage>
        Every data source is grouped by category: internal policies and claims need no approval; vendor feeds must be reviewed by an actuary before merging; reference data is one-shot public feeds. Inspect datasets to see the exact data changes, impact analysis, and approval history.
      </OnThisPage>

      {/* Skeleton shown only when even the meta hasn't arrived yet. */}
      {datasets.length === 0 && (
        <div className="space-y-3">
          {[0, 1, 2, 3, 4].map(i => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      )}

      {/* Group by category so the internal book sits above the vendor feeds */}
      {['internal', 'external_vendor', 'reference_data'].map((cat) => {
        const rows = datasets.filter((d) => (d.category || 'external_vendor') === cat);
        if (rows.length === 0) return null;
        const heading =
          cat === 'internal'         ? 'Internal book'
        : cat === 'external_vendor'  ? 'External vendor feeds (review required)'
        :                              'Public reference data';
        const headingHelp =
          cat === 'internal'         ? 'Policy and claim records from our own systems. Shown for completeness — no actuary approval needed.'
        : cat === 'external_vendor'  ? 'Incoming vendor data needs an actuary review before it can feed pricing.'
        :                              'Freely-available reference data (e.g. ONS). One-shot builds.';

        return (
          <div key={cat}>
            <SectionHead>{heading}</SectionHead>
            <div className="text-xs text-mut mb-3">{headingHelp}</div>
            <div className="space-y-2">
              {rows.map((ds) => (
                <DatasetCard key={ds.id} ds={ds} />
              ))}
            </div>
          </div>
        );
      })}

      <UnderTheHood
        title="Data Ingestion"
        lines={[
          { component: 'Lakeflow / DLT', detail: 'Bronze → silver with expectations (nulls, ranges, cardinality)' },
          { component: 'Unity Catalog', detail: 'Lineage + HITL approval gate before silver is tagged for pricing' },
          { component: 'Shadow pricing', detail: 'Re-rate affected policies on new vendor data before approval' },
          { component: 'Audit trail', detail: 'Every upload, approval, rejection, and download is immutably logged' },
        ]}
      />
    </Page>
  );
}

// Render an ingestion timestamp in relative form ("2 hours ago") with the ISO
// date as tooltip. Takes the shape Databricks SQL returns — either ISO string
// or epoch-like.
function formatIngested(iso?: string | null): string {
  if (!iso) return '—';
  const t = new Date(iso).getTime();
  if (isNaN(t)) return '—';
  const now = Date.now();
  const diff = Math.max(0, now - t);
  const mins = Math.floor(diff / 60_000);
  if (mins < 1)            return 'Just now';
  if (mins < 60)           return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)            return `${hrs} hour${hrs === 1 ? '' : 's'} ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30)           return `${days} day${days === 1 ? '' : 's'} ago`;
  return new Date(iso).toLocaleDateString();
}

function DatasetCard({ ds }: { ds: any }) {
  const category = ds.category || 'external_vendor';
  const isInternal = category === 'internal';
  const isReference = category === 'reference_data';

  // Icon + tile colour per category
  const tile =
    isInternal  ? { Icon: Building2, ring: 'bg-slate-100 text-slate-600' }
  : isReference ? { Icon: Globe,     ring: 'bg-indigo-50 text-indigo-600' }
  :               { Icon: Database,  ring: 'bg-blue-50 text-blue-600' };

  return (
    <Link
      to={`/dataset/${ds.id}`}
      className="block"
    >
      <Card drill>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 min-w-0">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${tile.ring}`}>
              <tile.Icon className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h3 className="font-semibold text-ink">
                {ds.display_name}
              </h3>
              <p className="text-[13px] text-mut line-clamp-2">{ds.description}</p>
            </div>
          </div>
          <div className="flex items-center gap-6 shrink-0">
            <div className="text-right min-w-[8rem]">
              <div className="text-[11px] font-bold uppercase text-mut">Source</div>
              <div className="text-[13px] font-medium truncate max-w-[12rem]">{ds.source}</div>
            </div>
            {isInternal || isReference ? (
              <div className="text-right min-w-[7rem]">
                <div className="text-[11px] font-bold uppercase text-mut">Rows</div>
                <div className="text-[13px] font-medium">
                  {ds.silver_row_count == null
                    ? <span className="inline-block w-16 h-3 rounded bg-slate-200 animate-pulse" />
                    : Number(ds.silver_row_count).toLocaleString()}
                </div>
              </div>
            ) : (
              <>
                <div className="text-right min-w-[8rem]">
                  <div className="text-[11px] font-bold uppercase text-mut">Last Ingested</div>
                  <div className="text-[13px] font-medium">
                    {ds.last_ingested === undefined
                      ? <span className="inline-block w-24 h-3 rounded bg-slate-200 animate-pulse" />
                      : formatIngested(ds.last_ingested)}
                  </div>
                </div>
                <div className="text-right min-w-[9rem]">
                  <div className="text-[11px] font-bold uppercase text-mut">Pending / Approved</div>
                  <div className="text-[13px] font-medium">
                    {ds.raw_row_count == null
                      ? <span className="inline-block w-24 h-3 rounded bg-slate-200 animate-pulse" />
                      : <>{Number(ds.raw_row_count).toLocaleString()} / {Number(ds.silver_row_count).toLocaleString()}</>}
                  </div>
                </div>
                <div className="text-right min-w-[5rem]">
                  <div className="text-[11px] font-bold uppercase text-mut">Blocked</div>
                  <div className={`text-[13px] font-medium ${ds.rows_dropped_by_dq && ds.rows_dropped_by_dq > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                    {ds.rows_dropped_by_dq == null
                      ? <span className="inline-block w-8 h-3 rounded bg-slate-200 animate-pulse" />
                      : ds.rows_dropped_by_dq}
                  </div>
                </div>
              </>
            )}
            <StatusBadge dataset={ds} />
          </div>
        </div>
      </Card>
    </Link>
  );
}

function StatusBadge({ dataset }: { dataset: any }) {
  const cat = dataset.category || 'external_vendor';
  // Internal and reference datasets skip approval entirely.
  if (cat === 'internal') {
    return <Pill tone="slate"><Building2 className="w-3 h-3" /> Internal</Pill>;
  }
  if (cat === 'reference_data') {
    return <Pill tone="blue"><Globe className="w-3 h-3" /> Reference</Pill>;
  }
  // External vendor feed — real approval workflow
  const status = dataset.approval?.decision || 'pending';
  if (status === 'approved') {
    return <Pill tone="green"><CheckCircle2 className="w-3 h-3" /> Approved</Pill>;
  }
  if (status === 'rejected') {
    return <Pill tone="red"><XCircle className="w-3 h-3" /> Rejected</Pill>;
  }
  return <Pill tone="amber"><Clock className="w-3 h-3" /> Pending</Pill>;
}
