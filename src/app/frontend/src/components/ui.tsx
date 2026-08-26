// Shared UI primitives — the Bricksurance workbench design language, matched to
// the underwriting / reserving / reinsurance / ifrs17 demos:
//   • #2563eb brand blue, #f8fafc page, #e2e8f0 hairlines, system font 14px
//   • eyebrow + h1 + sub page headers
//   • the "On this page" indigo→purple explainer callout on every page
//   • white cards w/ uppercase-muted titles, .big metric values, pills, buttons
//   • the purple-gradient AI ask box
// Import from '../components/ui'. Use these instead of bespoke markup so pages
// stay consistent with the rest of the workbench family.

import { useState, useEffect } from 'react';
import type { ReactNode, ComponentType } from 'react';
import { ChevronRight, Sparkles, Send, Loader2, Archive, Zap } from 'lucide-react';
import { api } from '../lib/api';

// ---------------------------------------------------------------------------
// Page header — eyebrow (brand, uppercase) + title + subtitle + optional actions
// ---------------------------------------------------------------------------
export function PageHeader({ eyebrow, title, subtitle, icon: Icon, actions }: {
  eyebrow: string; title: string; subtitle?: string;
  icon?: ComponentType<{ className?: string }>; actions?: ReactNode;
}) {
  return (
    <header className="mb-5 flex items-start gap-3">
      {Icon && (
        <div className="w-10 h-10 rounded-xl bg-brand/10 flex items-center justify-center shrink-0 mt-0.5">
          <Icon className="w-5 h-5 text-brand" />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-bold uppercase tracking-[0.08em] text-brand">{eyebrow}</div>
        <h1 className="text-2xl font-bold text-ink leading-tight">{title}</h1>
        {subtitle && <p className="text-mut text-[13.5px] mt-1 leading-relaxed">{subtitle}</p>}
      </div>
      {actions && <div className="shrink-0 flex items-center gap-2">{actions}</div>}
    </header>
  );
}

// ---------------------------------------------------------------------------
// OnThisPage — the "On this page" explainer callout (indigo→purple). Put one
// near the top of every page: what it is / what to look at.
// ---------------------------------------------------------------------------
export function OnThisPage({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-2.5 items-start bg-[linear-gradient(90deg,#eef2ff,#faf5ff)] border border-[#ddd6fe] rounded-[10px] px-3.5 py-2.5 text-[12.5px] text-[#4338ca] leading-relaxed">
      <span className="shrink-0 font-bold uppercase tracking-wide text-[10px] text-[#6d28d9] bg-white border border-[#ddd6fe] rounded-md px-1.5 py-1">On this page</span>
      <span>{children}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Card + CardTitle + Section
// ---------------------------------------------------------------------------
export function Card({ children, className = '', onClick, drill }: {
  children?: ReactNode; className?: string; onClick?: () => void; drill?: boolean;
}) {
  return (
    <div onClick={onClick}
      className={`bg-white border border-line rounded-xl p-4 ${drill ? 'cursor-pointer transition hover:-translate-y-0.5 hover:shadow-[0_8px_22px_rgba(15,23,42,.1)]' : ''} ${className}`}>
      {children}
    </div>
  );
}
export function CardTitle({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <h3 className={`text-[13px] text-mut font-semibold uppercase tracking-[0.04em] mb-2 ${className}`}>{children}</h3>;
}
export function Section({ title, subtitle, actions, children, className = '' }: {
  title: string; subtitle?: string; actions?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={`bg-white border border-line rounded-xl p-4 ${className}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h2 className="text-base font-bold text-ink">{title}</h2>
          {subtitle && <p className="text-mut text-[13px] mt-0.5">{subtitle}</p>}
        </div>
        {actions && <div className="shrink-0">{actions}</div>}
      </div>
      {children}
    </section>
  );
}

// Section eyebrow header used between blocks (uppercase muted).
export function SectionHead({ children }: { children: ReactNode }) {
  return <div className="text-xs font-bold uppercase tracking-[0.07em] text-mut mt-6 mb-2">{children}</div>;
}

// ---------------------------------------------------------------------------
// Metric — a big number with a label; optional colored tint (KPI style).
// ---------------------------------------------------------------------------
const tint: Record<string, string> = {
  blue: 'bg-[#eff6ff] border-[#bfdbfe] text-[#1d4ed8]',
  green: 'bg-[#f0fdf4] border-[#bbf7d0] text-[#15803d]',
  amber: 'bg-[#fffbeb] border-[#fde68a] text-[#b45309]',
  violet: 'bg-[#faf5ff] border-[#ddd6fe] text-[#6d28d9]',
  red: 'bg-[#fef2f2] border-[#fecaca] text-[#dc2626]',
  plain: 'bg-white border-line text-ink',
};
export function Metric({ label, value, sub, tone = 'plain' }: {
  label: string; value: ReactNode; sub?: string; tone?: 'blue' | 'green' | 'amber' | 'violet' | 'red' | 'plain';
}) {
  const t = tint[tone];
  return (
    <div className={`rounded-xl border px-4 py-3 ${tone === 'plain' ? 'bg-white border-line' : t}`}>
      <div className="text-[11px] font-bold uppercase tracking-[0.05em] text-mut">{label}</div>
      <div className={`text-[26px] font-extrabold leading-tight mt-0.5 ${tone === 'plain' ? 'text-ink' : t.split(' ').find(c => c.startsWith('text-'))}`}>{value}</div>
      {sub && <div className="text-mut text-[12.5px] mt-0.5">{sub}</div>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pill / status badge
// ---------------------------------------------------------------------------
const pillTone: Record<string, string> = {
  red: 'bg-red-50 text-red-600', amber: 'bg-amber-50 text-amber-600',
  green: 'bg-emerald-50 text-emerald-600', blue: 'bg-blue-100 text-blue-700',
  slate: 'bg-slate-200 text-slate-700', live: 'bg-emerald-50 text-emerald-600',
};
export function Pill({ children, tone = 'slate', className = '' }: {
  children: ReactNode; tone?: 'red' | 'amber' | 'green' | 'blue' | 'slate' | 'live'; className?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold ${pillTone[tone]} ${className}`}>
      {tone === 'live' && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />}
      {children}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Button
// ---------------------------------------------------------------------------
const btnTone: Record<string, string> = {
  primary: 'bg-brand text-white hover:bg-brand-dark',
  ghost: 'bg-[#eef2ff] text-brand hover:bg-[#e0e7ff]',
  warn: 'bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100',
  bad: 'bg-red-50 text-red-600 border border-red-200 hover:bg-red-100',
};
export function Btn({ children, tone = 'primary', onClick, disabled, className = '', title }: {
  children: ReactNode; tone?: 'primary' | 'ghost' | 'warn' | 'bad';
  onClick?: () => void; disabled?: boolean; className?: string; title?: string;
}) {
  return (
    <button onClick={onClick} disabled={disabled} title={title}
      className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-[12.5px] font-medium transition disabled:opacity-50 disabled:cursor-not-allowed ${btnTone[tone]} ${className}`}>
      {children}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Callouts: Note (amber), Prov (indigo provenance), DemoDisclaimer (amber)
// ---------------------------------------------------------------------------
export function Note({ children }: { children: ReactNode }) {
  return <div className="bg-amber-50 border border-amber-200 rounded-[10px] px-3.5 py-3 text-[12.5px] text-amber-800 leading-relaxed">{children}</div>;
}
export function Prov({ children }: { children: ReactNode }) {
  return <div className="bg-[#eef2ff] border border-[#c7d2fe] rounded-[10px] px-3.5 py-3 text-[12.5px] text-[#3730a3] leading-relaxed">⛁ {children}</div>;
}
export function DemoDisclaimer({ children }: { children: ReactNode }) {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-2xl px-5 py-4 text-[13px] text-amber-800 leading-relaxed">
      <strong>About this demo.</strong> {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// AskBox — the purple-gradient AI ask box (question + examples + answer).
// Pass onAsk(question) returning the answer text. Reusable across pages.
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Markdown — minimal, dependency-free renderer for agent answers: **bold**,
// `code`, - bullets, 1. numbered, # headings, paragraphs. Replaces the old raw
// whitespace-pre-line dump that leaked ** and {} braces into the UI.
// ---------------------------------------------------------------------------
function mdInline(text: string, kp = ''): ReactNode[] {
  const nodes: ReactNode[] = [];
  const re = /(\*\*([^*]+)\*\*|`([^`]+)`)/g;
  let last = 0, m: RegExpExecArray | null, i = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index));
    if (m[2] != null) nodes.push(<strong key={`${kp}b${i++}`}>{m[2]}</strong>);
    else nodes.push(<code key={`${kp}c${i++}`} className="px-1 py-0.5 rounded bg-slate-100 text-slate-800 text-[12px] font-mono">{m[3]}</code>);
    last = m.index + m[0].length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

export function Markdown({ text, className = '' }: { text: string; className?: string }) {
  const lines = (text || '').split('\n');
  const blocks: ReactNode[] = [];
  let list: string[] = []; let k = 0;
  const flush = () => {
    if (!list.length) return;
    const items = list;
    blocks.push(<ul key={`u${k++}`} className="list-disc pl-5 space-y-1 my-2">{items.map((li, j) => <li key={j}>{mdInline(li, `${k}-${j}-`)}</li>)}</ul>);
    list = [];
  };
  lines.forEach((raw) => {
    const line = raw.replace(/\s+$/, '');
    const bullet = line.match(/^\s*[-*•]\s+(.*)/);
    const num = line.match(/^\s*\d+\.\s+(.*)/);
    if (bullet) { list.push(bullet[1]); return; }
    if (num) { list.push(num[1]); return; }
    flush();
    if (!line.trim()) return;
    const h = line.match(/^#{1,4}\s+(.*)/);
    if (h) blocks.push(<p key={`h${k++}`} className="font-semibold text-ink mt-2">{mdInline(h[1], `${k}-`)}</p>);
    else blocks.push(<p key={`p${k++}`} className="my-1.5">{mdInline(line, `${k}-`)}</p>);
  });
  flush();
  return <div className={className}>{blocks}</div>;
}

// ---------------------------------------------------------------------------
// AskBox — lead-with-agent surface. ON-DEMAND ONLY (no auto-fire on mount, so a
// page never triggers a live agent call just by opening). `compact` renders the
// slim one-line inline variant for inner pages; the full card is the Home
// estate-review lead. Answers render as markdown.
// ---------------------------------------------------------------------------
export function AskBox({ title, subtitle, examples = [], onAsk, placeholder = 'Ask a question…', compact = false }: {
  title: string; subtitle?: string; examples?: string[];
  onAsk: (q: string) => Promise<string>; placeholder?: string; compact?: boolean;
}) {
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);
  const [opened, setOpened] = useState(false);

  const ask = async (question?: string) => {
    const query = (question ?? q).trim();
    if (!query || busy) return;
    setBusy(true); setAnswer(null); setQ(query); setOpened(true);
    try { setAnswer(await onAsk(query)); }
    catch (e: any) { setAnswer(`Error: ${e?.message || e}`); }
    finally { setBusy(false); }
  };

  if (compact) {
    return (
      <div className="border border-line bg-white rounded-xl px-3.5 py-2.5">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#2563eb] shrink-0" />
          <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') ask(); }}
            placeholder={placeholder}
            className="flex-1 bg-transparent text-[13.5px] text-ink focus:outline-none placeholder:text-slate-400" />
          <button onClick={() => ask()} disabled={busy || !q.trim()}
            className="px-3 py-1.5 rounded-md bg-[#2563eb] text-white text-[12.5px] font-semibold disabled:opacity-50 inline-flex items-center gap-1.5">
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />} Ask
          </button>
        </div>
        {examples.length > 0 && !opened && (
          <div className="flex gap-2 flex-wrap mt-2">
            {examples.slice(0, 3).map((ex, i) => (
              <button key={i} onClick={() => ask(ex)} className="text-[11.5px] text-[#2563eb]/80 hover:text-[#2563eb] hover:underline">{ex}</button>
            ))}
          </div>
        )}
        {(busy || answer) && (
          <div className="mt-2.5 border-t border-line pt-2.5 text-sm text-slate-700">
            {busy ? <span className="inline-flex items-center gap-1.5 text-mut"><Loader2 className="w-3.5 h-3.5 animate-spin" /> thinking…</span> : <Markdown text={answer || ''} />}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-indigo-200 bg-gradient-to-br from-slate-50 to-indigo-50/60 px-6 py-5">
      <h2 className="text-[18px] font-bold text-ink flex items-center gap-2"><Sparkles className="w-4.5 h-4.5 text-[#2563eb]" /> {title}</h2>
      {subtitle && <p className="text-[13px] text-mut mt-1 mb-3 leading-relaxed max-w-3xl">{subtitle}</p>}
      {examples.length > 0 && (
        <div className="flex gap-2 flex-wrap mb-3">
          {examples.map((ex, i) => (
            <button key={i} onClick={() => ask(ex)}
              className="bg-white border border-indigo-200 text-slate-700 px-3 py-1.5 rounded-full text-[12px] hover:border-[#2563eb] hover:text-[#2563eb] transition">{ex}</button>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') ask(); }}
          placeholder={placeholder}
          className="flex-1 px-3.5 py-3 rounded-lg border border-line text-[13.5px] text-ink bg-white focus:outline-none focus:ring-2 focus:ring-[#2563eb]/40" />
        <button onClick={() => ask()} disabled={busy || !q.trim()}
          className="px-5 py-3 rounded-lg bg-[#2563eb] text-white font-bold text-[13.5px] disabled:opacity-60 inline-flex items-center gap-1.5">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Ask
        </button>
      </div>
      {(busy || answer) && (
        <div className="mt-3.5 bg-white rounded-xl border border-line px-4 py-3.5 text-ink text-sm leading-relaxed">
          {busy ? <span className="inline-flex items-center gap-1.5 text-mut"><Loader2 className="w-3.5 h-3.5 animate-spin" /> thinking…</span> : <Markdown text={answer || ''} />}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// AgentLead — the lead-with-agent block: a persona's read of the page appears
// first (auto-seeded), then an ask box for follow-ups. Wired to /api/agent/lead.
//   persona: ask_the_book | model_review | rate_change | drift_monitor | explain
// ---------------------------------------------------------------------------
export function AgentLead({ persona, title, subtitle, examples = [], family, context, compact = false }: {
  persona: string; seed?: string; title: string; subtitle?: string;
  examples?: string[]; family?: string; context?: any; compact?: boolean;
}) {
  // On-demand only — never auto-fires. On inner pages pass `compact` for the
  // slim one-line ask; Home uses the full estate-review card. Routes through the
  // managed Mosaic AI Agent Framework endpoint (/api/agent/lead → pwg2_chat_agent),
  // so every call is a real, traced, monitorable agent invocation.
  const onAsk = async (q: string) => {
    const r = await api.agentLead({ persona, question: q, family, context });
    return r?.answer || (r?.error ? `Agent unavailable — ${r.error}` : 'No answer returned.');
  };
  return (
    <AskBox compact={compact} title={title} subtitle={subtitle} examples={examples}
      onAsk={onAsk} placeholder={compact ? 'Ask about this page…' : 'Ask about the estate…'} />
  );
}

// ---------------------------------------------------------------------------
// Collapsible "under the hood" — platform components in play on a page.
// ---------------------------------------------------------------------------
export function UnderTheHood({ title, lines }: {
  title?: string; lines: { component: string; detail: string }[];
}) {
  const [open, setOpen] = useState(false);
  return (
    <section className="border border-line bg-white rounded-xl overflow-hidden">
      <button onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3.5 py-2.5 text-left hover:bg-slate-50 transition">
        <span className="text-[11px] uppercase tracking-[0.08em] font-bold text-mut">⌘ How does this work?</span>
        {title && <span className="text-[11px] text-mut truncate">· {title}</span>}
        <ChevronRight className={`w-3.5 h-3.5 ml-auto text-slate-400 transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>
      {open && (
        <ul className="border-t border-line divide-y divide-slate-100">
          {lines.map((l, i) => (
            <li key={i} className="px-3.5 py-2 flex items-start gap-3 text-sm">
              <code className="font-mono text-[11px] bg-slate-50 border border-line text-slate-800 px-1.5 py-0.5 rounded shrink-0">{l.component}</code>
              <span className="text-slate-700 leading-relaxed">{l.detail}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Skeleton loaders + Page container
// ---------------------------------------------------------------------------
export function Skeleton({ className = 'h-4 w-full' }: { className?: string }) {
  return <div className={`bg-slate-200 rounded animate-pulse ${className}`} />;
}
export function Loading({ label = 'Loading…' }: { label?: string }) {
  return <div className="text-mut py-6 flex items-center gap-2 text-sm"><Loader2 className="w-4 h-4 animate-spin" /> {label}</div>;
}
export function Page({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`max-w-[1180px] px-8 py-7 space-y-5 ${className}`}>{children}</div>;
}

// grid helpers
export function Grid({ cols = 3, children, className = '' }: { cols?: 1 | 2 | 3 | 4 | 5 | 6; children: ReactNode; className?: string }) {
  const c = { 1: '', 2: 'md:grid-cols-2', 3: 'md:grid-cols-3', 4: 'md:grid-cols-4', 5: 'md:grid-cols-5', 6: 'md:grid-cols-6' }[cols];
  return <div className={`grid grid-cols-1 ${c} gap-4 ${className}`}>{children}</div>;
}

// ---------------------------------------------------------------------------
// AiModeBadge — live vs cached toggle. Used in the sidebar AND injected into
// standalone page headers (BrokerChat, QuoteSystem) so the mode is always
// visible when those pages are open direct.
// ---------------------------------------------------------------------------
export function AiModeBadge({ theme = 'dark' }: { theme?: 'dark' | 'light' }) {
  const [mode, setMode] = useState<'live' | 'cached' | null>(null);
  const [busy, setBusy] = useState(false);
  const [entries, setEntries] = useState<number>(0);
  const [denied, setDenied] = useState(false);   // toggle is admin-only (403)

  useEffect(() => {
    fetch('/api/admin/ai-mode')
      .then((r) => r.json())
      .then((d) => { if (d?.mode === 'live' || d?.mode === 'cached') setMode(d.mode); setEntries(d.entries ?? 0); })
      .catch(() => setMode('live'));
  }, []);

  async function flip() {
    if (busy || !mode) return;
    setBusy(true);
    const next = mode === 'live' ? 'cached' : 'live';
    try {
      const r = await fetch('/api/admin/ai-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ mode: next }),
      });
      if (!r.ok) {
        // Flipping the global AI mode is admin-only (POST is _require_admin-gated);
        // a non-admin viewer gets 403. Leave the displayed mode unchanged and mark
        // it read-only rather than blanking the badge (which would disable it for good).
        if (r.status === 403) setDenied(true);
        return;
      }
      const d = await r.json();
      if (d?.mode === 'live' || d?.mode === 'cached') { setMode(d.mode); setEntries(d.entries ?? 0); }
    } catch {
      /* network hiccup — keep the current mode, don't blank the badge */
    } finally {
      setBusy(false);
    }
  }

  const isCached = mode === 'cached';
  const Icon = isCached ? Archive : Zap;
  const colour = theme === 'dark'
    ? (isCached
        ? 'bg-amber-500/15 text-amber-300 hover:bg-amber-500/25 border-amber-400/30'
        : 'bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25 border-emerald-400/30')
    : (isCached
        ? 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100'
        : 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100');

  return (
    <button
      type="button"
      onClick={flip}
      disabled={!mode || busy}
      title={denied
        ? `AI mode is ${mode} (switching is admin-only for this shared demo).`
        : isCached
        ? `Serving cached AI responses (${entries} stored). Click to switch to live.`
        : 'Calling real serving endpoints. Click to switch to cached / consistent / fast.'}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border text-[11px] font-medium transition-colors disabled:opacity-50 ${colour}`}
    >
      <Icon className="w-3.5 h-3.5 shrink-0" />
      <span>AI: {mode ?? '…'}</span>
      {isCached && entries > 0 && (
        <span className="text-[10px] opacity-70">{entries}</span>
      )}
    </button>
  );
}
