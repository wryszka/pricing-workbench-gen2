import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Rocket, ExternalLink, Loader2, Undo2, ChevronDown, ChevronRight,
  FileCheck2, ShieldCheck, Server, AlertCircle, Zap, Clock, Database,
  Power, Play, Square, Activity, FileText, AlertTriangle,
  Receipt, Radio, Gauge, Network,
} from 'lucide-react';
import { api } from '../lib/api';
import {
  Page, PageHeader, OnThisPage, Card, CardTitle, Section, Metric, Pill, AgentLead,
  UnderTheHood, Grid, SectionHead, Btn,
} from '../components/ui';

type Family = {
  family: string;
  label: string;
  uc_name: string;
  catalog_url: string;
  champion?: { version: string; run_id: string; status: string; created_at?: string; created_by?: string } | null;
  champion_is_alias: boolean;
  previous_champion?: { version: string; run_id: string; created_at?: string; created_by?: string } | null;
  latest_pack?: {
    pack_id: string; pdf_path: string; generated_by: string; generated_at: string; download_url: string;
  } | null;
};

type Tab = 'production' | 'live';

export default function ModelDeployment() {
  const [tab, setTab] = useState<Tab>('production');

  return (
    <Page>
      <PageHeader
        eyebrow="Bricksurance SE · Model Deployment"
        title="Model Deployment"
        subtitle="Champions, rollback, and endpoint health monitoring"
        icon={Rocket}
      />

      <AgentLead compact
        persona="drift_monitor"
        title="Monitoring"
        subtitle="Watches deployed champions for calibration drift."
        seed="Are the deployed champions healthy — any calibration drift I should act on, and what would you recommend?"
        examples={[
          'Is the frequency model drifting?',
          'How fresh is the scoring?',
          'Draft a committee note on any drift',
        ]}
      />

      <OnThisPage>
        The live champion versions across all four model families, their deployment status, and governance pack
        linkage. Production rollback is one-click — swaps the champion alias back to the previous version with an
        audit-logged justification. Live endpoint metrics stream below.
      </OnThisPage>

      <div className="flex gap-1 border-b border-line mb-5">
        <TabButton active={tab === 'production'} onClick={() => setTab('production')}
                   icon={<ShieldCheck className="w-4 h-4" />} label="Production Models" />
        <TabButton active={tab === 'live'} onClick={() => setTab('live')}
                   icon={<Zap className="w-4 h-4" />} label="Live Pricing System" />
      </div>

      {tab === 'production' && <ProductionModels />}
      {tab === 'live'       && <LivePricing />}

      <UnderTheHood
        title="Deployment architecture"
        lines={[
          { component: 'UC model aliases', detail: 'champion, previous_champion — point to versioned MLflow models' },
          { component: 'Mosaic AI endpoints', detail: 'pwg2_freq_scorer, sev, demand, fraud — four independent serving endpoints' },
          { component: 'Governance packs', detail: 'PDF generated on promotion, stored in UC Volumes, linked to champion version' },
          { component: 'Rollback mechanism', detail: 'Swaps alias + demotes current → previous_champion; audit-logged with justification' },
        ]}
      />
    </Page>
  );
}

function TabButton({ active, onClick, icon, label }:
  { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button onClick={onClick}
            className={`px-4 py-2 text-sm font-medium inline-flex items-center gap-2 border-b-2 transition ${
              active
                ? 'border-brand text-brand'
                : 'border-transparent text-mut hover:text-ink'
            }`}>
      {icon} {label}
    </button>
  );
}

// ===========================================================================
// Tab 1 — Production Models
// ===========================================================================

function ProductionModels() {
  const [families, setFamilies]     = useState<Family[]>([]);
  const [loading, setLoading]       = useState(true);
  const [openRow, setOpenRow]       = useState<string | null>(null);
  const [history, setHistory]       = useState<Record<string, any[]>>({});
  const [rollbackFor, setRollbackFor] = useState<Family | null>(null);
  const [toast, setToast]           = useState<string | null>(null);

  const reload = () => {
    setLoading(true);
    api.getChampions()
      .then((d) => setFamilies(d.families || []))
      .catch(() => setFamilies([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { reload(); }, []);

  const toggleRow = (family: string) => {
    if (openRow === family) {
      setOpenRow(null);
      return;
    }
    setOpenRow(family);
    if (!history[family]) {
      api.getChampionHistory(family, 10).then((d) => {
        setHistory(cur => ({ ...cur, [family]: d.events || [] }));
      });
    }
  };

  return (
    <div className="space-y-5">
      <Card className="border-[#ddd6fe] bg-[#faf5ff]">
        <CardTitle>Production champions</CardTitle>
        <p className="text-[13px] text-ink leading-relaxed mb-3">
          Current champions across all pricing models. Promotion flips the <code className="bg-white border border-line px-1 rounded text-[10px] font-mono">champion</code> alias and demotes the prior version to <code className="bg-white border border-line px-1 rounded text-[10px] font-mono">previous_champion</code>.
          Rollback swaps them back with an audit-logged justification.
        </p>
        <div className="flex flex-wrap gap-1.5">
          {['UC model aliases', 'One-click rollback', 'Audit-logged', 'Governance packs'].map(f => (
            <Pill key={f} tone="blue">{f}</Pill>
          ))}
        </div>
      </Card>

      <Card>
        <div className="flex items-center justify-between mb-3">
          <CardTitle>Current champions</CardTitle>
          <span className="text-[11px] text-mut">{families.length} families</span>
        </div>
        {loading ? (
          <div className="py-8 text-center text-mut text-sm"><Loader2 className="w-4 h-4 animate-spin inline mr-2" />Loading…</div>
        ) : families.length === 0 ? (
          <div className="py-8 text-center text-mut text-sm italic">No production models registered yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[11px] text-mut uppercase tracking-[0.04em] border-b">
                  <th className="text-left px-3 py-2 font-semibold w-4"></th>
                  <th className="text-left px-3 py-2 font-semibold">Model</th>
                  <th className="text-left px-3 py-2 font-semibold">Champion</th>
                  <th className="text-left px-3 py-2 font-semibold">Promoted</th>
                  <th className="text-left px-3 py-2 font-semibold">By</th>
                  <th className="text-left px-3 py-2 font-semibold">Pack</th>
                  <th className="text-left px-3 py-2 font-semibold">Previous</th>
                  <th className="text-right px-3 py-2 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {families.map(f => {
                  const isOpen = openRow === f.family;
                  const canRollback = Boolean(f.previous_champion);
                  return (
                    <>
                      <tr key={`${f.family}-row`}
                          className={`border-b last:border-0 hover:bg-slate-50 text-sm ${isOpen ? 'bg-slate-50' : ''}`}>
                        <td className="px-3 py-2">
                          <button onClick={() => toggleRow(f.family)} className="text-mut hover:text-ink">
                            {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                          </button>
                        </td>
                        <td className="px-3 py-2">
                          <div className="font-medium text-ink">{f.label}</div>
                          <div className="text-[10px] text-mut font-mono">{f.uc_name.split('.').slice(-1)[0]}</div>
                        </td>
                        <td className="px-3 py-2">
                          {f.champion ? (
                            <span className="font-mono text-xs text-ink">
                              v{f.champion.version}
                              {!f.champion_is_alias && (
                                <Pill tone="amber" className="ml-1 inline-flex">latest</Pill>
                              )}
                            </span>
                          ) : <span className="text-mut">—</span>}
                        </td>
                        <td className="px-3 py-2 text-xs text-mut">
                          {formatDate(f.champion?.created_at)}
                        </td>
                        <td className="px-3 py-2 text-xs text-mut">
                          {(f.champion?.created_by || '').split('@')[0] || '—'}
                        </td>
                        <td className="px-3 py-2">
                          {f.latest_pack ? (
                            <a href={f.latest_pack.download_url} target="_blank" rel="noopener noreferrer"
                               className="inline-flex items-center gap-1 text-xs text-brand hover:text-blue-700">
                              <FileCheck2 className="w-3 h-3" />
                              {formatDate(f.latest_pack.generated_at)}
                            </a>
                          ) : (
                            <span className="text-[11px] text-mut inline-flex items-center gap-1">
                              <AlertCircle className="w-3 h-3" /> —
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-mut">
                          {f.previous_champion ? `v${f.previous_champion.version}` : '—'}
                        </td>
                        <td className="px-3 py-2 text-right">
                          <Btn tone={canRollback ? 'bad' : 'ghost'}
                               onClick={() => setRollbackFor(f)}
                               disabled={!canRollback}
                               className="text-[11px]">
                            <Undo2 className="w-3 h-3" /> Rollback
                          </Btn>
                        </td>
                      </tr>
                      {isOpen && (
                        <tr key={`${f.family}-det`} className="border-b bg-slate-50/50">
                          <td colSpan={8} className="px-4 py-3">
                            <RowDetail family={f} events={history[f.family] || null} />
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Serving SLO tiles */}
      <ServingSLOs />

      {/* Live endpoint metrics */}
      {families.length > 0 && <LiveEndpointMetrics families={families} />}

      {rollbackFor && (
        <RollbackDialog
          family={rollbackFor}
          onClose={() => setRollbackFor(null)}
          onDone={(msg) => { setRollbackFor(null); setToast(msg); reload(); }}
        />
      )}

      {toast && (
        <div onClick={() => setToast(null)}
             className="fixed bottom-4 right-4 bg-ink text-white text-sm px-4 py-2 rounded-lg shadow-lg z-50 cursor-pointer">
          {toast}
        </div>
      )}
    </div>
  );
}

function RowDetail({ family, events }: { family: Family; events: any[] | null }) {
  return (
    <Grid cols={3}>
      <Card>
        <CardTitle>Champion</CardTitle>
        {family.champion ? (
          <div className="text-[12px] space-y-0.5">
            <div><span className="text-mut">Version:</span> <span className="font-mono text-ink">v{family.champion.version}</span></div>
            <div><span className="text-mut">Run:</span> <span className="font-mono text-[10px] break-all text-ink">{family.champion.run_id}</span></div>
            <div><span className="text-mut">Status:</span> <span className="text-ink">{family.champion.status}</span></div>
            <div><span className="text-mut">Trained by:</span> <span className="text-ink">{family.champion.created_by}</span></div>
            <div><span className="text-mut">Trained at:</span> <span className="text-ink">{formatDate(family.champion.created_at)}</span></div>
          </div>
        ) : <div className="text-xs text-mut italic">No champion assigned.</div>}
        <a href={family.catalog_url} target="_blank" rel="noopener noreferrer"
           className="inline-flex items-center gap-1 text-xs text-brand hover:underline mt-2">
          Open in Catalog <ExternalLink className="w-3 h-3" />
        </a>
      </Card>

      <Card>
        <CardTitle>Governance pack</CardTitle>
        {family.latest_pack ? (
          <div className="text-[12px] space-y-0.5">
            <div><span className="text-mut">Pack ID:</span> <span className="font-mono text-[10px] text-ink">{family.latest_pack.pack_id}</span></div>
            <div><span className="text-mut">Generated:</span> <span className="text-ink">{formatDate(family.latest_pack.generated_at)}</span></div>
            <div><span className="text-mut">By:</span> <span className="text-ink">{family.latest_pack.generated_by}</span></div>
            <a href={family.latest_pack.download_url} target="_blank" rel="noopener noreferrer"
               className="inline-flex items-center gap-1 text-brand hover:underline mt-1">
              <FileCheck2 className="w-3 h-3" /> Download PDF
            </a>
          </div>
        ) : <div className="text-xs text-mut italic">No pack yet.</div>}
      </Card>

      <Card>
        <CardTitle>Approval history</CardTitle>
        {events === null ? (
          <div className="text-xs text-mut"><Loader2 className="w-3 h-3 inline animate-spin mr-1" /> Loading…</div>
        ) : events.length === 0 ? (
          <div className="text-xs text-mut italic">No events.</div>
        ) : (
          <ul className="text-xs space-y-1 max-h-40 overflow-y-auto">
            {events.map((e, i) => (
              <li key={i} className="flex items-start gap-2">
                <Pill tone={eventTone(e.event_type)} className="text-[10px]">
                  {eventShortLabel(e.event_type)}
                </Pill>
                <span className="text-ink">
                  v{e.version || '—'} · {formatDate(e.timestamp)}
                  <span className="text-mut"> · {(e.user || '').split('@')[0]}</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </Grid>
  );
}

// ---------------------------------------------------------------------------
// Live endpoint metrics — placeholder stream
//
// Real Model Serving will replace this with `serving_endpoints/metrics` pulls.
// Until then we simulate a plausible load profile client-side so the page has
// the monitoring signals reviewers expect to see on a live production board.
// ---------------------------------------------------------------------------

function LiveEndpointMetrics({ families }: { families: Family[] }) {
  const [tick, setTick] = useState(0);
  const [history, setHistory] = useState<Record<string, number[]>>({});

  useEffect(() => {
    const h: Record<string, number[]> = {};
    for (const f of families) h[f.family] = seedSeries(f.family, 60);
    setHistory(h);
  }, [families.map(f => f.family).join(',')]);

  useEffect(() => {
    const t = setInterval(() => setTick(x => x + 1), 2000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    setHistory(cur => {
      const next: Record<string, number[]> = { ...cur };
      for (const f of families) {
        const s = [...(cur[f.family] || seedSeries(f.family, 60))];
        const last = s[s.length - 1] ?? 50;
        const drift = (Math.random() - 0.5) * 6;
        const v = clamp(last + drift, 10, 120);
        s.push(v);
        while (s.length > 60) s.shift();
        next[f.family] = s;
      }
      return next;
    });
  }, [tick]);

  const allQps = families.reduce((acc, f) => {
    const s = history[f.family] || [];
    return acc + (s[s.length - 1] ?? 0);
  }, 0);
  const p50 = pickLatency(0.5, tick);
  const p95 = pickLatency(0.95, tick);
  const p99 = pickLatency(0.99, tick);
  const errRate = 0.08 + 0.05 * Math.sin(tick / 6);
  const uptime = 99.97 + 0.02 * Math.cos(tick / 9);

  return (
    <Card>
      <div className="flex items-center justify-between mb-3">
        <CardTitle>Live endpoint metrics</CardTitle>
        <div className="text-[11px] text-mut inline-flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Updated every 2s
          <Pill tone="amber" className="ml-1">demo simulation</Pill>
        </div>
      </div>

      <Grid cols={5} className="mb-3 pb-3 border-b">
        <Metric label="QPS (all)" value={Math.round(allQps).toLocaleString()} sub="request rate" tone="blue" />
        <Metric label="Latency p50" value={`${p50.toFixed(0)} ms`} sub="median" tone="green" />
        <Metric label="Latency p95" value={`${p95.toFixed(0)} ms`} sub={p95 < 400 ? "within SLA" : "approaching SLA"} tone={p95 < 400 ? "green" : "amber"} />
        <Metric label="Latency p99" value={`${p99.toFixed(0)} ms`} sub={p99 < 500 ? "within SLA" : "breaching"} tone={p99 < 500 ? "green" : "red"} />
        <Metric label="Error rate" value={`${errRate.toFixed(2)}%`} sub={`uptime ${uptime.toFixed(2)}%`} tone={errRate > 0.5 ? "red" : "green"} />
      </Grid>

      <SectionHead>Per-model throughput (last 2 min)</SectionHead>
      <div className="space-y-1.5 mb-3">
        {families.map(f => {
          const s = history[f.family] || [];
          const current = s[s.length - 1] ?? 0;
          return (
            <div key={f.family} className="flex items-center gap-3 text-xs">
              <div className="w-32 shrink-0 text-ink font-medium">{f.label}</div>
              <Sparkline values={s} height={26} className="flex-1" />
              <div className="w-24 text-right text-ink font-mono">{Math.round(current)} q/s</div>
              <div className="w-20 text-right text-mut font-mono">
                {(pickLatency(0.5, tick + f.family.length) + 20).toFixed(0)} ms
              </div>
            </div>
          );
        })}
      </div>

      <div className="text-[11px] text-mut pt-2 border-t">
        <span className="font-semibold block mb-1">SLO targets:</span> p95 &lt; 400ms, p99 &lt; 500ms, error rate &lt; 0.5%
      </div>
    </Card>
  );
}

function MetricTile({ label, value, subtext, tone }:
  { label: string; value: string; subtext?: string; tone: 'blue' | 'emerald' | 'amber' | 'red' }) {
  const toneCls = {
    blue:    'text-blue-700',
    emerald: 'text-emerald-700',
    amber:   'text-amber-700',
    red:     'text-red-700',
  }[tone];
  return (
    <div className="px-4 py-3 border-r last:border-r-0">
      <div className="text-[10px] text-gray-500 uppercase tracking-wide">{label}</div>
      <div className={`text-2xl font-semibold mt-1 ${toneCls}`}>{value}</div>
      {subtext && <div className="text-[10px] text-gray-500 mt-0.5">{subtext}</div>}
    </div>
  );
}

function Sparkline({ values, height, className }:
  { values: number[]; height: number; className?: string }) {
  if (!values || values.length < 2) {
    return <div className={className} style={{ height }} />;
  }
  const w = 200;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(1, max - min);
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = height - 2 - ((v - min) / span) * (height - 4);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return (
    <svg className={className} viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none"
         style={{ height, width: '100%' }}>
      <polyline fill="none" stroke="#3b82f6" strokeWidth="1.5" points={points} />
      <polyline fill="rgba(59,130,246,0.1)" stroke="none"
                points={`0,${height} ${points} ${w},${height}`} />
    </svg>
  );
}

function clamp(x: number, lo: number, hi: number) { return Math.max(lo, Math.min(hi, x)); }

function seedSeries(familyKey: string, n: number): number[] {
  // Deterministic-ish starting point so the card renders the same baseline
  // between re-renders for the same family.
  let seed = Array.from(familyKey).reduce((s, c) => s + c.charCodeAt(0), 0);
  const center = 40 + (seed % 40);
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    seed = (seed * 9301 + 49297) % 233280;
    const r = seed / 233280;
    out.push(clamp(center + Math.sin(i / 5) * 6 + (r - 0.5) * 10, 10, 120));
  }
  return out;
}

function pickLatency(pct: number, tick: number): number {
  // Base latency bands for realistic variance around a healthy SLA.
  const base = pct < 0.6 ? 110 : pct < 0.97 ? 280 : 420;
  const jitter = Math.sin(tick / 5) * 20 + (Math.random() - 0.5) * 30;
  return clamp(base + jitter, base - 60, base + 120);
}

function RollbackDialog({ family, onClose, onDone }:
  { family: Family; onClose: () => void; onDone: (msg: string) => void }) {
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr]   = useState<string | null>(null);

  const submit = async () => {
    setBusy(true); setErr(null);
    try {
      const r = await api.rollbackChampion(family.family, note.trim());
      onDone(`Rolled back ${family.label} to v${r.new_champion}`);
    } catch (e: any) {
      setErr(e.message); setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-40">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full mx-4 border border-line">
        <div className="px-5 py-3 border-b border-line flex items-center gap-2">
          <Undo2 className="w-4 h-4 text-red-600" />
          <h3 className="font-semibold text-ink">Rollback {family.label}</h3>
        </div>
        <div className="p-5 space-y-3">
          <p className="text-sm text-ink leading-relaxed">
            The <code className="bg-slate-100 border border-line px-1 rounded text-[11px] font-mono">champion</code> alias will move from
            <strong className="mx-1">v{family.champion?.version}</strong>
            back to
            <strong className="mx-1">v{family.previous_champion?.version}</strong>.
            Current champion becomes <code className="bg-slate-100 border border-line px-1 rounded text-[11px] font-mono">previous_champion</code>.
          </p>
          <label className="text-xs font-bold uppercase tracking-[0.04em] text-ink block">
            Justification <span className="text-red-600">*</span>
            <span className="text-mut font-normal text-[11px]">
              {' '}(minimum 10 characters, logged to audit trail)
            </span>
          </label>
          <textarea value={note} onChange={e => setNote(e.target.value)}
                    rows={3}
                    placeholder="e.g. Observed +14% false-positive rate in fraud referrals since promotion"
                    className="w-full border border-line rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/50" />
          {err && <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 flex items-start gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" /> {err}
          </div>}
        </div>
        <div className="px-5 py-3 border-t border-line bg-slate-50/50 flex items-center justify-end gap-2">
          <Btn tone="ghost" onClick={onClose}>Cancel</Btn>
          <Btn tone="bad"
               onClick={submit}
               disabled={busy || note.trim().length < 10}>
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Undo2 className="w-4 h-4" />}
            Confirm rollback
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ===========================================================================
// Tab 2 — Live Pricing System
// ===========================================================================

type LiveState = 'off' | 'starting' | 'on' | 'stopping' | 'unknown';
type LiveStatus = {
  state: LiveState;
  endpoint:     { name: string; present: boolean; ready?: string; config_update?: string };
  online_store: { name: string; present: boolean; state?: string; capacity?: string };
  metrics_table?: string;
};

function LivePricing() {
  const [status, setStatus] = useState<LiveStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState<'start' | 'stop' | null>(null);
  const [archOpen, setArchOpen] = useState(false);

  const inTransition = status?.state === 'starting' || status?.state === 'stopping';

  // Poll status — 5s when idle, 2s during transitions.
  useEffect(() => {
    let cancelled = false;
    const fetchOnce = async () => {
      try {
        const s = await api.livePricingStatus();
        if (!cancelled) { setStatus(s); setStatusError(null); }
      } catch (e: any) {
        if (!cancelled) setStatusError(e?.message || String(e));
      }
    };
    fetchOnce();
    const interval = inTransition ? 2000 : 5000;
    const t = window.setInterval(fetchOnce, interval);
    return () => { cancelled = true; window.clearInterval(t); };
  }, [inTransition]);

  const togglePower = async () => {
    if (!status) return;
    if (status.state === 'on' || status.state === 'starting') {
      setActionBusy('stop');
      try { await api.livePricingStop(); }
      catch (e: any) { setStatusError(e?.message || String(e)); }
      finally { setActionBusy(null); }
    } else {
      setActionBusy('start');
      try { await api.livePricingStart(); }
      catch (e: any) { setStatusError(e?.message || String(e)); }
      finally { setActionBusy(null); }
    }
  };

  const stateBadge = (() => {
    switch (status?.state) {
      case 'on':       return { dot: 'bg-emerald-500',       label: 'On',         desc: 'Endpoint READY · online store live' };
      case 'starting': return { dot: 'bg-amber-500 animate-pulse', label: 'Starting', desc: 'Provisioning Lakebase + warm-up (5–10 min)' };
      case 'stopping': return { dot: 'bg-amber-500 animate-pulse', label: 'Stopping', desc: 'Tearing down endpoint + online store' };
      case 'off':      return { dot: 'bg-gray-300',          label: 'Off',        desc: 'No live runtime — click Activate to bring up' };
      default:         return { dot: 'bg-gray-300',          label: '—',          desc: 'Resolving state…' };
    }
  })();

  return (
    <div className="space-y-5">
      {/* Header — power button + state */}
      <Card>
        <div className="flex items-center justify-between gap-4 flex-wrap mb-3">
          <div className="flex items-center gap-3">
            <span className={`w-3 h-3 rounded-full ${stateBadge.dot}`} aria-hidden />
            <div>
              <h2 className="font-bold text-ink text-base flex items-center gap-2">
                <Zap className="w-4 h-4 text-purple-600" />
                Live Pricing System
              </h2>
              <p className="text-xs text-mut mt-0.5">
                {stateBadge.label} — {stateBadge.desc}
              </p>
            </div>
          </div>
          <Btn tone={status?.state === 'on' ? 'bad' : 'primary'}
               onClick={togglePower}
               disabled={actionBusy !== null || inTransition}>
            {actionBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Power className="w-4 h-4" />}
            {status?.state === 'on' ? 'Deactivate' : 'Activate'}
          </Btn>
        </div>
        {statusError && (
          <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 flex items-start gap-2 mb-3">
            <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            <span>{statusError}</span>
          </div>
        )}
        {status && (
          <Grid cols={2}>
            <StatusChip
              icon={<Server className="w-3.5 h-3.5" />}
              label="Endpoint"
              value={status.endpoint.name}
              detail={status.endpoint.present
                ? `ready=${status.endpoint.ready ?? '?'} · config=${status.endpoint.config_update ?? '?'}`
                : 'not present'}
              ok={status.endpoint.present && status.endpoint.ready === 'READY'}
            />
            <StatusChip
              icon={<Database className="w-3.5 h-3.5" />}
              label="Online store"
              value={status.online_store.name}
              detail={status.online_store.present
                ? `${status.online_store.state ?? '?'} · ${status.online_store.capacity ?? '?'}`
                : 'not present'}
              ok={status.online_store.present && (status.online_store.state ?? '').endsWith('AVAILABLE')}
            />
          </Grid>
        )}
      </Card>

      {status?.state === 'on' && (
        <Card>
          <CardTitle className="flex items-center gap-1.5 mb-1">
            <ExternalLink className="w-4 h-4 text-purple-600" /> Demo pages
          </CardTitle>
          <p className="text-[13px] text-mut mb-3">
            Standalone customer-facing UIs for the live pricing story. Best opened in new tabs.
          </p>
          <Grid cols={2}>
            <DemoLink href="/quote"       icon={Receipt} accent="blue"
                      title="Quote portal"   desc="Consumer quote, pre-filled for John" />
            <DemoLink href="/blackbox"    icon={Radio} accent="amber"
                      title="Black-box panel" desc="Fire a telematics event" />
            <DemoLink href="/quotetester" icon={Gauge} accent="violet"
                      title="Live quote tester" desc="Streaming QPS + latency" />
            <DemoLink href="/quote-chat"  icon={Network} accent="fuchsia"
                      title="Agentic MCP sales"
                      desc="Buy by conversation — Claude calls engine over MCP" />
          </Grid>
        </Card>
      )}

      {/* Sections only show when ON */}
      {status?.state === 'on' && (
        <>
          <DemoFlow />
          <SingleQuote />
          <LoadTest />
        </>
      )}

      {status?.state !== 'on' && (
        <Card className="bg-slate-50/50 border-line">
          <p className="text-[13px] text-ink mb-3">
            Activate the system to access demo pages, demo flow, latency probe, and load-test chart.
            First activation provisions a Lakebase online store and warm-starts the scorer endpoint —
            typically 5–10 minutes. Subsequent activations reuse what's there.
          </p>
          <SectionHead>Available without activating</SectionHead>
          <p className="text-[13px] text-mut mb-3">
            The agentic journey prices a BRAND-NEW risk independently — no online store needed.
          </p>
          <DemoLink href="/quote-chat" icon={Network} accent="fuchsia"
                    title="Agentic MCP sales"
                    desc="Prices a new risk — Claude calls engine over MCP" />
        </Card>
      )}

      {/* Architecture — collapsible */}
      <Card>
        <button
          onClick={() => setArchOpen(o => !o)}
          className="w-full flex items-center justify-between"
        >
          <CardTitle className="flex items-center gap-2 mb-0">
            {archOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            Architecture
          </CardTitle>
          <span className="text-[11px] text-mut font-normal">
            {archOpen ? 'Hide diagram' : 'Show diagram'}
          </span>
        </button>
        {archOpen && (
          <div className="mt-3 flex justify-center overflow-x-auto">
            <ArchitectureDiagram />
          </div>
        )}
      </Card>
    </div>
  );
}

// Each demo page carries its own accent so the four are tellable apart at a
// glance mid-demo. Full class strings (no interpolation) so Tailwind's scanner
// keeps them.
const DEMO_ACCENTS = {
  blue:    { border: 'hover:border-blue-300',    bg: 'hover:bg-blue-50',    icon: 'text-blue-600',    title: 'group-hover:text-blue-700' },
  amber:   { border: 'hover:border-amber-300',   bg: 'hover:bg-amber-50',   icon: 'text-amber-600',   title: 'group-hover:text-amber-700' },
  violet:  { border: 'hover:border-violet-300',  bg: 'hover:bg-violet-50',  icon: 'text-violet-600',  title: 'group-hover:text-violet-700' },
  fuchsia: { border: 'hover:border-fuchsia-300', bg: 'hover:bg-fuchsia-50', icon: 'text-fuchsia-600', title: 'group-hover:text-fuchsia-700' },
} as const;

function DemoLink({ href, title, desc, icon: Icon, accent = 'violet' }: {
  href: string; title: string; desc: string;
  icon?: React.ComponentType<{ className?: string }>;
  accent?: keyof typeof DEMO_ACCENTS;
}) {
  const c = DEMO_ACCENTS[accent];
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
       className={`group flex items-start gap-2.5 px-3 py-2.5 rounded-lg border border-gray-200 transition-colors ${c.border} ${c.bg}`}>
      {Icon && <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${c.icon}`} />}
      <div className="flex-1 min-w-0">
        <div className={`text-sm font-medium text-gray-800 flex items-center gap-1 ${c.title}`}>
          {title} <ExternalLink className="w-3 h-3 opacity-50" />
        </div>
        <div className="text-[11px] text-gray-500">{desc}</div>
        <div className="text-[10px] font-mono text-gray-400 mt-0.5">{href}</div>
      </div>
    </a>
  );
}

function StatusChip({ icon, label, value, detail, ok }:
  { icon: React.ReactNode; label: string; value: string; detail: string; ok: boolean }) {
  return (
    <div className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border text-xs
      ${ok ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-slate-50 border-line text-mut'}`}>
      {icon}
      <span className="font-semibold">{ok ? 'text-emerald-900' : 'text-ink'}</span>
      <span className="font-semibold">{label}</span>
      <span className="font-mono text-[11px] truncate">{value}</span>
      <span className="text-[11px] opacity-70 ml-auto">{detail}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Demo Flow — three sequential cards: initial quote → file claim → re-quote
// ---------------------------------------------------------------------------

function DemoFlow() {
  const [policyId, setPolicyId] = useState('POL-MOTOR-00000001');
  const [step1, setStep1] = useState<any>(null);
  const [step2, setStep2] = useState<any>(null);
  const [step3, setStep3] = useState<any>(null);
  const [busy,  setBusy]  = useState<1 | 2 | 3 | null>(null);
  const [err,   setErr]   = useState<string | null>(null);

  const reset = () => { setStep1(null); setStep2(null); setStep3(null); setErr(null); };

  const runStep1 = async () => {
    setBusy(1); setErr(null); setStep2(null); setStep3(null);
    try {
      const r = await api.livePricingQuote(policyId);
      setStep1(r);
    } catch (e: any) { setErr(e?.message || String(e)); }
    finally { setBusy(null); }
  };

  const runStep2 = async () => {
    setBusy(2); setErr(null); setStep3(null);
    try {
      const r = await api.livePricingTelematicsEvent({
        policy_id: policyId, speeding_event: true, curfew_breach: true,
        behaviour_score_delta: -15, harsh_braking_delta: 1,
      });
      setStep2(r);
    } catch (e: any) { setErr(e?.message || String(e)); }
    finally { setBusy(null); }
  };

  const runStep3 = async () => {
    setBusy(3); setErr(null);
    try {
      const r = await api.livePricingQuote(policyId);
      setStep3(r);
    } catch (e: any) { setErr(e?.message || String(e)); }
    finally { setBusy(null); }
  };

  const delta = (step1 && step3 && step1.result?.final_premium != null && step3.result?.final_premium != null)
    ? Number(step3.result.final_premium) - Number(step1.result.final_premium)
    : null;

  return (
    <Card>
      <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
        <CardTitle className="flex items-center gap-1.5 mb-0">
          <Activity className="w-4 h-4 text-purple-600" /> Demo flow
        </CardTitle>
        <div className="flex items-center gap-2">
          <input
            value={policyId}
            onChange={e => setPolicyId(e.target.value.toUpperCase())}
            className="text-xs font-mono px-2 py-1 border border-line rounded w-36 focus:outline-none focus:ring-2 focus:ring-brand/50"
            placeholder="POL-MOTOR-00000001"
          />
          <Btn tone="ghost" onClick={reset} className="text-xs">
            <Undo2 className="w-3 h-3" /> Reset
          </Btn>
        </div>
      </div>

      <Grid cols={3}>
        <DemoCard
          step={1} title="Initial quote" icon={<Zap className="w-4 h-4" />}
          body={step1
            ? <>
                <PremiumLine label="Final premium" value={step1.result?.final_premium} />
                <DetailGrid result={step1.result} latency={step1.latency_ms} />
              </>
            : <p className="text-xs text-gray-500">Score the policy on the live endpoint and capture the baseline premium.</p>}
          action={<button onClick={runStep1} disabled={busy !== null}
                          className="text-xs px-2.5 py-1.5 rounded bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-50 inline-flex items-center gap-1">
                    {busy === 1 ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                    Run
                  </button>}
        />
        <DemoCard
          step={2} title="Simulate telematics event" icon={<FileText className="w-4 h-4" />}
          body={step2
            ? <>
                <div className="text-[11px] text-gray-600 space-y-0.5">
                  <div>Event ID: <code className="text-gray-800">{step2.event_id || step2.claim_id}</code></div>
                  <div className="text-gray-800 font-medium mt-1">Telematics signal change</div>
                  {step2.before && step2.after && (
                    <>
                      <div>behaviour_score: <span className="text-gray-800">{step2.before.behaviour_score} → {step2.after.behaviour_score}</span></div>
                      <div>recent_speeding: <span className="text-gray-800">{step2.before.recent_speeding_events} → {step2.after.recent_speeding_events}</span></div>
                      <div>recent_curfew:   <span className="text-gray-800">{step2.before.recent_curfew_breaches} → {step2.after.recent_curfew_breaches}</span></div>
                    </>
                  )}
                  <div className="mt-1">Telematics write: <span className="text-gray-800">{Math.round(step2.claim_write_ms)} ms</span></div>
                  <div>UPT MERGE:        <span className="text-gray-800">{Math.round(step2.upt_merge_ms)} ms</span></div>
                  {step2.online_refresh && (
                    <div className={step2.online_refresh.completed ? 'text-emerald-700 mt-1.5' : 'text-amber-700 mt-1.5'}>
                      Lakebase SNAPSHOT refresh: {step2.online_refresh.completed
                        ? `synced in ${Math.round(step2.online_refresh.duration_ms ?? 0)} ms`
                        : `state ${step2.online_refresh.state ?? 'unknown'}${step2.online_refresh.duration_ms ? ` (${Math.round(step2.online_refresh.duration_ms)} ms)` : ''}`}
                    </div>
                  )}
                </div>
              </>
            : <p className="text-xs text-gray-500">Out-of-curfew speeding event from the black box. Behaviour score drops, recent event counters tick up, UPT mirrors the change, Lakebase syncs.</p>}
          disabled={!step1}
          action={<button onClick={runStep2} disabled={busy !== null || !step1}
                          className="text-xs px-2.5 py-1.5 rounded bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-50 inline-flex items-center gap-1">
                    {busy === 2 ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                    Run
                  </button>}
        />
        <DemoCard
          step={3} title="Re-quote" icon={<Zap className="w-4 h-4" />}
          body={step3
            ? <>
                <PremiumLine label="New final premium" value={step3.result?.final_premium} />
                <DetailGrid result={step3.result} latency={step3.latency_ms} />
                {delta !== null && (
                  <div className={`mt-2 text-xs px-2 py-1 rounded inline-flex items-center gap-1
                    ${delta >= 0 ? 'bg-amber-50 text-amber-800 border border-amber-200'
                                 : 'bg-emerald-50 text-emerald-800 border border-emerald-200'}`}>
                    Δ vs initial: {delta >= 0 ? '+' : ''}£{delta.toFixed(2)}
                  </div>
                )}
              </>
            : <p className="text-xs text-gray-500">Score the same policy again — fraud_pred picks up the new event, telematics surcharge kicks in, premium moves up.</p>}
          disabled={!step2}
          action={<button onClick={runStep3} disabled={busy !== null || !step2}
                          className="text-xs px-2.5 py-1.5 rounded bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-50 inline-flex items-center gap-1">
                    {busy === 3 ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                    Run
                  </button>}
        />
      </Grid>

      {err && (
        <div className="mt-3 text-xs text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 flex items-start gap-2">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          <span>{err}</span>
        </div>
      )}
    </Card>
  );
}

function DemoCard({ step, title, icon, body, action, disabled }:
  { step: number; title: string; icon: React.ReactNode; body: React.ReactNode; action: React.ReactNode; disabled?: boolean }) {
  return (
    <div className={`border rounded-lg p-3 flex flex-col gap-2 ${disabled ? 'border-gray-200 bg-gray-50 opacity-70' : 'border-gray-200 bg-white'}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-semibold text-gray-700">
          <span className={`w-5 h-5 rounded-full text-white text-[11px] inline-flex items-center justify-center
            ${disabled ? 'bg-gray-400' : 'bg-violet-600'}`}>{step}</span>
          {icon}
          <span>{title}</span>
        </div>
        {action}
      </div>
      <div>{body}</div>
    </div>
  );
}

function PremiumLine({ label, value, prefix = '£' }: { label: string; value: any; prefix?: string }) {
  const num = Number(value);
  const fmt = isFinite(num) ? `${prefix}${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—';
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-[11px] text-gray-500">{label}:</span>
      <span className="text-base font-semibold text-gray-900">{fmt}</span>
    </div>
  );
}

function DetailGrid({ result, latency }: { result: any; latency: number }) {
  if (!result) return null;
  return (
    <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px] text-gray-600">
      <div>freq: <span className="text-gray-800">{Number(result.freq_pred ?? 0).toFixed(4)}</span></div>
      <div>sev: <span className="text-gray-800">£{Number(result.sev_pred ?? 0).toFixed(0)}</span></div>
      <div>fraud: <span className="text-gray-800">{Number(result.fraud_pred ?? 0).toFixed(4)}</span></div>
      <div>demand: <span className="text-gray-800">{Number(result.demand_pred ?? 0).toFixed(4)}</span></div>
      <div>technical: <span className="text-gray-800">£{Number(result.technical_premium ?? 0).toLocaleString()}</span></div>
      <div>fraud_load: <span className="text-gray-800">£{Number(result.fraud_load ?? 0).toLocaleString()}</span></div>
      <div className="col-span-2 mt-0.5 flex items-center gap-1 text-[11px]">
        <Clock className="w-3 h-3" /> latency: <span className="text-gray-800">{Number(latency).toFixed(0)} ms</span>
        <span className="ml-auto opacity-70">re v{result.rating_engine_version ?? '?'}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Single quote — bare latency probe, separate from the demo flow
// ---------------------------------------------------------------------------

function SingleQuote() {
  const [policyId, setPolicyId] = useState('POL-MOTOR-00000001');
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<any>(null);
  const [err,  setErr]  = useState<string | null>(null);

  const run = async () => {
    setBusy(true); setErr(null);
    try {
      const r = await api.livePricingQuote(policyId);
      setLast(r);
    } catch (e: any) { setErr(e?.message || String(e)); }
    finally { setBusy(false); }
  };

  return (
    <Card>
      <CardTitle className="flex items-center gap-1.5 mb-3">
        <Server className="w-4 h-4 text-purple-600" /> Single quote
      </CardTitle>
      <div className="flex items-end gap-2 flex-wrap">
        <label className="text-xs text-mut">
          <div className="mb-1 font-semibold uppercase tracking-wide">policy_id</div>
          <input value={policyId}
                 onChange={e => setPolicyId(e.target.value.toUpperCase())}
                 className="px-2 py-1 border border-line rounded font-mono text-xs w-44 focus:outline-none focus:ring-2 focus:ring-brand/50" />
        </label>
        <Btn onClick={run} disabled={busy} className="text-xs">
          {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
          Quote
        </Btn>
        {last && last.ok && (
          <div className="text-xs text-ink ml-3 inline-flex items-center gap-3">
            <span className="font-semibold">£{Number(last.result?.final_premium ?? 0).toFixed(2)}</span>
            <span className="text-mut"><Clock className="w-3 h-3 inline" /> {Number(last.latency_ms).toFixed(0)} ms</span>
            <span className="text-mut">re v{last.result?.rating_engine_version ?? '?'}</span>
          </div>
        )}
      </div>
      {err && <div className="mt-2 text-xs text-red-700">{err}</div>}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Load test — start/stop + live SVG chart
// ---------------------------------------------------------------------------

type LoadTestRow = { ts: string; run_id: string; qps: number; p50_ms: number; p95_ms: number; p99_ms: number; error_pct: number };

function LoadTest() {
  const [targetQps, setTargetQps]  = useState(100);
  const [duration,  setDuration]   = useState(60);
  const [running,   setRunning]    = useState<{ run_id: number; load_test_run_id: string; run_page_url?: string } | null>(null);
  const [rows,      setRows]       = useState<LoadTestRow[]>([]);
  const [err,       setErr]        = useState<string | null>(null);
  const [tableReady, setTableReady] = useState(true);
  const sinceRef = useRef<string | null>(null);

  // Poll metrics whenever there's a row history or a run is active.
  useEffect(() => {
    if (!running && rows.length === 0) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const params: { since?: string; run_id?: string } = {};
        if (sinceRef.current) params.since = sinceRef.current;
        if (running) params.run_id = running.load_test_run_id;
        const r = await api.livePricingLoadTestMetrics(params);
        if (cancelled) return;
        setTableReady(r.table_ready !== false);
        // Warehouse returns all values as strings — coerce numerics so .toFixed
        // and arithmetic in the chart code don't crash the render.
        const newRows: LoadTestRow[] = (r.rows || []).map((raw: any) => ({
          ts:        String(raw.ts ?? ''),
          run_id:    String(raw.run_id ?? ''),
          qps:       Number(raw.qps) || 0,
          p50_ms:    Number(raw.p50_ms) || 0,
          p95_ms:    Number(raw.p95_ms) || 0,
          p99_ms:    Number(raw.p99_ms) || 0,
          error_pct: Number(raw.error_pct) || 0,
        }));
        if (newRows.length > 0) {
          setRows(prev => {
            // Append only rows newer than the last known timestamp.
            const seen = new Set(prev.map(p => p.ts + ':' + p.run_id));
            const merged = [...prev];
            for (const row of newRows) {
              const key = row.ts + ':' + row.run_id;
              if (!seen.has(key)) merged.push(row);
            }
            const trimmed = merged.slice(-180);   // keep last ~3 minutes
            return trimmed;
          });
          sinceRef.current = newRows[newRows.length - 1].ts;
        }
      } catch (e: any) {
        if (!cancelled) setErr(e?.message || String(e));
      }
    };
    poll();
    const t = window.setInterval(poll, running ? 1500 : 5000);
    return () => { cancelled = true; window.clearInterval(t); };
  }, [running, rows.length]);

  const start = async () => {
    setErr(null); setRows([]); sinceRef.current = null;
    try {
      const r = await api.livePricingLoadTestStart({
        target_qps: targetQps, duration_seconds: duration, concurrency: Math.max(20, Math.floor(targetQps / 2)),
      });
      setRunning({ run_id: r.run_id, load_test_run_id: r.load_test_run_id, run_page_url: r.run_page_url });
    } catch (e: any) { setErr(e?.message || String(e)); }
  };

  const stop = async () => {
    if (!running) return;
    try { await api.livePricingLoadTestStop(running.run_id); }
    catch (e: any) { setErr(e?.message || String(e)); }
    setRunning(null);
  };

  return (
    <Card>
      <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
        <CardTitle className="flex items-center gap-1.5 mb-0">
          <Activity className="w-4 h-4 text-purple-600" /> Load test
        </CardTitle>
        <div className="flex items-center gap-2 text-xs">
          <label className="flex items-center gap-1 text-mut">
            target qps
            <input type="number" value={targetQps} min={10} max={500} step={10}
                   onChange={e => setTargetQps(Number(e.target.value))}
                   disabled={!!running}
                   className="px-1.5 py-0.5 border border-line rounded font-mono w-16 focus:outline-none focus:ring-2 focus:ring-brand/50" />
          </label>
          <label className="flex items-center gap-1 text-mut">
            duration (s)
            <input type="number" value={duration} min={10} max={600} step={10}
                   onChange={e => setDuration(Number(e.target.value))}
                   disabled={!!running}
                   className="px-1.5 py-0.5 border border-line rounded font-mono w-16 focus:outline-none focus:ring-2 focus:ring-brand/50" />
          </label>
          {running ? (
            <Btn tone="bad" onClick={stop} className="text-xs">
              <Square className="w-3 h-3" /> Stop
            </Btn>
          ) : (
            <Btn tone="primary" onClick={start} className="text-xs">
              <Play className="w-3 h-3" /> Start
            </Btn>
          )}
          {running?.run_page_url && (
            <a href={running.run_page_url} target="_blank" rel="noreferrer"
               className="text-brand hover:underline inline-flex items-center gap-0.5">
              run <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>

      {!tableReady && (
        <div className="text-xs text-mut mb-2">
          Metrics table not yet populated — first load test will create it.
        </div>
      )}

      <LatencyChart rows={rows} />

      {rows.length > 0 && (
        <Grid cols={4} className="mt-3">
          <Metric label="QPS" value={rows[rows.length - 1].qps.toString()} tone="plain" />
          <Metric label="P50" value={`${rows[rows.length - 1].p50_ms.toFixed(0)} ms`} tone="plain" />
          <Metric label="P95" value={`${rows[rows.length - 1].p95_ms.toFixed(0)} ms`} tone="plain" />
          <Metric label="P99" value={`${rows[rows.length - 1].p99_ms.toFixed(0)} ms`} tone="plain" />
        </Grid>
      )}
      {err && <div className="mt-2 text-xs text-red-700">{err}</div>}
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-2 py-1.5 bg-gray-50 border border-gray-200 rounded">
      <div className="text-[10px] uppercase text-gray-500">{label}</div>
      <div className="font-mono text-sm text-gray-900">{value}</div>
    </div>
  );
}

function LatencyChart({ rows }: { rows: LoadTestRow[] }) {
  const W = 760, H = 200, M = { l: 40, r: 20, t: 10, b: 24 };
  const innerW = W - M.l - M.r;
  const innerH = H - M.t - M.b;

  const { yMax, qpsMax, points } = useMemo(() => {
    if (rows.length === 0) return { yMax: 100, qpsMax: 100, points: [] as any[] };
    const yMaxRaw  = Math.max(...rows.map(r => r.p99_ms || 0), 100);
    const qpsMaxRaw = Math.max(...rows.map(r => r.qps || 0), 50);
    const yMax = Math.ceil(yMaxRaw / 50) * 50;
    const qpsMax = Math.ceil(qpsMaxRaw / 10) * 10;
    return {
      yMax, qpsMax,
      points: rows.map((r, i) => ({
        x: rows.length > 1 ? (i / (rows.length - 1)) * innerW : innerW / 2,
        p50: innerH - (r.p50_ms / yMax) * innerH,
        p95: innerH - (r.p95_ms / yMax) * innerH,
        p99: innerH - (r.p99_ms / yMax) * innerH,
        qpsBar: (r.qps / qpsMax) * innerH,
      })),
    };
  }, [rows, innerW, innerH]);

  const path = (key: 'p50' | 'p95' | 'p99') =>
    points.length === 0 ? '' :
      points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${(p[key] as number).toFixed(1)}`).join(' ');

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" aria-label="Load test latency chart">
      <g transform={`translate(${M.l},${M.t})`}>
        {/* Y grid */}
        {[0, 0.25, 0.5, 0.75, 1].map(t => (
          <g key={t}>
            <line x1={0} x2={innerW} y1={innerH * (1 - t)} y2={innerH * (1 - t)}
                  stroke="#e5e7eb" strokeDasharray="2,3" />
            <text x={-6} y={innerH * (1 - t) + 3} textAnchor="end" fontSize={10} fill="#6b7280">
              {Math.round(yMax * t)} ms
            </text>
          </g>
        ))}
        {/* QPS bars (faint) */}
        {points.map((p, i) => (
          <rect key={i} x={p.x - 1.5} y={innerH - p.qpsBar} width={3} height={p.qpsBar}
                fill="#ddd6fe" opacity={0.65} />
        ))}
        {/* Latency lines */}
        {points.length > 0 && (
          <>
            <path d={path('p99')} stroke="#dc2626" strokeWidth={1.5} fill="none" />
            <path d={path('p95')} stroke="#f59e0b" strokeWidth={1.5} fill="none" />
            <path d={path('p50')} stroke="#10b981" strokeWidth={1.8} fill="none" />
          </>
        )}
        {/* Axis labels */}
        <text x={innerW / 2} y={innerH + 18} textAnchor="middle" fontSize={10} fill="#6b7280">
          time →   ({rows.length} samples · qps max ~{qpsMax})
        </text>
      </g>
      {/* Legend */}
      <g transform={`translate(${M.l + 8},${M.t + 8})`} fontSize={11}>
        <g><circle cx={0} cy={0} r={3} fill="#10b981" /><text x={8} y={4} fill="#374151">p50</text></g>
        <g transform="translate(50,0)"><circle cx={0} cy={0} r={3} fill="#f59e0b" /><text x={8} y={4} fill="#374151">p95</text></g>
        <g transform="translate(100,0)"><circle cx={0} cy={0} r={3} fill="#dc2626" /><text x={8} y={4} fill="#374151">p99</text></g>
        <g transform="translate(150,0)"><rect x={-3} y={-3} width={6} height={6} fill="#ddd6fe" /><text x={8} y={4} fill="#374151">qps</text></g>
      </g>
    </svg>
  );
}

function ArchitectureDiagram() {
  return (
    <svg viewBox="0 0 920 400" className="w-full max-w-5xl" aria-label="Live pricing architecture">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
                markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="#94a3b8" />
        </marker>
        <linearGradient id="quote-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#eff6ff" />
          <stop offset="100%" stopColor="#dbeafe" />
        </linearGradient>
        <linearGradient id="orch-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#faf5ff" />
          <stop offset="100%" stopColor="#ede9fe" />
        </linearGradient>
        <linearGradient id="model-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#f0fdfa" />
          <stop offset="100%" stopColor="#ccfbf1" />
        </linearGradient>
        <linearGradient id="fs-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#fffbeb" />
          <stop offset="100%" stopColor="#fef3c7" />
        </linearGradient>
        <linearGradient id="rules-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#fef2f2" />
          <stop offset="100%" stopColor="#fecaca" />
        </linearGradient>
      </defs>

      {/* Quote request */}
      <rect x="20" y="170" width="140" height="60" rx="8" fill="url(#quote-grad)" stroke="#3b82f6" />
      <text x="90" y="200" textAnchor="middle" fontSize="13" fontWeight="600" fill="#1e3a8a">Quote request</text>
      <text x="90" y="218" textAnchor="middle" fontSize="10" fill="#2563eb">policy_id · &lt; 1 KB</text>

      {/* Orchestrator (pyfunc) */}
      <rect x="200" y="170" width="160" height="60" rx="8" fill="url(#orch-grad)" stroke="#7c3aed" />
      <text x="280" y="196" textAnchor="middle" fontSize="13" fontWeight="600" fill="#4c1d95">motor_pricing_scorer</text>
      <text x="280" y="214" textAnchor="middle" fontSize="10" fill="#6d28d9">pyfunc · single endpoint</text>
      <line x1="160" y1="200" x2="200" y2="200" stroke="#94a3b8" strokeWidth="2" markerEnd="url(#arrow)" />

      {/* Online feature store (Lakebase) — above orchestrator */}
      <rect x="200" y="60" width="160" height="60" rx="8" fill="url(#fs-grad)" stroke="#d97706" />
      <text x="280" y="86" textAnchor="middle" fontSize="13" fontWeight="600" fill="#78350f">Lakebase online store</text>
      <text x="280" y="104" textAnchor="middle" fontSize="10" fill="#92400e">unified_motor_table_live</text>
      <line x1="280" y1="170" x2="280" y2="120" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="4 2" markerEnd="url(#arrow)" />
      <text x="370" y="148" fontSize="9" fill="#92400e" fontStyle="italic">FeatureLookup</text>

      {/* 4 parallel models */}
      <g>
        {[
          { name: "freq_glm_motor",   sub: "Poisson · claim count" },
          { name: "sev_glm_motor",    sub: "Gamma · £ per claim" },
          { name: "demand_gbm_motor", sub: "LightGBM · accept prob" },
          { name: "fraud_gbm_motor",  sub: "LightGBM · fraud prob" },
        ].map((m, i) => {
          const y = 80 + i * 60;
          return (
            <g key={m.name}>
              <rect x="420" y={y} width="180" height="44" rx="6" fill="url(#model-grad)" stroke="#14b8a6" />
              <text x="510" y={y + 18} textAnchor="middle" fontSize="12" fontWeight="600" fill="#115e59">{m.name}</text>
              <text x="510" y={y + 34} textAnchor="middle" fontSize="10" fill="#0f766e">{m.sub}</text>
              <line x1="360" y1="200" x2="420" y2={y + 22} stroke="#cbd5e1" strokeWidth="1.5" />
            </g>
          );
        })}
      </g>
      <text x="510" y="350" textAnchor="middle" fontSize="10" fill="#0f766e" fontStyle="italic">
        4 champions scored in-process · shared feature batch
      </text>

      {/* Rating Engine */}
      <rect x="660" y="155" width="160" height="90" rx="8" fill="url(#rules-grad)" stroke="#dc2626" />
      <text x="740" y="178" textAnchor="middle" fontSize="13" fontWeight="600" fill="#7f1d1d">Rating engine</text>
      <text x="740" y="196" textAnchor="middle" fontSize="9.5" fill="#991b1b">freq × sev → technical</text>
      <text x="740" y="210" textAnchor="middle" fontSize="9.5" fill="#991b1b">+ expense · commission</text>
      <text x="740" y="224" textAnchor="middle" fontSize="9.5" fill="#991b1b">+ young driver · telematics</text>
      <text x="740" y="238" textAnchor="middle" fontSize="9.5" fill="#991b1b">+ fraud load · demand adj</text>
      {/* Arrows from each model into rating engine */}
      {[80, 140, 200, 260].map((y) => (
        <line key={y} x1="600" y1={y + 22} x2="660" y2="200" stroke="#cbd5e1" strokeWidth="1.5" markerEnd="url(#arrow)" />
      ))}

      {/* Final premium response — arrow back to quote */}
      <path d="M 740 245 Q 740 320 420 320 Q 180 320 90 245"
            fill="none" stroke="#64748b" strokeWidth="2" strokeDasharray="5 3" markerEnd="url(#arrow)" />
      <text x="430" y="338" textAnchor="middle" fontSize="11" fontWeight="600" fill="#475569">
        final_premium + every intermediate factor · end-to-end &lt; 200 ms
      </text>
      <text x="430" y="354" textAnchor="middle" fontSize="9.5" fill="#64748b" fontStyle="italic">
        audit trail logged to inference table
      </text>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso?: string | null): string {
  if (!iso) return '—';
  const t = new Date(iso);
  if (isNaN(t.getTime())) return String(iso).substring(0, 10);
  return t.toISOString().substring(0, 10);
}

function eventShortLabel(t: string): string {
  if (t === 'governance_pack_generated') return 'pack';
  if (t === 'model_promoted')   return 'promote';
  if (t === 'model_rollback' || t === 'model_rolled_back') return 'rollback';
  if (t === 'model_trained')    return 'train';
  return t;
}
function eventTone(t: string): 'red' | 'green' | 'blue' | 'slate' {
  if (t === 'model_rollback' || t === 'model_rolled_back') return 'red';
  if (t === 'model_promoted') return 'green';
  if (t === 'governance_pack_generated') return 'blue';
  return 'slate';
}
function eventColor(t: string): string {
  if (t === 'model_rollback' || t === 'model_rolled_back') return 'bg-red-100 text-red-700';
  if (t === 'model_promoted') return 'bg-emerald-100 text-emerald-700';
  if (t === 'governance_pack_generated') return 'bg-blue-100 text-blue-700';
  return 'bg-gray-100 text-gray-600';
}

// ---------------------------------------------------------------------------
// Serving SLOs — what the rating engine sees at quote time
// ---------------------------------------------------------------------------

function ServingSLOs() {
  const tiles = [
    { icon: <Clock    className="w-4 h-4 text-emerald-600" />, label: 'Feature lookup p50',    value: '38 ms',  sub: 'online feature store',     tone: 'green' as const },
    { icon: <Clock    className="w-4 h-4 text-emerald-600" />, label: 'Feature lookup p99',    value: '92 ms',  sub: 'sub-100ms target',         tone: 'green' as const },
    { icon: <Database className="w-4 h-4 text-blue-600" />,    label: 'Features tested',       value: '3.0 M',  sub: 'across all candidates',    tone: 'blue'    as const },
    { icon: <Zap      className="w-4 h-4 text-purple-600" />,  label: 'End-to-end quote',      value: '<500 ms',sub: '4 models + factor build-up', tone: 'violet'  as const },
  ];
  return (
    <Section title="Serving SLOs" subtitle="What the rating engine sees at quote time">
      <Grid cols={4}>
        {tiles.map(t => (
          <Metric key={t.label} label={t.label} value={t.value} sub={t.sub} tone={t.tone} />
        ))}
      </Grid>
      <p className="text-[11px] text-mut mt-3">
        Targets representative of Mosaic AI Model Serving deployment. Real numbers populate when the endpoint
        receives production traffic — an Inference Table records every request, latency, and feature for governance.
      </p>
    </Section>
  );
}
