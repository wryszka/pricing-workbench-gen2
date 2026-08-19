import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { Database, FlaskConical, Shield, Code, Rocket, Home as HomeIcon, Table2, Package, Sparkles, Calculator, Zap, Archive, BookOpen, Target, GraduationCap, RotateCcw, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from './lib/api';
import Home from './pages/Home';
import Learn from './pages/Learn';
import DatasetList from './pages/DatasetList';
import DatasetDetail from './pages/DatasetDetail';
import FeatureStore from './pages/FeatureStore';
import ModelDevelopment from './pages/ModelDevelopment';
import ModelFactory from './pages/ModelFactory';
import ModelDeployment from './pages/ModelDeployment';
import Governance from './pages/Governance';
import QuoteReview from './pages/QuoteReview';
import Addons from './pages/Addons';
import AgenticDistribution from './pages/AgenticDistribution';
import BrokerChat from './pages/BrokerChat';
import NewDataImpact from './pages/NewDataImpact';
import RatingEngineIntegration from './pages/RatingEngineIntegration';
import Supervisor from './pages/Supervisor';
import PricingEngine from './pages/PricingEngine';
import PriceOptimisation from './pages/PriceOptimisation';
import QuoteSystem from './pages/QuoteSystem';
import BlackBox from './pages/BlackBox';
import QuoteTester from './pages/QuoteTester';

const NAV_ITEMS = [
  { to: '/',              label: 'Home',              icon: HomeIcon,     match: (p: string) => p === '/' },
  { to: '/datasets',      label: 'Data Ingestion',         icon: Database,     match: (p: string) => p.startsWith('/dataset') },
  { to: '/pricing-table', label: 'Modelling Mart',    icon: Table2,       match: (p: string) => p.startsWith('/pricing-table') },
  { to: '/development',   label: 'Model Development', icon: Code,         match: (p: string) => p.startsWith('/development') },
  { to: '/deployment',    label: 'Model Deployment',  icon: Rocket,       match: (p: string) => p.startsWith('/deployment') },
  { to: '/pricing-engine',label: 'Pricing Engine',    icon: Calculator,   match: (p: string) => p.startsWith('/pricing-engine') },
  { to: '/optimisation',  label: 'Price Optimisation',icon: Target,       match: (p: string) => p.startsWith('/optimisation') },
  { to: '/governance',    label: 'Model Governance',  icon: Shield,       match: (p: string) => p.startsWith('/governance') },
  { to: '/pricing-ai',    label: 'Pricing AI',        icon: Sparkles,     match: (p: string) => p.startsWith('/pricing-ai') || p.startsWith('/supervisor') || p.startsWith('/regulatory-ai') },
  { to: '/models',        label: 'Model Factory',     icon: FlaskConical, match: (p: string) => p.startsWith('/models') },
  { to: '/add-ons',       label: 'Add-ons',           icon: Package,      match: (p: string) => p.startsWith('/add-ons') || p.startsWith('/quote-review') },
];

function Sidebar() {
  const { pathname } = useLocation();

  return (
    <aside className="w-[264px] shrink-0 min-h-screen flex flex-col text-[#cbd5e1] border-r border-white/[0.06] bg-[linear-gradient(180deg,#1e293b_0%,#172033_100%)]">
      {/* Brand */}
      <Link to="/" className="flex items-center gap-3 px-4 py-4 border-b border-white/[0.08] hover:bg-white/[0.03] transition">
        <div className="w-[34px] h-[34px] rounded-[9px] flex items-center justify-center shrink-0 bg-[linear-gradient(135deg,#2563eb,#60a5fa)] shadow-[0_2px_10px_rgba(37,99,235,.4)]">
          <Database className="w-[19px] h-[19px] text-white" />
        </div>
        <div className="leading-tight">
          <div className="text-[14.5px] font-bold text-white tracking-tight">Bricksurance SE</div>
          <div className="text-[10.5px] text-[#94a3b8]">Pricing Workbench</div>
        </div>
      </Link>

      {/* Nav items */}
      <nav className="flex-1 px-2.5 py-2 overflow-y-auto">
        {NAV_ITEMS.map(({ to, label, icon: Icon, match }) => {
          const on = match(pathname);
          return (
            <Link key={to} to={to}
              className={`flex items-center gap-3 px-3 py-2 rounded-[9px] text-[13.5px] my-0.5 transition ${
                on
                  ? 'text-white font-semibold bg-[linear-gradient(135deg,#2563eb,#3b82f6)] shadow-[0_2px_8px_rgba(37,99,235,.35)]'
                  : 'text-[#cbd5e1] hover:bg-white/[0.06] hover:text-white'}`}>
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Learn tile */}
      <div className="px-3 pb-1">
        <Link to="/learn"
          className={`flex items-center gap-2 px-2.5 py-2 rounded-[9px] text-[12.5px] font-semibold border transition ${
            pathname.startsWith('/learn')
              ? 'bg-emerald-500/25 border-emerald-400/50 text-emerald-200'
              : 'bg-emerald-500/[0.12] border-emerald-400/40 text-emerald-300 hover:bg-emerald-500/20'}`}>
          <GraduationCap className="w-3.5 h-3.5 shrink-0" /> Learn · Pricing 101
        </Link>
      </div>

      <DemoDocCard />
      <AiModeBadge />

      {/* Foot — reset demo + disclaimer */}
      <div className="p-3 border-t border-white/[0.08]">
        <SidebarReset />
        <div className="text-[10.5px] text-[#64748b] mt-2.5 leading-relaxed">
          <b className="text-[#94a3b8]">About this demo</b> — Bricksurance SE is a synthetic insurer; not a Databricks product. Every panel calls real Unity Catalog functions, models, agents and Genie.
        </div>
      </div>
    </aside>
  );
}

// Demo run-through doc — same sidebar card the other workbench demos carry.
function DemoDocCard() {
  return (
    <div className="px-3 py-2 border-t border-white/10">
      <a
        href="https://docs.google.com/document/d/1VHVMrbwo1D2Gfl2NKnKJzosBlS-hltcFZ9guvBejUkM/edit"
        target="_blank"
        rel="noreferrer"
        title="Opens the demo run-through (Google Doc — Databricks internal)"
        className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md border text-[11px] font-medium transition-colors bg-blue-500/15 text-blue-300 hover:bg-blue-500/25 border-blue-400/30"
      >
        <BookOpen className="w-3.5 h-3.5 shrink-0" />
        <span className="flex-1 text-left">Demo doc — run-through</span>
        <span className="text-[10px] opacity-70">↗</span>
      </a>
    </div>
  );
}

// Reset demo — moved into the left pane. Fires demo_reset, polls to completion.
function SidebarReset() {
  const [confirming, setConfirming] = useState(false);
  const [running, setRunning]       = useState(false);
  const [result, setResult]         = useState<any>(null);
  const [status, setStatus]         = useState<any>(null);
  const [error, setError]           = useState<string | null>(null);

  const fire = async () => {
    setRunning(true); setError(null); setResult(null); setStatus(null);
    try { setResult(await api.resetDemo()); }
    catch (e: any) { setError(e.message || String(e)); }
    finally { setRunning(false); setConfirming(false); }
  };

  useEffect(() => {
    if (!result?.run_id || status?.life_cycle === 'TERMINATED') return;
    const t = setInterval(async () => {
      try {
        const r = await fetch(`/api/admin/reset-demo/status?run_id=${result.run_id}`);
        if (!r.ok) return;
        const s = await r.json();
        setStatus(s);
        if (s.life_cycle === 'TERMINATED') clearInterval(t);
      } catch { /* swallow */ }
    }, 6000);
    return () => clearInterval(t);
  }, [result, status?.life_cycle]);

  if (result) {
    const finished = status?.life_cycle === 'TERMINATED';
    const success  = status?.result === 'SUCCESS';
    const Icon     = finished ? (success ? CheckCircle2 : AlertCircle) : Loader2;
    const colour   = !finished ? 'text-blue-300' : success ? 'text-emerald-300' : 'text-red-300';
    return (
      <div className={`flex items-center gap-2 px-3 py-2 text-[11px] ${colour}`}>
        <Icon className={`w-3.5 h-3.5 shrink-0 ${!finished ? 'animate-spin' : ''}`} />
        <span className="flex-1">Reset {finished ? (success ? 'complete' : 'failed') : 'running…'}</span>
        {finished && (
          <button onClick={() => { setResult(null); setStatus(null); }}
                  className="opacity-70 hover:opacity-100">×</button>
        )}
      </div>
    );
  }
  if (confirming) {
    return (
      <div className="px-2 py-1.5 space-y-1.5">
        <p className="text-[10px] text-gray-400 leading-snug px-1">
          Re-anchors the demo to today (rolling releases + fresh dates), reverts
          champions, clears transient results.
        </p>
        <div className="flex gap-1.5">
          <button onClick={fire} disabled={running}
            className="flex-1 inline-flex items-center justify-center gap-1 px-2 py-1.5 rounded-md bg-amber-500/90 text-white text-[11px] font-medium hover:bg-amber-500 disabled:opacity-50">
            {running ? <Loader2 className="w-3 h-3 animate-spin" /> : <RotateCcw className="w-3 h-3" />} Confirm
          </button>
          <button onClick={() => setConfirming(false)}
            className="px-2 py-1.5 rounded-md text-[11px] text-gray-400 hover:text-white hover:bg-white/5">cancel</button>
        </div>
      </div>
    );
  }
  return (
    <button onClick={() => setConfirming(true)}
      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-colors">
      <RotateCcw className="w-4 h-4 shrink-0" /> Reset demo
      {error && <span className="ml-auto text-[10px] text-red-400">failed</span>}
    </button>
  );
}

function AiModeBadge() {
  const [mode, setMode] = useState<'live' | 'cached' | null>(null);
  const [busy, setBusy] = useState(false);
  const [entries, setEntries] = useState<number>(0);

  useEffect(() => {
    fetch('/api/admin/ai-mode')
      .then((r) => r.json())
      .then((d) => { setMode(d.mode); setEntries(d.entries ?? 0); })
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
      const d = await r.json();
      setMode(d.mode);
      setEntries(d.entries ?? 0);
    } finally {
      setBusy(false);
    }
  }

  const isCached = mode === 'cached';
  const Icon = isCached ? Archive : Zap;
  const colour = isCached ? 'bg-amber-500/15 text-amber-300 hover:bg-amber-500/25 border-amber-400/30'
                          : 'bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25 border-emerald-400/30';
  return (
    <div className="px-3 py-2 border-t border-white/10">
      <button
        type="button"
        onClick={flip}
        disabled={!mode || busy}
        title={isCached
          ? `Serving cached AI responses (${entries} stored). Click to switch to live.`
          : 'Calling real serving endpoints. Click to switch to cached / consistent / fast.'}
        className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md border text-[11px] font-medium transition-colors disabled:opacity-50 ${colour}`}
      >
        <Icon className="w-3.5 h-3.5 shrink-0" />
        <span className="flex-1 text-left">AI: {mode ?? '…'}</span>
        {isCached && entries > 0 && (
          <span className="text-[10px] opacity-70">{entries}</span>
        )}
      </button>
    </div>
  );
}

// Standalone, chrome-less routes (no workbench sidebar) — these read as
// separate external products for the live demo.
function StandaloneRoutes() {
  return (
    <Routes>
      <Route path="/quote" element={<QuoteSystem />} />
      <Route path="/quote-chat" element={<BrokerChat />} />
      <Route path="/blackbox" element={<BlackBox />} />
      <Route path="/quotetester" element={<QuoteTester />} />
    </Routes>
  );
}

const STANDALONE = ['/quote', '/quote-chat', '/blackbox', '/quotetester'];

export default function App() {
  const path = window.location.pathname;
  if (STANDALONE.includes(path)) {
    return (
      <BrowserRouter>
        <StandaloneRoutes />
      </BrowserRouter>
    );
  }
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-page flex">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/learn" element={<Learn />} />
            <Route path="/datasets" element={<DatasetList />} />
            <Route path="/dataset/:datasetId" element={<DatasetDetail />} />
            <Route path="/pricing-table" element={<FeatureStore />} />
            <Route path="/development" element={<ModelDevelopment />} />
            <Route path="/models" element={<ModelFactory />} />
            <Route path="/deployment" element={<ModelDeployment />} />
            <Route path="/pricing-engine" element={<PricingEngine />} />
            <Route path="/optimisation" element={<PriceOptimisation />} />
            <Route path="/governance" element={<Governance />} />
            <Route path="/pricing-ai"   element={<Supervisor />} />
            <Route path="/supervisor"   element={<Supervisor />} />  {/* legacy URL */}
            <Route path="/regulatory-ai" element={<Supervisor />} />  {/* legacy URL */}
            <Route path="/add-ons" element={<Addons />} />
            <Route path="/add-ons/quote-review" element={<QuoteReview />} />
            <Route path="/add-ons/new-data-impact" element={<NewDataImpact />} />
            <Route path="/add-ons/rating-engine" element={<RatingEngineIntegration />} />
            <Route path="/add-ons/agentic-distribution" element={<AgenticDistribution />} />
            {/* Legacy redirect */}
            <Route path="/quote-review" element={<QuoteReview />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
