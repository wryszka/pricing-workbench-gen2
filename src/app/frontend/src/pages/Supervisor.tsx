import { useEffect, useRef, useState } from 'react';
import {
  Bot, Send, Loader2, Sparkles, ChevronDown, ChevronUp, Wrench,
  Database, Shield, Scale, Workflow, FlaskConical, ExternalLink,
} from 'lucide-react';
import { api } from '../lib/api';
import {
  Page, PageHeader, OnThisPage, Card, CardTitle, Section, UnderTheHood,
  Grid,
} from '../components/ui';

/**
 * Pricing AI — single chat surface that fronts every agent in the
 * workbench. Auto-routes by classifying the question, or the user picks
 * a sub-agent explicitly. Below the chat, a diagram shows what the
 * supervisor fronts so the architecture is legible at a glance.
 */

type SubAgent = {
  id: string;
  label: string;
  subtitle: string;
  endpoint: string;
  persona: string | null;
  tools: string[];
  good_for: string[];
  kind: 'agent' | 'genie';
  needs_run_id: boolean;
};

type Turn = {
  role: 'user' | 'assistant';
  text: string;
  trace?: any[];
  usage?: any;
  model?: string;
  sub_agent?: string;
  sub_agent_label?: string;
  classifier_used?: boolean;
  kind?: 'agent' | 'genie' | 'multi';
  space_id?: string;
  embed_url?: string;
  open_url?: string;
  question?: string;
  error?: string;
};

const ICON_BY_ID: Record<string, any> = {
  governance:  Shield,
  bias:        Scale,
  explain:     Workflow,
  factory:     FlaskConical,
  genie_mart:  Database,
  genie_quote: Database,
};

export default function Supervisor() {
  const [agents, setAgents] = useState<SubAgent[]>([]);
  const [chosen, setChosen] = useState<string>('auto');
  const [turns, setTurns]   = useState<Turn[]>([]);
  const [input, setInput]   = useState('');
  const [busy, setBusy]     = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getSupervisorAgents().then((d: any) => setAgents(d.agents || [])).catch(() => {});
  }, []);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [turns, busy]);

  const send = async (q: string) => {
    const text = q.trim();
    if (!text || busy) return;
    setInput('');
    setBusy(true);
    setTurns(t => [...t, { role: 'user', text }]);
    try {
      const r: any = await api.askSupervisor({ question: text, sub_agent: chosen });
      setTurns(t => [...t, {
        role:             'assistant',
        text:             r.answer || (r.error ? `[error: ${r.error}]` : '(empty response)'),
        trace:            r.trace,
        usage:            r.usage,
        model:            r.model,
        sub_agent:        r.sub_agent,
        sub_agent_label:  r.sub_agent_label,
        classifier_used:  r.classifier_used,
        kind:             r.kind,
        space_id:         r.space_id,
        embed_url:        r.embed_url,
        open_url:         r.open_url,
        question:         text,
        error:            r.error,
      }]);
    } catch (e: any) {
      setTurns(t => [...t, { role: 'assistant', text: `[request failed: ${e.message || e}]` }]);
    } finally {
      setBusy(false);
    }
  };

  const allSuggestions = agents.flatMap(a => a.good_for.slice(0, 1).map(q => ({ id: a.id, label: a.label, q })));

  return (
    <Page>
      <PageHeader
        eyebrow="Bricksurance SE · Pricing AI"
        title="Multi-agent pricing copilot"
        subtitle="Ask anything—pack defence, bias, ingestion impact, factory plan, mart query. Single address, six specialised brains."
        icon={Sparkles}
      />

      <OnThisPage>
        Chat surface auto-routes to the right agent (or pick one manually) · every dispatch is audit-logged
        · Mosaic AI Framework agents + Genie spaces together.
      </OnThisPage>

      <SupervisorChat
        agents={agents} chosen={chosen} setChosen={setChosen}
        turns={turns} input={input} setInput={setInput} busy={busy}
        onSend={send} allSuggestions={allSuggestions}
        scrollRef={scrollRef}
      />

      <ArchitectureDiagram agents={agents} />

      <UnderTheHood
        title="Pricing AI — Multi-Agent Routing"
        lines={[
          { component: '/api/supervisor', detail: 'Chat endpoint that classifies questions and routes to sub-agents; audit-logged' },
          { component: 'classifier', detail: '10-token FM API call for routing — sub-second latency' },
          { component: 'sub-agents', detail: 'Six independent Mosaic AI Agent Framework endpoints (governance, bias, explain, factory) + Genie spaces (mart, quote)' },
          { component: 'audit_log', detail: 'Every dispatch recorded: question, chosen agent, classifier flag, model, tokens, tool trace' },
          { component: 'Mosaic AI Agent Framework', detail: 'Unified agent interface with tool orchestration and grounding' },
        ]}
      />
    </Page>
  );
}

// ---------------------------------------------------------------------------
// Chat surface
// ---------------------------------------------------------------------------

function SupervisorChat({
  agents, chosen, setChosen, turns, input, setInput, busy, onSend, allSuggestions, scrollRef,
}: {
  agents: SubAgent[];
  chosen: string;
  setChosen: (v: string) => void;
  turns: Turn[];
  input: string;
  setInput: (v: string) => void;
  busy: boolean;
  onSend: (q: string) => void;
  allSuggestions: { id: string; label: string; q: string }[];
  scrollRef: React.RefObject<HTMLDivElement | null>;
}) {
  return (
    <Card>
      <div className="flex items-center gap-2 mb-3">
        <Bot className="w-4 h-4 text-brand" />
        <CardTitle>Pricing AI chat</CardTitle>
      </div>
      <p className="text-[12.5px] text-mut mb-4">Auto-classifies via a fast Foundation-Model call, or pin a sub-agent with the pills below.</p>

      <div className="mb-4">
        <div className="text-[11px] font-bold uppercase tracking-[0.05em] text-mut mb-2">Route to</div>
        <div className="flex flex-wrap gap-1.5">
          <RoutePill active={chosen === 'auto'} label="Auto"
                     onClick={() => setChosen('auto')} icon={<Sparkles className="w-3 h-3"/>}/>
          {agents.map(a => {
            const Icon = ICON_BY_ID[a.id] || Bot;
            return (
              <RoutePill key={a.id} active={chosen === a.id} label={a.label}
                         onClick={() => setChosen(a.id)} icon={<Icon className="w-3 h-3"/>}/>
            );
          })}
        </div>
      </div>

      {turns.length === 0 && allSuggestions.length > 0 && (
        <div className="mb-4 pb-4 border-b border-line">
          <div className="text-[11px] font-bold uppercase tracking-[0.05em] text-mut mb-2">
            Try one of these
          </div>
          <div className="flex flex-wrap gap-2">
            {allSuggestions.map(s => (
              <button key={s.id + s.q} onClick={() => onSend(s.q)}
                      disabled={busy}
                      className="text-[12.5px] text-left px-3 py-1.5 rounded-full border border-brand/20 bg-white hover:bg-brand/5 text-ink">
                <span className="text-[10px] uppercase tracking-wider font-bold text-brand mr-1.5">
                  {s.label}
                </span>
                {s.q}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="border border-line rounded-lg overflow-hidden flex flex-col" style={{ height: '480px' }}>
        {turns.length > 0 && (
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3 bg-slate-50">
            {turns.map((t, i) => <TurnView key={i} turn={t} />)}
            {busy && (
              <div className="flex items-center gap-2 text-[12.5px] text-brand">
                <Loader2 className="w-4 h-4 animate-spin" />
                Pricing AI is dispatching…
              </div>
            )}
          </div>
        )}

        <div className="border-t border-line bg-white p-2 flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend(input); } }}
            disabled={busy}
            placeholder="Ask anything — pack defence, bias, ingestion impact, factory plan, mart query…"
            className="flex-1 border border-line rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 disabled:bg-slate-50"
          />
          <button onClick={() => onSend(input)}
                  disabled={busy || !input.trim()}
                  className="inline-flex items-center justify-center w-10 h-10 rounded-lg text-white bg-brand hover:bg-blue-700 disabled:opacity-40">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </Card>
  );
}

function RoutePill({ active, label, onClick, icon }:
  { active: boolean; label: string; onClick: () => void; icon: React.ReactNode }) {
  return (
    <button onClick={onClick}
            className={`text-[12.5px] px-2.5 py-1 rounded-full border inline-flex items-center gap-1.5 transition font-medium ${
              active
                ? 'bg-brand text-white border-brand'
                : 'bg-white text-ink border-line hover:border-brand/40 hover:bg-brand/5'
            }`}>
      {icon}{label}
    </button>
  );
}

function TurnView({ turn }: { turn: Turn }) {
  const [showTrace, setShowTrace] = useState(false);
  if (turn.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[78%] bg-brand text-white text-sm px-3.5 py-2 rounded-xl rounded-br-sm whitespace-pre-wrap">
          {turn.text}
        </div>
      </div>
    );
  }
  return (
    <div className="flex justify-start">
      <div className="max-w-[88%] bg-white border border-line text-sm text-ink px-3.5 py-2.5 rounded-xl rounded-bl-sm">
        {turn.sub_agent_label && (
          <div className="flex items-center gap-1.5 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-brand">
            <Sparkles className="w-3 h-3" />
            {turn.sub_agent_label}
            {turn.classifier_used && (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-brand/10 text-brand border border-brand/30 normal-case">
                auto-routed
              </span>
            )}
          </div>
        )}
        <div className="whitespace-pre-wrap leading-relaxed">{turn.text}</div>
        {turn.kind === 'genie' && turn.embed_url && (
          <div className="mt-3">
            <div className="flex items-center justify-end mb-2">
              <a href={turn.open_url || turn.embed_url} target="_blank" rel="noopener noreferrer"
                 className="inline-flex items-center gap-1 text-[11px] text-brand hover:text-blue-700">
                Open in Databricks <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <iframe
              src={turn.embed_url}
              title={turn.sub_agent_label || 'Genie chat'}
              className="w-full rounded-lg border border-line bg-white"
              style={{ height: 600 }}
            />
          </div>
        )}
        {(turn.trace?.length || turn.usage?.total_tokens || turn.model) && (
          <div className="mt-2 pt-2 border-t border-line">
            <button onClick={() => setShowTrace(s => !s)}
                    className="text-[11px] text-mut hover:text-ink inline-flex items-center gap-1">
              <Wrench className="w-3 h-3" />
              {turn.trace?.length ? `${turn.trace.length} tool call${turn.trace.length === 1 ? '' : 's'}` : 'agent details'}
              {showTrace ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
            {showTrace && (
              <div className="mt-2 text-[11px] text-mut space-y-1">
                {turn.model && <div><b>Model:</b> {turn.model}</div>}
                {turn.usage?.total_tokens != null && (
                  <div><b>Tokens:</b> {turn.usage.total_tokens.toLocaleString()} total</div>
                )}
                {turn.trace?.length ? (
                  <ol className="list-decimal pl-4 mt-1 space-y-0.5">
                    {turn.trace.map((tc: any, i: number) => (
                      <li key={i}>
                        <code>{tc.tool || tc.name || 'tool'}</code>
                        {tc.arguments && (
                          <span className="text-mut"> · {JSON.stringify(tc.arguments).slice(0, 120)}</span>
                        )}
                      </li>
                    ))}
                  </ol>
                ) : null}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Architecture diagram
// ---------------------------------------------------------------------------

function ArchitectureDiagram({ agents }: { agents: SubAgent[] }) {
  // Hard-coded layout — six tiles in a 3-2-1 hierarchy with the supervisor on top.
  const order: { id: string; tone: string }[] = [
    { id: 'governance',  tone: 'amber'   },
    { id: 'bias',        tone: 'indigo'  },
    { id: 'explain',     tone: 'blue'    },
    { id: 'factory',     tone: 'rose'    },
    { id: 'genie_mart',  tone: 'emerald' },
    { id: 'genie_quote', tone: 'cyan'    },
  ];
  const visible = order
    .map(o => ({ ...o, agent: agents.find(a => a.id === o.id) }))
    .filter(x => x.agent);

  const tone: Record<string, { bg: string; border: string; head: string; chip: string }> = {
    amber:   { bg: 'bg-amber-50',   border: 'border-amber-300',   head: 'text-amber-900',   chip: 'bg-amber-100 text-amber-900' },
    indigo:  { bg: 'bg-indigo-50',  border: 'border-indigo-300',  head: 'text-indigo-900',  chip: 'bg-indigo-100 text-indigo-900' },
    blue:    { bg: 'bg-blue-50',    border: 'border-blue-300',    head: 'text-blue-900',    chip: 'bg-blue-100 text-blue-900' },
    rose:    { bg: 'bg-rose-50',    border: 'border-rose-300',    head: 'text-rose-900',    chip: 'bg-rose-100 text-rose-900' },
    emerald: { bg: 'bg-emerald-50', border: 'border-emerald-300', head: 'text-emerald-900', chip: 'bg-emerald-100 text-emerald-900' },
    cyan:    { bg: 'bg-cyan-50',    border: 'border-cyan-300',    head: 'text-cyan-900',    chip: 'bg-cyan-100 text-cyan-900' },
  };

  return (
    <Card className="mt-5">
      <CardTitle>What Pricing AI fronts</CardTitle>
      <p className="text-[12.5px] text-mut mb-4">Six specialised brains, one address. Each is a Databricks Mosaic AI agent endpoint or AI/BI Genie space — independently deployable, independently auditable.</p>

      {/* Top — supervisor box */}
      <div className="flex justify-center mb-3">
        <div className="rounded-xl border border-brand bg-brand/5 px-5 py-3 text-center min-w-[280px]">
          <div className="text-[10px] uppercase tracking-wider font-bold text-brand">Pricing AI</div>
          <div className="text-base font-bold text-ink">Pricing AI Supervisor</div>
          <div className="text-[12.5px] text-mut mt-0.5">classifies → dispatches → audit-logs</div>
        </div>
      </div>

      {/* Connector lines */}
      <div className="flex justify-center mb-3">
        <div className="w-px h-6 bg-line" />
      </div>

      {/* Mid horizontal bus */}
      <div className="border-t border-dashed border-line mx-12 mb-4" />

      {/* Sub-agent grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        {visible.map(({ id, tone: t, agent }) => {
          if (!agent) return null;
          const c = tone[t];
          const Icon = ICON_BY_ID[id] || Bot;
          return (
            <div key={id} className={`rounded-xl border ${c.border} ${c.bg} p-3`}>
              <div className="flex items-center gap-2 mb-1">
                <Icon className={`w-4 h-4 ${c.head}`} />
                <h4 className={`text-sm font-semibold ${c.head}`}>{agent.label}</h4>
                <span className="ml-auto text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded bg-white border border-line text-ink">
                  {agent.kind}
                </span>
              </div>
              <p className="text-[12.5px] text-ink mb-2 leading-snug">{agent.subtitle}</p>
              <div className="text-[10px] uppercase tracking-wider font-semibold text-mut mb-1">Tools</div>
              <div className="flex flex-wrap gap-1 mb-2">
                {agent.tools.slice(0, 4).map(tool => (
                  <span key={tool} className={`text-[10px] px-1.5 py-0.5 rounded ${c.chip} font-mono`}>
                    {tool}
                  </span>
                ))}
              </div>
              <div className="text-[10px] text-ink leading-tight">
                <span className="font-semibold">Endpoint:</span>{' '}
                <code className="font-mono text-[9px]">{agent.endpoint}</code>
                {agent.persona && <> · <span className="font-semibold">persona:</span> <code className="font-mono text-[9px]">{agent.persona}</code></>}
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom note */}
      <div className="text-[11px] text-mut italic pt-3 border-t border-line">
        Agents are independently deployed Mosaic AI Agent Framework endpoints; Genie spaces are
        AI/BI Genie rooms governed by Unity Catalog. Auto-routing uses a 10-token Foundation-Model
        classifier — sub-second, low cost. Every dispatch lands in <code className="bg-slate-100 px-1 rounded">audit_log</code> with the
        chosen route, classifier flag, model used, token usage, and tool trace.
      </div>
    </Card>
  );
}
