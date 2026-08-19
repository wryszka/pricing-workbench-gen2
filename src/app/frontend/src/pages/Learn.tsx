import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  BookOpen, Database, Table2, Code, Rocket, Calculator, Shield, Sparkles,
  GitBranch, RefreshCw, Lock, ArrowRight,
} from 'lucide-react';

// Self-contained "Learn" page — the accelerator's guide. Sticky TOC on the
// left, scrollable panels on the right. No external deps (matches the other
// workbench demos' Learn pattern).

const PANELS = [
  { id: 'what',       label: 'What this is',          icon: BookOpen },
  { id: 'spine',      label: 'The pricing spine',     icon: GitBranch },
  { id: 'ratebook',   label: 'Rolling rate book',     icon: RefreshCw },
  { id: 'agents',     label: 'Real agents',           icon: Sparkles },
  { id: 'governance', label: 'Governance & bias',     icon: Shield },
  { id: 'platform',   label: 'Platform & deploy',     icon: Rocket },
];

export default function Learn() {
  const [active, setActive] = useState('what');

  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => { if (e.isIntersecting) setActive(e.target.id); });
      },
      { rootMargin: '-20% 0px -70% 0px', threshold: 0 },
    );
    PANELS.forEach((p) => {
      const el = document.getElementById(p.id);
      if (el) obs.observe(el);
    });
    return () => obs.disconnect();
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-blue-600" /> Learn — Pricing Workbench
        </h1>
        <p className="text-gray-500 mt-1 text-sm max-w-3xl">
          How the accelerator is put together: the end-to-end pricing flow, the
          rolling rate book, the governed AI agents, and the Databricks platform
          it runs on. Every page links back here.
        </p>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Sticky TOC */}
        <nav className="col-span-12 md:col-span-3">
          <div className="sticky top-6 space-y-1">
            {PANELS.map(({ id, label, icon: Icon }) => (
              <a key={id} href={`#${id}`}
                 className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                   active === id ? 'bg-blue-50 text-blue-700 font-medium'
                                 : 'text-gray-600 hover:bg-gray-50'}`}>
                <Icon className="w-4 h-4 shrink-0" /> {label}
              </a>
            ))}
          </div>
        </nav>

        {/* Panels */}
        <div className="col-span-12 md:col-span-9 space-y-10">
          <Panel id="what" title="What this is" icon={BookOpen}>
            <p>
              The Pricing Workbench is an <strong>example accelerator</strong> — not a
              Databricks product — showing an end-to-end commercial pricing operation
              built entirely on the Databricks platform: Unity Catalog, Delta Lake,
              MLflow, Mosaic AI (Agent Framework + Model Serving + Foundation Model API),
              Databricks Apps and AI/BI Genie. The carrier "Bricksurance SE" is
              synthetic; the UK postcode enrichment is real public data. The models,
              agents, governance packs, audit log and scoring flow are real.
            </p>
            <p>
              Everything is <strong>serverless and scale-to-zero</strong>: endpoints and
              warehouses cost nothing when idle and warm on first use.
            </p>
          </Panel>

          <Panel id="spine" title="The pricing spine" icon={GitBranch}>
            <p>Six stages, left to right — each is a tab in the left nav:</p>
            <Ribbon items={[
              { icon: Database,   label: 'Ingestion',      to: '/datasets',       sub: 'approved sources + HITL gate' },
              { icon: Table2,     label: 'Modelling Mart', to: '/pricing-table',  sub: 'governed feature table' },
              { icon: Code,       label: 'Model Dev',      to: '/development',    sub: 'train · compare · promote' },
              { icon: Rocket,     label: 'Deployment',     to: '/deployment',     sub: 'UC champions · rollback' },
              { icon: Calculator, label: 'Pricing Engine', to: '/pricing-engine', sub: 'the live rate book' },
              { icon: Shield,     label: 'Governance',     to: '/governance',     sub: 'defend to regulators' },
            ]} />
            <p>
              Vendor data passes an <strong>actuary approval gate</strong> with data-quality
              checks before it reaches the mart; every promotion produces a governance
              pack; every action is written to an immutable audit log.
            </p>
          </Panel>

          <Panel id="ratebook" title="Rolling rate book" icon={RefreshCw}>
            <p>
              The <strong>Pricing Engine</strong> ships monthly <strong>releases</strong> — a
              rate book bundles one version of each of the four model families
              (frequency, severity, demand, fraud) plus a rating-engine config, an
              effective date, and a committee narrative. Exactly one release is
              <em> live</em> at a time.
            </p>
            <p>
              The series is <strong>rolling</strong>: the live release is always the current
              month and history steps back month-by-month. <em>Reset demo</em> (left
              pane) re-anchors everything to today — it re-seeds the release series and
              shifts every dated table forward so the data is never stale, without
              retraining. The control tower on the Home page shows the live release at a
              glance.
            </p>
          </Panel>

          <Panel id="agents" title="Real agents" icon={Sparkles}>
            <p>
              The agents use the <strong>Mosaic AI Agent Framework</strong> (MLflow
              ChatAgent), registered to Unity Catalog with a <code>@Production</code> alias
              and deployed to scale-to-zero Model Serving endpoints. They reason with
              Claude via the Databricks Foundation Model API and query governed tables
              through declared tools.
            </p>
            <p>
              Auth is <strong>Model Serving automatic authentication passthrough</strong>:
              the warehouse, tables and volumes an agent reads are declared as model
              resources, so serving provisions and auto-refreshes short-lived
              credentials. There are <strong>no personal access tokens</strong> — nothing
              expires. <Link to="/pricing-ai" className="text-blue-600 hover:underline">Pricing
              AI</Link> is one chat surface that auto-routes across every agent.
            </p>
          </Panel>

          <Panel id="governance" title="Governance & bias" icon={Shield}>
            <p>
              Every promoted model gets a <strong>governance pack</strong> — a multi-section
              PDF (model card, metrics, feature importance, fairness, lineage,
              approvals) generated from the real run. The <Link to="/governance"
              className="text-blue-600 hover:underline">Governance</Link> tab browses packs
              by model, by date, or by policy, with an LLM assistant grounded in the
              pack contents.
            </p>
            <p>
              A <strong>bias monitor</strong> scans champions across director gender and a
              postcode-derived demographic proxy before each release is approved. The
              audit log is immutable and append-only.
            </p>
          </Panel>

          <Panel id="platform" title="Platform & deploy" icon={Rocket}>
            <p>
              One platform, integrated: sources → bronze/silver (DLT + expectations +
              HITL) → Modelling Mart (Delta + optional online store + Genie) → models
              (MLflow + UC registry) → champions (UC aliases + Model Serving) → the
              rating engine. Cross-cutting: UC lineage, audit log, governance packs,
              bias monitor.
            </p>
            <p>
              Deploy is three commands — bootstrap the app, deploy the bundle, run one
              populate job — everything serverless. The full source is public; fork it
              and point it at your own workspace.
            </p>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function Panel({ id, title, icon: Icon, children }: {
  id: string; title: string; icon: any; children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-6">
      <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2 mb-3">
        <Icon className="w-5 h-5 text-blue-600" /> {title}
      </h2>
      <div className="prose prose-sm max-w-none text-gray-700 space-y-3 [&_p]:leading-relaxed">
        {children}
      </div>
    </section>
  );
}

function Ribbon({ items }: { items: { icon: any; label: string; to: string; sub: string }[] }) {
  return (
    <div className="flex items-stretch gap-2 overflow-x-auto py-2 my-2">
      {items.map((s, i) => (
        <div key={s.to} className="flex items-stretch gap-2">
          <Link to={s.to}
                className="w-36 shrink-0 rounded-lg border border-gray-200 bg-gray-50 hover:bg-blue-50 hover:border-blue-300 p-3 transition no-underline">
            <s.icon className="w-4 h-4 text-gray-600 mb-1.5" />
            <div className="text-sm font-semibold text-gray-900 leading-tight">{s.label}</div>
            <div className="text-[11px] text-gray-500 mt-0.5 leading-snug">{s.sub}</div>
          </Link>
          {i < items.length - 1 && (
            <div className="flex items-center shrink-0"><ArrowRight className="w-4 h-4 text-gray-400" /></div>
          )}
        </div>
      ))}
    </div>
  );
}
