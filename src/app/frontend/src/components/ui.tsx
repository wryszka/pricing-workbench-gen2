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
import { ChevronRight, Sparkles, Send, Loader2 } from 'lucide-react';
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
  children: ReactNode; className?: string; onClick?: () => void; drill?: boolean;
}) {
  return (
    <div onClick={onClick}
      className={`bg-white border border-line rounded-xl p-4 ${drill ? 'cursor-pointer transition hover:-translate-y-0.5 hover:shadow-[0_8px_22px_rgba(15,23,42,.1)]' : ''} ${className}`}>
      {children}
    </div>
  );
}
export function CardTitle({ children }: { children: ReactNode }) {
  return <h3 className="text-[13px] text-mut font-semibold uppercase tracking-[0.04em] mb-2">{children}</h3>;
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
  plain: 'bg-white border-line text-ink',
};
export function Metric({ label, value, sub, tone = 'plain' }: {
  label: string; value: ReactNode; sub?: string; tone?: 'blue' | 'green' | 'amber' | 'violet' | 'plain';
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
export function Pill({ children, tone = 'slate' }: {
  children: ReactNode; tone?: 'red' | 'amber' | 'green' | 'blue' | 'slate' | 'live';
}) {
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold ${pillTone[tone]}`}>
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
export function Btn({ children, tone = 'primary', onClick, disabled, className = '' }: {
  children: ReactNode; tone?: 'primary' | 'ghost' | 'warn' | 'bad';
  onClick?: () => void; disabled?: boolean; className?: string;
}) {
  return (
    <button onClick={onClick} disabled={disabled}
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
export function AskBox({ title, subtitle, examples = [], onAsk, placeholder = 'Ask a question…', seedQuestion }: {
  title: string; subtitle?: string; examples?: string[];
  onAsk: (q: string) => Promise<string>; placeholder?: string;
  seedQuestion?: string;   // auto-run on mount to populate the initial "lead" read
}) {
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);

  const ask = async (question?: string) => {
    const query = (question ?? q).trim();
    if (!query || busy) return;
    setBusy(true); setAnswer(null); setQ(query);
    try { setAnswer(await onAsk(query)); }
    catch (e: any) { setAnswer(`Error: ${e?.message || e}`); }
    finally { setBusy(false); }
  };

  // Lead-with-agent: auto-run the seed question once so the description appears
  // before the user types anything (without echoing the seed into the input).
  useEffect(() => {
    if (!seedQuestion) return;
    let alive = true;
    setBusy(true); setAnswer(null);
    onAsk(seedQuestion)
      .then((a) => { if (alive) setAnswer(a); })
      .catch((e: any) => { if (alive) setAnswer(`Error: ${e?.message || e}`); })
      .finally(() => { if (alive) setBusy(false); });
    return () => { alive = false; };
  }, [seedQuestion]);   // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="bg-[linear-gradient(135deg,#312e81_0%,#6d28d9_55%,#7c3aed_100%)] rounded-2xl px-6 py-5 text-white shadow-[0_10px_30px_rgba(109,40,217,.28)]">
      <h2 className="text-[19px] font-bold flex items-center gap-2"><Sparkles className="w-4.5 h-4.5" /> {title}</h2>
      {subtitle && <p className="text-[13px] text-[#ddd6fe] mt-1 mb-3 leading-relaxed max-w-3xl">{subtitle}</p>}
      {examples.length > 0 && (
        <div className="flex gap-2 flex-wrap mb-3">
          {examples.map((ex, i) => (
            <button key={i} onClick={() => ask(ex)}
              className="bg-white/10 border border-white/20 text-[#ede9fe] px-3 py-1.5 rounded-full text-[12px] hover:bg-white/25 transition">{ex}</button>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') ask(); }}
          placeholder={placeholder}
          className="flex-1 px-3.5 py-3 rounded-lg border-0 text-[13.5px] text-ink focus:outline-none focus:ring-2 focus:ring-white/50" />
        <button onClick={() => ask()} disabled={busy || !q.trim()}
          className="px-5 py-3 rounded-lg bg-white text-[#6d28d9] font-bold text-[13.5px] disabled:opacity-60 inline-flex items-center gap-1.5">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Ask
        </button>
      </div>
      {(busy || answer) && (
        <div className="mt-3.5 bg-white/95 rounded-xl px-4 py-3.5 text-ink text-sm leading-relaxed whitespace-pre-line">
          {busy ? <span className="inline-flex items-center gap-1.5 text-mut"><Loader2 className="w-3.5 h-3.5 animate-spin" /> thinking…</span> : answer}
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
export function AgentLead({ persona, seed, title, subtitle, examples = [], family, context }: {
  persona: string; seed: string; title: string; subtitle?: string;
  examples?: string[]; family?: string; context?: any;
}) {
  const onAsk = async (q: string) => {
    const r = await api.agentLead({ persona, question: q, family, context });
    return r?.answer || (r?.error ? `Agent unavailable — ${r.error}` : 'No answer returned.');
  };
  return (
    <AskBox title={title} subtitle={subtitle} examples={examples}
      onAsk={onAsk} seedQuestion={seed} placeholder="Ask a follow-up…" />
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
        <span className="text-[11px] uppercase tracking-[0.08em] font-bold text-mut">⌘ Under the hood</span>
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
export function Grid({ cols = 3, children, className = '' }: { cols?: 2 | 3 | 4; children: ReactNode; className?: string }) {
  const c = { 2: 'md:grid-cols-2', 3: 'md:grid-cols-3', 4: 'md:grid-cols-4' }[cols];
  return <div className={`grid grid-cols-1 ${c} gap-4 ${className}`}>{children}</div>;
}
