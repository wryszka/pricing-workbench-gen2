import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  BookOpen, Database, Table2, Code, Rocket, Calculator, Shield, Sparkles,
  GitBranch, RefreshCw, Lock, ArrowRight, Target,
} from 'lucide-react';
import { Page, PageHeader, OnThisPage } from '../components/ui';

// Self-contained "Learn" page — the accelerator's guide. Sticky TOC on the
// left, scrollable panels on the right. No external deps (matches the other
// workbench demos' Learn pattern).

const PANELS = [
  { id: 'what',       label: 'What this is',          icon: BookOpen },
  { id: 'spine',      label: 'The pricing spine',     icon: GitBranch },
  { id: 'ratebook',   label: 'Rolling rate book',     icon: RefreshCw },
  { id: 'optimiser',  label: 'Price optimisation',    icon: Target },
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
    <Page>
      <PageHeader
        eyebrow="Bricksurance SE · Pricing Workbench"
        title="Learn — Pricing Workbench"
        subtitle="How the accelerator is put together: the end-to-end pricing flow, the rolling rate book, the governed AI agents, and the Databricks platform it runs on."
        icon={BookOpen}
      />
      <OnThisPage>
        Use the sticky TOC on the left to jump to any section. Seven topics: what this demo is, the six-stage pricing spine, the rolling rate book mechanics, price optimisation (the ten ideas + a glossary for anyone without a pricing background), how the real AI agents work, governance and bias monitoring, and how to deploy on your own workspace.
      </OnThisPage>

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

          <Panel id="optimiser" title="Price optimisation — the ten ideas" icon={Target}>
            <p>
              A primer for anyone running <Link to="/optimisation" className="text-blue-600 hover:underline">Price
              Optimisation</Link> without a pricing background. It is not a pricing course — it is the
              defensible perimeter: the ideas that are load-bearing for the demo, and one sentence for
              everything past them. You do <em>not</em> need GLM/GBM internals, Monte-Carlo mechanics,
              solver algorithms, reserving, capital or IFRS 17 — none of it is load-bearing here.
            </p>
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              <strong>The perimeter rule</strong> — for any modelling question you can't answer, say it
              without apology and move on: <em>"That's a modelling choice your actuaries would own — the
              platform runs whichever choice they make."</em>
            </div>
            <ol className="list-decimal pl-5 space-y-1.5 text-sm">
              <li><strong>Technical price</strong> — the break-even cost of a policy (expected claims + expenses). Every price is expressed relative to this floor: it answers "what does this risk cost us?"; optimisation answers "what should we charge, given that?"</li>
              <li><strong>The demand curve (elasticity)</strong> — per segment, as price rises what fraction still buys? Steep = price-sensitive shoppers; flat = loyal. This is the one extra model optimisation adds; the risk models and rating an insurer already has.</li>
              <li><strong>Why lost quotes matter</strong> — you can't learn price sensitivity from customers who said yes. The quotes that walked away carry the signal — a data-platform story before it's a modelling one.</li>
              <li><strong>The endogeneity trap</strong> — riskier customers are quoted more <em>and still buy</em>, so a naive model reads demand as price-insensitive and leaves money everywhere. Fix: model demand on price <em>relative to technical</em>, so the risk-driven part cancels. The "wrong-model" panel shows the trap.</li>
              <li><strong>The corridor</strong> — a hard ±15% bound around technical price that no optimised price may leave, enforced <em>at solve time</em> (the solver can't produce a violating price) and re-checked at deploy. Not a guideline someone checks afterwards — that's the governance story.</li>
              <li><strong>Why the machine raises loyal segments (the grandma logic)</strong> — if a segment's curve is flat on the upside, a profit maximiser will always raise it. Not a bug — the objective doing its job. Whether it <em>should</em> is a policy question (the twist below).</li>
              <li><strong>GIPP</strong> — UK FCA rule (2022): a renewal price may not exceed the equivalent new-business price. It exists because insurers "price-walked" loyal customers year after year. Checked at solve time, shown as the Conduct column.</li>
              <li><strong>Legal floor vs fair-value standard</strong> — GIPP is the law (the floor); Consumer Duty asks the broader question: is this customer getting fair value at all? A price can pass GIPP and still fail fair value. The machine checks the floor; only a human sets the standard. The amber pill flags the second question.</li>
              <li><strong>What "Re-solve" does</strong> — it searches thousands of candidate factor sets against the fitted demand curves and keeps the best one satisfying every constraint. It does <em>not</em> retrain a model and isn't AI magic — a governed search job (which is why it's fast, and why N is a text box).</li>
              <li><strong>Ensemble disagreement = model risk</strong> (heavy mode) — one demand model is one opinion. Heavy mode refits demand as eight specifications and re-solves under each: where they agree the move is robust; where they split it's a model artifact — hold it or widen the corridor.</li>
            </ol>
            <p className="text-sm">
              <strong>Three answers that cover most hard questions.</strong> (1) <em>"How does this reach my
              rating engine?"</em> → the factor table is a governed Delta table; publish it like any rate
              revision — this replaces the analysis/decision layer, not your execution path. (2) <em>"Is any
              of this real?"</em> → concede first: synthetic book, production-shaped patterns; your data and
              your actuaries' models drop into the same slots. (3) Anything on modelling choices → the
              perimeter rule above.
            </p>
            <details className="text-sm">
              <summary className="cursor-pointer font-medium text-gray-800">Glossary — the terms you'll see on the page</summary>
              <Glossary items={[
                ['Technical price', 'Break-even cost of a policy (expected claims + expenses). All optimised prices are a factor on this baseline.'],
                ['Street / final premium', 'What the customer is charged: technical price × the optimised factor, bounded by the corridor.'],
                ['Price factor', 'The multiplier on a segment’s technical price (1.05 = +5%). The factor table is the solver’s output and what exports to a rating engine.'],
                ['Segment', 'A group of similar customers priced together (age band × vehicle group). The demo optimises per segment.'],
                ['Conversion', 'The share of quoted customers who buy — the quantity the demand model predicts and the y-axis of every elasticity curve.'],
                ['Demand model', 'Predicts conversion as a function of price relative to technical. The one extra model optimisation requires.'],
                ['Elasticity', 'How strongly conversion reacts to a price change. Elastic = shoppers; inelastic = loyal.'],
                ['Monotonic constraint', 'A rule forcing conversion to only fall as price rises — the model can’t say "raise price, sell more".'],
                ['Endogeneity', 'The trap where risk drives both price and purchase, making demand look price-insensitive. Removed by modelling on price relative to technical.'],
                ['Lost quote', 'A quote that didn’t convert — carries most of the price signal; without it there is no demand model.'],
                ['Objective', 'What the solver maximises: expected profit, volume, or a blend. Set by a human; the machine never picks its own goal.'],
                ['Expected profit', 'Conversion-weighted margin of street price over technical cost, before fixed overheads.'],
                ['Constraint', 'A rule the solver must respect (corridor, segment caps, forbidden signals, GIPP, volume floor). Lives in a versioned YAML file — the pricing policy as an artifact.'],
                ['Corridor', 'The hard ±15% band around technical price. Enforced at solve time and re-checked at deploy.'],
                ['Forbidden signal', 'A variable the model may never use (protected characteristics + proxies). Excluded by construction; proxy-tested after solve.'],
                ['Solver / Re-solve', 'The governed job that searches candidate factor sets for the best one satisfying all constraints. Search, not training.'],
                ['Efficient frontier', 'The curve of best available trade-offs between volume and profit. Below it = leaving money or customers on the table.'],
                ['Waterfall', 'The chart decomposing where the profit uplift comes from, segment by segment.'],
                ['GIPP', 'UK FCA rule: a renewal price may not exceed the equivalent new-business price. Checked at solve time; shown in the Conduct column.'],
                ['Consumer Duty / fair value', 'UK conduct standard asking whether the customer gets fair value overall — a higher bar than GIPP. The amber pill flags segments for a human call.'],
                ['Price walking', 'Raising loyal customers’ renewal prices year after year because they don’t shop around. The practice GIPP banned.'],
                ['Decision record', 'The immutable row written when prices deploy: who, when, why, which model version, which constraint version.'],
                ['Provenance block', 'The chain under an explained price: model version → constraint version → approver → decision record.'],
                ['Deploy gate', 'A Unity Catalog stored procedure that re-checks the corridor and writes the audit record. Permission to run it is a per-person DB grant, not app logic.'],
                ['Heavy mode', 'The optional second gear: refit demand as an ensemble and score the whole book across hundreds of plans and demand draws.'],
                ['Disagreement map', 'Per-segment spread of the ensemble’s prices. Green = models agree (deploy with confidence); amber = they split (hold / widen the corridor).'],
                ['Monte-Carlo demand draws', 'Simulating "who actually converts" many times per plan, since each customer converts with a probability — an outcome distribution, not one number.'],
                ['P5–P95 band', 'The realistic worst-to-best range of a plan’s outcome. A tight band above today’s line often beats a higher but wider mean.'],
                ['Scored evaluation', 'One policy × one plan × one demand draw — cheap arithmetic on fitted curves, not a model inference.'],
              ]} />
            </details>
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
    </Page>
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

function Glossary({ items }: { items: [string, string][] }) {
  return (
    <dl className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
      {items.map(([term, def]) => (
        <div key={term} className="min-w-0">
          <dt className="font-semibold text-gray-900 text-[13px]">{term}</dt>
          <dd className="text-[12px] text-gray-600 leading-snug">{def}</dd>
        </div>
      ))}
    </dl>
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
