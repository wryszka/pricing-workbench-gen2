import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Target, ChevronDown, ChevronUp, ShieldCheck, Info, SlidersHorizontal,
         Cpu, Database, Layers, GitBranch, LineChart, Route, ExternalLink,
         Play, Loader2, CheckCircle2, Bot, Activity, Zap } from 'lucide-react';
import { api } from '../lib/api';

// Price Optimisation — an INTERACTIVE optimizer, not a dashboard. The demand +
// profit curves per segment are precomputed and governed by the optimiser job;
// the optimisation DECISION (objective + constraints) runs live in the browser
// against those governed curves, with a portfolio roll-up and efficient frontier.
// This is what a pricing practitioner needs to believe the platform replaces a
// closed optimiser: turn the levers, watch the whole book move.

type Seg = {
  segment: string; n_quotes: number; elasticity: number; market_ref: number;
  cost_line: number; current_multiplier: number; current_conversion: number;
  current_profit_per_quote: number; optimal_multiplier: number;
  optimal_conversion: number; optimal_profit_per_quote: number;
  profit_uplift_per_quote: number; profit_uplift_pct: number; binding_constraint: string;
};
type CurvePt = {
  segment: string; price_multiplier: number; expected_conversion: number;
  price: number; expected_profit_per_quote: number; within_rate_cap: boolean;
};
type Levers = { alpha: number; rateCap: number; marginFloor: number };

const fmtPct = (v: number) => `${(v * 100).toFixed(0)}%`;
const fmtMult = (v: number) => `${v.toFixed(2)}×`;
const gbpM = (v: number) => `£${(v / 1e6).toFixed(2)}m`;
const num = (v: any) => (v === null || v === undefined || v === '' ? v : Number(v));

// Pick the objective-optimal curve point for a segment under the current levers.
function choose(seg: Seg, pts: CurvePt[], L: Levers): CurvePt | null {
  const within = pts.filter((p) => Math.abs(p.price_multiplier - seg.current_multiplier) <= L.rateCap + 1e-9);
  const ok = within.filter((p) => p.price > 0 && (p.price - seg.cost_line) / p.price >= L.marginFloor - 1e-9);
  const pool = ok.length ? ok : within;
  if (!pool.length) return null;
  const maxProfit = Math.max(...pts.map((p) => p.expected_profit_per_quote), 1e-9);
  let best = pool[0], bestVal = -Infinity;
  for (const p of pool) {
    const val = L.alpha * (p.expected_profit_per_quote / maxProfit) + (1 - L.alpha) * p.expected_conversion;
    if (val > bestVal) { bestVal = val; best = p; }
  }
  return best;
}
function nearestCurrent(seg: Seg, pts: CurvePt[]): CurvePt | null {
  if (!pts.length) return null;
  return pts.reduce((a, b) =>
    Math.abs(b.price_multiplier - seg.current_multiplier) < Math.abs(a.price_multiplier - seg.current_multiplier) ? b : a);
}

export default function PriceOptimisation() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [seg, setSeg] = useState<string>('');
  const [showHelp, setShowHelp] = useState(false);
  const [tab, setTab] = useState<'optimise' | 'how' | 'story'>('optimise');
  const [objective, setObjective] = useState<'profit' | 'volume' | 'blend'>('profit');
  const [alpha, setAlpha] = useState(0.6);
  const [rateCap, setRateCap] = useState(0.15);
  const [marginFloor, setMarginFloor] = useState(0.05);
  const [assets, setAssets] = useState<any>(null);

  const load = () => {
    const numify = (r: any) => {
      const o = { ...r };
      for (const k of ['n_quotes', 'elasticity', 'market_ref', 'cost_line', 'current_multiplier',
        'current_conversion', 'current_profit_per_quote', 'optimal_multiplier', 'optimal_conversion',
        'optimal_profit_per_quote', 'profit_uplift_per_quote', 'profit_uplift_pct',
        'price_multiplier', 'expected_conversion', 'price', 'expected_profit_per_quote']) {
        if (k in o) o[k] = num(o[k]);
      }
      return o;
    };
    return api.optimisationSummary()
      .then((d) => {
        if (d?.segments) d.segments = d.segments.map(numify);
        if (d?.curve) d.curve = d.curve.map(numify);
        setData(d);
        if (d?.segments?.length) setSeg((prev) => prev || d.segments[0].segment);
      })
      .catch((e) => setErr(String(e)));
  };

  useEffect(() => {
    load();
    api.optAssets().then(setAssets).catch(() => {});
  }, []);

  const segments: Seg[] = data?.segments || [];
  const curve: CurvePt[] = data?.curve || [];
  const cfg = data?.config;
  const effAlpha = objective === 'profit' ? 1 : objective === 'volume' ? 0 : alpha;
  const levers: Levers = { alpha: effAlpha, rateCap, marginFloor };

  const ptsBySeg = useMemo(() => {
    const m: Record<string, CurvePt[]> = {};
    for (const c of curve) (m[c.segment] ||= []).push(c);
    for (const k in m) m[k].sort((a, b) => a.price_multiplier - b.price_multiplier);
    return m;
  }, [curve]);

  // Live per-segment choice + portfolio roll-up under the current levers.
  const roll = useMemo(() => {
    let curProfit = 0, optProfit = 0, curPol = 0, optPol = 0, gwp = 0, wRate = 0, pool = 0;
    const perSeg: Record<string, { chosen: CurvePt | null; cur: CurvePt | null }> = {};
    for (const s of segments) {
      const pts = ptsBySeg[s.segment] || [];
      const chosen = choose(s, pts, levers);
      const cur = nearestCurrent(s, pts);
      perSeg[s.segment] = { chosen, cur };
      const n = s.n_quotes || 0; pool += n;
      if (cur) { curProfit += cur.expected_profit_per_quote * n; curPol += cur.expected_conversion * n; }
      if (chosen) {
        optProfit += chosen.expected_profit_per_quote * n;
        optPol += chosen.expected_conversion * n;
        gwp += chosen.price * chosen.expected_conversion * n;
        wRate += chosen.price_multiplier * n;
      }
    }
    return { curProfit, optProfit, curPol, optPol, gwp, avgRate: pool ? wRate / pool : 1, perSeg };
  }, [segments, ptsBySeg, levers]);

  // Efficient frontier: sweep the profit/volume blend, plot (policies, profit).
  const frontier = useMemo(() => {
    const out: { alpha: number; pol: number; profit: number }[] = [];
    for (let a = 0; a <= 1.0001; a += 0.1) {
      let profit = 0, pol = 0;
      for (const s of segments) {
        const c = choose(s, ptsBySeg[s.segment] || [], { alpha: a, rateCap, marginFloor });
        if (c) { profit += c.expected_profit_per_quote * s.n_quotes; pol += c.expected_conversion * s.n_quotes; }
      }
      out.push({ alpha: a, pol, profit });
    }
    return out;
  }, [segments, ptsBySeg, rateCap, marginFloor]);

  if (err) return <div className="p-8 text-red-600">Failed to load: {err}</div>;
  if (!data) return <div className="p-8 text-gray-500">Loading…</div>;
  if (!data.available)
    return (
      <div className="max-w-3xl mx-auto p-8">
        <h1 className="text-2xl font-bold mb-3 flex items-center gap-2">
          <Target className="w-6 h-6 text-teal-600" /> Price Optimisation
        </h1>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-900">{data.message}</div>
      </div>
    );

  const active = segments.find((s) => s.segment === seg);
  const segChoice = roll.perSeg[seg];
  const profitDelta = roll.optProfit - roll.curProfit;
  const polDelta = roll.optPol - roll.curPol;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="flex items-center gap-2 mb-1">
        <Target className="w-6 h-6 text-teal-600" />
        <h1 className="text-2xl font-bold">Price Optimisation</h1>
        <span className="ml-2 text-[11px] uppercase tracking-wide bg-teal-100 text-teal-800 px-2 py-0.5 rounded">interactive</span>
      </div>
      <p className="text-gray-600 text-sm mb-4 max-w-3xl">
        Set the objective and the guardrails; the optimiser re-solves the profit-optimal
        price per segment against the governed demand curves and rolls the impact up
        across the book — live. Your models, transparent, constraint-aware.
      </p>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-4">
        <TabBtn active={tab === 'optimise'} onClick={() => setTab('optimise')} icon={SlidersHorizontal} label="Optimiser" />
        <TabBtn active={tab === 'story'} onClick={() => setTab('story')} icon={Route} label="Walkthrough" />
        <TabBtn active={tab === 'how'} onClick={() => setTab('how')} icon={Cpu} label="How it works" />
      </div>

      {tab === 'how' && (
        <HowItWorks cfg={cfg} assets={assets} segCount={segments.length}
          totalQuotes={segments.reduce((a, s) => a + (s.n_quotes || 0), 0)} />
      )}

      {tab === 'story' && (
        <Walkthrough assets={assets} segments={segments} roll={roll}
          levers={{ rateCap, marginFloor }}
          setObjective={setObjective} setRateCap={setRateCap} setSeg={setSeg}
          reload={load} goOptimiser={() => setTab('optimise')} />
      )}

      {tab === 'optimise' && (<>
      <button onClick={() => setShowHelp(!showHelp)} className="text-xs text-teal-700 flex items-center gap-1 mb-3">
        <Info className="w-3.5 h-3.5" /> What am I looking at?
        {showHelp ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>
      {showHelp && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-700 mb-4 space-y-2 max-w-3xl">
          <p><b>Objective</b> — maximise profit, volume, or a blend. <b>Guardrails</b> — a
            rate-change cap around today's book price and a margin floor, enforced as
            first-class constraints. Move any lever and every number below re-solves.</p>
          <p><b>Portfolio impact</b> — the whole-book roll-up of the chosen strategy vs the
            current book. <b>Efficient frontier</b> — the profit↔volume trade-off; each dot is
            a blend weight, the ring is where you are now.</p>
          <p className="text-gray-500">Bricksurance SE is fictional; data synthetic; the cost
            line + method are illustrative, not a certified rate.</p>
        </div>
      )}

      {/* Levers */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
        <div className="flex items-center gap-2 mb-3 text-sm font-semibold text-gray-700">
          <SlidersHorizontal className="w-4 h-4 text-teal-600" /> Objective &amp; guardrails
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-start">
          <div>
            <div className="text-[11px] uppercase tracking-wide text-gray-400 mb-1">Objective</div>
            <div className="flex gap-1">
              {(['profit', 'volume', 'blend'] as const).map((o) => (
                <button key={o} onClick={() => setObjective(o)}
                  className={`px-2.5 py-1 rounded text-xs border capitalize ${objective === o
                    ? 'bg-teal-600 text-white border-teal-600' : 'bg-white text-gray-600 border-gray-300 hover:border-teal-400'}`}>{o}</button>
              ))}
            </div>
            {objective === 'blend' && (
              <div className="mt-2">
                <input type="range" min={0} max={1} step={0.05} value={alpha}
                  onChange={(e) => setAlpha(Number(e.target.value))} className="w-full accent-teal-600" />
                <div className="text-[11px] text-gray-500">{fmtPct(alpha)} profit / {fmtPct(1 - alpha)} volume</div>
              </div>
            )}
          </div>
          <Slider label="Rate-change cap" value={rateCap} min={0} max={0.3} step={0.01}
            onChange={setRateCap} display={`±${fmtPct(rateCap)}`} />
          <Slider label="Margin floor" value={marginFloor} min={0} max={0.25} step={0.01}
            onChange={setMarginFloor} display={fmtPct(marginFloor)} />
          <div className="text-[11px] text-gray-500 self-end">
            Every lever re-solves the optimiser client-side against the governed curves —
            no black box.
          </div>
        </div>
      </div>

      {/* Portfolio roll-up */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Kpi label="Expected profit (book)" value={gbpM(roll.optProfit)}
          delta={`${profitDelta >= 0 ? '+' : ''}${gbpM(profitDelta)} vs current`} up={profitDelta >= 0} big />
        <Kpi label="Policies bound (book)" value={Math.round(roll.optPol).toLocaleString()}
          delta={`${polDelta >= 0 ? '+' : ''}${Math.round(polDelta).toLocaleString()} vs current`} up={polDelta >= 0} big />
        <Kpi label="Avg rate change" value={`${roll.avgRate >= 1 ? '+' : ''}${fmtPct(roll.avgRate - 1)}`}
          delta="vs today's book" />
        <Kpi label="Gross written premium" value={gbpM(roll.gwp)} delta="at the optimised prices" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Efficient frontier */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Efficient frontier — volume vs profit</h2>
          <FrontierChart frontier={frontier} alpha={effAlpha} />
        </div>
        {/* Per-segment curve */}
        <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-gray-700">Demand &amp; profit — {seg}</h2>
            <div className="flex gap-1 flex-wrap">
              {segments.map((s) => (
                <button key={s.segment} onClick={() => setSeg(s.segment)}
                  className={`px-2 py-0.5 rounded text-[11px] border ${seg === s.segment
                    ? 'bg-teal-600 text-white border-teal-600' : 'bg-white text-gray-600 border-gray-300'}`}>
                  {s.segment.replace(/^\d+ /, '')}</button>
              ))}
            </div>
          </div>
          {active && segChoice && (
            <CurveChart pts={ptsBySeg[seg] || []} current={segChoice.cur} chosen={segChoice.chosen}
              currentMult={active.current_multiplier} rateCap={rateCap} />
          )}
        </div>
      </div>

      {/* Per-segment table (live under levers) */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden mb-6">
        <div className="px-4 py-2 border-b border-gray-200 text-sm font-semibold text-gray-700">
          Per-segment recommendation — under the current levers
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>{['Segment', 'Quotes', 'Elasticity', 'Current', 'Optimal', 'Conversion →', 'Profit/quote →'].map((h) => (
                <th key={h} className="text-left px-3 py-2 font-medium whitespace-nowrap">{h}</th>))}</tr>
            </thead>
            <tbody>
              {segments.map((s) => {
                const ch = roll.perSeg[s.segment]?.chosen; const cu = roll.perSeg[s.segment]?.cur;
                return (
                  <tr key={s.segment} className={`border-t border-gray-100 ${seg === s.segment ? 'bg-teal-50/40' : ''}`}>
                    <td className="px-3 py-2 font-medium">{s.segment}</td>
                    <td className="px-3 py-2 text-gray-500">{s.n_quotes.toLocaleString()}</td>
                    <td className="px-3 py-2">{s.elasticity.toFixed(1)}</td>
                    <td className="px-3 py-2">{fmtMult(s.current_multiplier)}</td>
                    <td className="px-3 py-2 font-semibold text-teal-700">{ch ? fmtMult(ch.price_multiplier) : '—'}</td>
                    <td className="px-3 py-2 text-gray-600">{cu ? fmtPct(cu.expected_conversion) : '—'} → {ch ? fmtPct(ch.expected_conversion) : '—'}</td>
                    <td className="px-3 py-2 text-gray-600">£{cu ? Math.round(cu.expected_profit_per_quote).toLocaleString() : '—'} → £{ch ? Math.round(ch.expected_profit_per_quote).toLocaleString() : '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Governed scenario */}
      {cfg && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-teal-600" /> This scenario, governed
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <Cfg label="Objective" value={objective === 'blend' ? `blend ${fmtPct(alpha)} profit` : objective} />
            <Cfg label="Rate-change cap" value={`±${fmtPct(rateCap)}`} />
            <Cfg label="Margin floor" value={fmtPct(marginFloor)} />
            <Cfg label="Demand source" value={cfg.demand_source} />
          </div>
          <p className="text-xs text-gray-500 mt-3">
            In production this lever set is saved as a versioned, audited config (like the
            baseline in <code>optimisation_config</code>) — the "why" of every price is a
            diffable governed artefact a closed optimiser can't evidence. A fair-value /
            no-price-walking rule plugs in as another constraint, and the accepted strategy
            becomes a rate release.
          </p>
        </div>
      )}
      </>)}
    </div>
  );
}

function TabBtn({ active, onClick, icon: Icon, label }: {
  active: boolean; onClick: () => void; icon: any; label: string;
}) {
  return (
    <button onClick={onClick}
      className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px flex items-center gap-1.5 ${active
        ? 'border-teal-600 text-teal-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
      <Icon className="w-4 h-4" /> {label}
    </button>
  );
}

function InfoCard({ icon: Icon, title, children }: { icon: any; title: string; children: ReactNode }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-2 text-sm font-semibold text-gray-700">
        <Icon className="w-4 h-4 text-teal-600" /> {title}
      </div>
      <ul className="list-disc pl-4 space-y-1.5 text-[13px] text-gray-600 leading-snug">{children}</ul>
    </div>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-gray-400">{label}</div>
      <div className="text-gray-700 break-words">{value}</div>
    </div>
  );
}

// A deep-link chip → opens a real platform asset in a new tab. Renders nothing
// until the assets resolve, so it never shows a dead link.
function LinkChip({ href, icon: Icon, label }: { href?: string | null; icon: any; label: string }) {
  if (!href) return null;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded border border-teal-200 bg-teal-50 text-teal-700 hover:bg-teal-100">
      <Icon className="w-3 h-3" /> {label} <ExternalLink className="w-2.5 h-2.5 opacity-60" />
    </a>
  );
}

// "How it works" — the behind-the-scenes tab. Answers "what's actually running?"
// for a demo audience: the data, the model/method, and the Databricks tech. Kept
// faithful to src/04_models/production/price_optimiser.py. Cards deep-link to the
// real assets via /api/optimisation/assets.
function HowItWorks({ cfg, assets, segCount, totalQuotes }:
  { cfg: any; assets: any; segCount: number; totalQuotes: number }) {
  const t = assets?.tables || {};
  const steps = [
    { icon: Database, t: 'Quote stream', d: 'Every priced commercial quote — offered price, market reference, convert / no-convert.' },
    { icon: LineChart, t: 'Demand curve', d: 'Per segment: a logistic fit of conversion vs price-to-market. Slope = elasticity.' },
    { icon: Cpu, t: 'Cost + solve', d: 'Lay a cost line, grid-search the price that maximises d(p)·(p−c) under the guardrails.' },
    { icon: ShieldCheck, t: 'Governed tables', d: 'Curve, summary and a versioned config row land in Unity Catalog.' },
    { icon: SlidersHorizontal, t: 'This app', d: 'The Optimiser tab re-solves the decision live in your browser over those curves.' },
  ];
  return (
    <div className="space-y-5">
      <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 text-sm text-teal-900">
        <b>No black box.</b> Every number on the Optimiser tab is readable code over three governed
        Delta tables. Below is the whole pipeline — here running over {segCount} segments and{' '}
        {totalQuotes.toLocaleString()} priced quotes.
      </div>

      {/* Pipeline strip */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">The pipeline, end to end</h2>
        <div className="flex flex-col md:flex-row md:items-stretch gap-2">
          {steps.map((s, i) => (
            <div key={s.t} className="flex-1 flex items-center gap-2">
              <div className="flex-1 rounded-lg border border-gray-200 bg-gray-50 p-3 h-full">
                <s.icon className="w-4 h-4 text-teal-600 mb-1" />
                <div className="text-xs font-semibold text-gray-800">{s.t}</div>
                <div className="text-[11px] text-gray-500 leading-snug mt-0.5">{s.d}</div>
              </div>
              {i < steps.length - 1 && <div className="hidden md:block text-gray-300 shrink-0">→</div>}
            </div>
          ))}
        </div>
      </div>

      {/* Data / Model / Tech */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <InfoCard icon={Database} title="Data">
          <li><b>Source:</b> <code>quotes</code> — priced commercial quotes with the offered premium,
            the market reference, and whether the quote converted (bound). That convert / no-convert
            outcome is the elasticity signal.</li>
          <li><b>Filter:</b> price-to-market between 0.5× and 2.0×, non-outlier, premium present.</li>
          <li><b>Segments:</b> by account size — Micro (&lt;£10k), SME (£10–50k), Mid (£50–250k),
            Large (£250k+). Bigger accounts are more price-sensitive, so each gets a genuinely
            different curve and optimal move.</li>
          <li><b>Governed output (Unity Catalog):</b> <code>optimisation_curve</code>,{' '}
            <code>optimisation_summary</code>, <code>optimisation_config</code>.</li>
          <div className="flex flex-wrap gap-1.5 pt-1">
            <LinkChip href={t.quotes} icon={Database} label="quotes" />
            <LinkChip href={t.optimisation_summary} icon={Database} label="optimisation_summary" />
            <LinkChip href={t.optimisation_curve} icon={Database} label="optimisation_curve" />
          </div>
        </InfoCard>

        <InfoCard icon={Cpu} title="Model &amp; method">
          <li><b>Demand:</b> a per-segment <b>logistic regression</b> of conversion on price-to-market
            (scikit-learn). The slope is the segment's price elasticity — negative, so demand falls as
            price rises.</li>
          <li><b>Cost line:</b> illustrative expected claims = segment loss ratio × market premium
            (0.54 Micro → 0.80 Large). The floor optimisation cannot cross.</li>
          <li><b>Objective:</b> expected profit per quote <code>d(p)·(p−c)</code>, swept over a price
            grid (0.80×–1.30× market, 0.02 steps).</li>
          <li><b>Constraints:</b> a rate-change cap around today's book price (±15% default) and a
            margin floor (5%); the binding one is recorded per segment.</li>
          <li><b>MLflow</b> logs each run — params and total profit uplift.</li>
          <div className="flex flex-wrap gap-1.5 pt-1">
            <LinkChip href={assets?.notebook_url} icon={Cpu} label="open the notebook" />
            <LinkChip href={assets?.experiment_url} icon={LineChart} label="MLflow" />
          </div>
        </InfoCard>

        <InfoCard icon={Layers} title="Underlying tech">
          <li><b>Job:</b> <code>price_optimiser.py</code> — a serverless notebook (Spark → pandas /
            scikit-learn), part of Full Build.</li>
          <li><b>Storage &amp; governance:</b> Delta tables in <b>Unity Catalog</b>; a scale-to-zero
            SQL warehouse serves the app's reads.</li>
          <li><b>App:</b> Databricks Apps (FastAPI) exposes <code>/api/optimisation/summary</code>; this
            React page re-solves the objective + constraints <b>client-side</b>, so the levers move the
            whole book instantly.</li>
          <li><b>Why it matters:</b> the maths is deterministic and inspectable — the wedge against a
            closed, black-box optimiser.</li>
          <div className="flex flex-wrap gap-1.5 pt-1">
            <LinkChip href={assets?.job_url} icon={Play} label="the job" />
            <LinkChip href={assets?.agent_url} icon={Bot} label="the agent endpoint" />
          </div>
        </InfoCard>
      </div>

      {/* The decision, formalised */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">The decision, in one line</h2>
        <div className="bg-gray-900 text-gray-100 rounded-lg px-4 py-3 font-mono text-sm overflow-x-auto whitespace-nowrap">
          maximise <span className="text-teal-300">d(p)·(p − c)</span> over p&nbsp;&nbsp; s.t.&nbsp;&nbsp;
          |p − p₀| ≤ cap&nbsp;&nbsp; and&nbsp;&nbsp; (p − c)/p ≥ floor
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3 text-xs text-gray-600">
          <div><code>d(p)</code> — expected conversion at price p (fitted demand curve)</div>
          <div><code>p</code> — offered price = multiplier × market reference</div>
          <div><code>c</code> — cost line (expected claims)</div>
          <div><code>p₀</code> — today's book price for the segment</div>
        </div>
      </div>

      {/* Governed config row */}
      {cfg && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
            <GitBranch className="w-4 h-4 text-teal-600" /> Governed config — the audited "why"
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
            <KV label="Objective" value={cfg.objective || '—'} />
            <KV label="Demand source" value={cfg.demand_source || '—'} />
            <KV label="Cost source" value={cfg.cost_source || '—'} />
            <KV label="Rate-change cap" value={cfg.rate_change_cap != null ? `±${fmtPct(Number(cfg.rate_change_cap))}` : '—'} />
            <KV label="Margin floor" value={cfg.margin_floor != null ? fmtPct(Number(cfg.margin_floor)) : '—'} />
            <KV label="Version" value={cfg.version || '—'} />
          </div>
          <p className="text-xs text-gray-500 mt-3">
            This config row is versioned and audited in <code>optimisation_config</code> — the "why" of
            every recommended price is a diffable governed artefact a closed optimiser can't evidence.
          </p>
        </div>
      )}

      <p className="text-xs text-gray-500">
        Bricksurance SE is fictional; data synthetic. The cost line and method are illustrative, not a
        certified rate — the point is the mechanism and its governance, not the numbers.
      </p>
    </div>
  );
}

const btnCls = 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-60';
const btnGhost = 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border border-gray-300 text-gray-600 hover:border-teal-400';

function Step({ n, icon: Icon, title, children }: { n: number; icon: any; title: string; children: ReactNode }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 flex gap-3">
      <div className="shrink-0 w-8 h-8 rounded-full bg-teal-600 text-white flex items-center justify-center text-sm font-bold">{n}</div>
      <div className="flex-1 space-y-2 min-w-0">
        <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-800"><Icon className="w-4 h-4 text-teal-600" /> {title}</div>
        <div className="text-[13px] text-gray-600 leading-snug space-y-2">{children}</div>
      </div>
    </div>
  );
}

function MiniKpi({ label, value, tone }: { label: string; value: string; tone?: 'up' | 'down' }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-2">
      <div className="text-[10px] uppercase tracking-wide text-gray-400">{label}</div>
      <div className={`text-sm font-semibold ${tone === 'up' ? 'text-emerald-600' : tone === 'down' ? 'text-rose-600' : 'text-gray-800'}`}>{value}</div>
    </div>
  );
}

// Actual vs model-expected conversion by month; the gap is drift.
function MonitorChart({ months }: { months: any[] }) {
  const pts = months
    .map((m) => ({ month: String(m.month).slice(0, 7), a: Number(m.actual_conversion), e: Number(m.expected_conversion), d: Number(m.drift) }))
    .filter((p) => isFinite(p.a));
  if (!pts.length) return null;
  const W = 640, H = 180, padL = 36, padR = 12, padT = 12, padB = 26;
  const ys = pts.flatMap((p) => [p.a, p.e]).filter((v) => isFinite(v));
  const y0 = Math.min(...ys) * 0.9, y1 = Math.max(...ys) * 1.05;
  const x = (i: number) => padL + (pts.length <= 1 ? 0 : i / (pts.length - 1)) * (W - padL - padR);
  const y = (v: number) => padT + (1 - (v - y0) / (y1 - y0 || 1)) * (H - padT - padB);
  const line = (key: 'a' | 'e') => pts.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p[key]).toFixed(1)}`).join(' ');
  const last = pts[pts.length - 1];
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
        <line x1={padL} y1={H - padB} x2={W - padR} y2={H - padB} stroke="#e5e7eb" />
        <path d={line('e')} fill="none" stroke="#9ca3af" strokeWidth={2} strokeDasharray="4 3" />
        <path d={line('a')} fill="none" stroke="#0d9488" strokeWidth={2.5} />
        {pts.map((p, i) => <circle key={i} cx={x(i)} cy={y(p.a)} r={2} fill="#0d9488" />)}
        <text x={padL} y={H - 8} fontSize="9" fill="#9ca3af">{pts[0].month}</text>
        <text x={W - padR} y={H - 8} fontSize="9" fill="#9ca3af" textAnchor="end">{last.month}</text>
        <g fontSize="10">
          <rect x={W - 160} y={padT} width={10} height={3} fill="#0d9488" /><text x={W - 145} y={padT + 4} fill="#374151">actual</text>
          <rect x={W - 90} y={padT} width={10} height={3} fill="#9ca3af" /><text x={W - 75} y={padT + 4} fill="#374151">expected</text>
        </g>
      </svg>
      <div className="text-xs text-gray-600">
        Latest-month drift:{' '}
        <b className={last.d >= 0 ? 'text-emerald-600' : 'text-rose-600'}>{last.d >= 0 ? '+' : ''}{(last.d * 100).toFixed(1)}pp</b>{' '}
        (actual − model-expected conversion) — the signal to refit the curve.
      </div>
    </div>
  );
}

// The driven demo story: market event → change → run → result → monitor → govern → agent.
// Every beat touches a real asset (levers, the governed job, the monitor table, the agent).
function Walkthrough({ assets, segments, roll, levers, setObjective, setRateCap, setSeg, reload, goOptimiser }: {
  assets: any; segments: Seg[]; roll: any; levers: { rateCap: number; marginFloor: number };
  setObjective: (o: 'profit' | 'volume' | 'blend') => void; setRateCap: (v: number) => void;
  setSeg: (s: string) => void; reload: () => Promise<any>; goOptimiser: () => void;
}) {
  const t = assets?.tables || {};
  const smeSeg = segments.find((s) => /SME/i.test(s.segment))?.segment
    || segments.find((s) => /Mid/i.test(s.segment))?.segment || segments[0]?.segment || '';

  const [applied, setApplied] = useState(false);
  const [running, setRunning] = useState(false);
  const [runState, setRunState] = useState<any>(null);
  const [monitor, setMonitor] = useState<any[] | null>(null);
  const [monBusy, setMonBusy] = useState(false);
  const [agentQ, setAgentQ] = useState(
    'Under the defend-SME-volume strategy, who wins and who loses, what is the retention risk, and is any segment outside the corridor?');
  const [agentAns, setAgentAns] = useState<string | null>(null);
  const [agentBusy, setAgentBusy] = useState(false);

  const applyStrategy = () => { setSeg(smeSeg); setObjective('volume'); setRateCap(0.10); setApplied(true); };

  const triggerRun = async () => {
    setRunning(true); setRunState({ life_cycle_state: 'PENDING' });
    try {
      const r = await api.optRun({ rate_change_cap: levers.rateCap, margin_floor: levers.marginFloor });
      if (!r.ok) { setRunState({ error: r.error || 'run failed' }); setRunning(false); return; }
      const rid = r.run_id;
      setRunState({ run_id: rid, life_cycle_state: 'RUNNING' });
      for (let i = 0; i < 120; i++) {
        await new Promise((res) => setTimeout(res, 3000));
        const s = await api.optRunStatus(rid);
        setRunState(s);
        const done = !!s.result_state || ['TERMINATED', 'SKIPPED', 'INTERNAL_ERROR'].includes(s.life_cycle_state);
        if (done) { if (s.result_state === 'SUCCESS') await reload(); break; }
      }
    } catch (e: any) { setRunState({ error: String(e) }); }
    setRunning(false);
  };

  const loadMonitor = async () => {
    setMonBusy(true);
    try { const d = await api.optMonitoring(); setMonitor(d?.months || []); } catch { setMonitor([]); }
    setMonBusy(false);
  };

  const askAgent = async () => {
    setAgentBusy(true); setAgentAns(null);
    try { const r = await api.agentLead({ persona: 'rate_change', question: agentQ }); setAgentAns(r?.answer || r?.error || 'No answer.'); }
    catch (e: any) { setAgentAns('Agent unavailable: ' + String(e)); }
    setAgentBusy(false);
  };

  const profitDelta = roll ? roll.optProfit - roll.curProfit : 0;
  const polDelta = roll ? roll.optPol - roll.curPol : 0;
  const runOk = runState?.result_state === 'SUCCESS';

  return (
    <div className="space-y-3">
      <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 text-sm text-teal-900">
        <b>A day in the life.</b> A market event hits; you change the optimisation, run it on the real
        platform, read the result, monitor it, govern it — and an agent helps. Drive it top to bottom.
      </div>

      <Step n={1} icon={Zap} title="A market event">
        <p>A competitor has just cut <b>SME</b> rates ~8%. Conversion there will slip unless you respond —
          let's defend it without over-correcting the rest of the book.</p>
        <button onClick={() => setSeg(smeSeg)} className={btnGhost}>Focus on {smeSeg.replace(/^\d+ /, '') || 'SME'}</button>
      </Step>

      <Step n={2} icon={SlidersHorizontal} title="Change the optimisation to X">
        <p>Strategy — <b>defend SME volume</b>: steer the objective toward volume and tighten the
          rate-change cap to ±10% (hold the margin floor). One click sets the levers on the Optimiser tab.</p>
        <div className="flex flex-wrap gap-2 items-center">
          <button onClick={applyStrategy} className={btnCls}><Zap className="w-3.5 h-3.5" /> Apply strategy</button>
          <button onClick={goOptimiser} className={btnGhost}>See it on the Optimiser →</button>
        </div>
        {applied && roll && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mt-1">
            <MiniKpi label="Strategy" value="volume · ±10% cap" />
            <MiniKpi label="Book profit vs now" value={`${profitDelta >= 0 ? '+' : ''}${gbpM(profitDelta)}`} tone={profitDelta >= 0 ? 'up' : 'down'} />
            <MiniKpi label="Policies vs now" value={`${polDelta >= 0 ? '+' : ''}${Math.round(polDelta).toLocaleString()}`} tone={polDelta >= 0 ? 'up' : 'down'} />
          </div>
        )}
      </Step>

      <Step n={3} icon={GitBranch} title="This is how I do it">
        <p>The levers aren't a black box — they're a governed, versioned config. In production this
          strategy is written to <code>optimisation_config</code>, and the maths lives in one readable
          notebook. Straight to the real artefacts:</p>
        <div className="flex flex-wrap gap-1.5">
          <LinkChip href={t.optimisation_config} icon={Database} label="optimisation_config" />
          <LinkChip href={assets?.notebook_url} icon={Cpu} label="price_optimiser notebook" />
        </div>
      </Step>

      <Step n={4} icon={Play} title="This is how it runs">
        <p>Commit it: run the <b>real governed job</b> with the new rate cap (±{fmtPct(levers.rateCap)}).
          It refits the demand curves on the latest quotes and rewrites the governed tables + a new config
          version — a real Databricks job, not a client-side illusion.</p>
        <div className="flex flex-wrap gap-2 items-center">
          <button onClick={triggerRun} disabled={running} className={btnCls}>
            {running ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Running…</> : <><Play className="w-3.5 h-3.5" /> Run the job</>}
          </button>
          {runState && !runState.error && (
            <span className="text-xs text-gray-600 inline-flex items-center gap-1">
              {runOk ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <Loader2 className="w-3.5 h-3.5 animate-spin text-teal-600" />}
              {runOk ? 'Succeeded' : `${runState.life_cycle_state || 'starting'}…`}
            </span>
          )}
          {runState?.run_page_url && <LinkChip href={runState.run_page_url} icon={ExternalLink} label="open the run" />}
          <LinkChip href={assets?.job_url} icon={Play} label="the job" />
        </div>
        {runState?.error && <p className="text-xs text-rose-600">Run error: {runState.error}</p>}
      </Step>

      <Step n={5} icon={Target} title="This is the result">
        <p>{runOk ? 'Governed tables refreshed. ' : ''}The re-solve moves the whole book — explore it on the
          Optimiser tab; these are the current strategy vs today.</p>
        {roll && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <MiniKpi label="Expected profit (book)" value={gbpM(roll.optProfit)} />
            <MiniKpi label="Δ profit vs now" value={`${profitDelta >= 0 ? '+' : ''}${gbpM(profitDelta)}`} tone={profitDelta >= 0 ? 'up' : 'down'} />
            <MiniKpi label="Policies bound" value={Math.round(roll.optPol).toLocaleString()} />
            <MiniKpi label="Avg rate change" value={`${roll.avgRate >= 1 ? '+' : ''}${fmtPct(roll.avgRate - 1)}`} />
          </div>
        )}
        <div className="flex flex-wrap gap-1.5">
          <LinkChip href={t.optimisation_summary} icon={Database} label="optimisation_summary" />
          <LinkChip href={assets?.experiment_url} icon={LineChart} label="MLflow" />
        </div>
      </Step>

      <Step n={6} icon={Activity} title="This is how I monitor it">
        <p>Is the demand model still right? Monthly <b>actual</b> conversion vs what the fitted curves
          <b> expect</b> at the realised price — the gap is drift.</p>
        <button onClick={loadMonitor} disabled={monBusy} className={btnCls}>
          {monBusy ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading…</> : <><Activity className="w-3.5 h-3.5" /> Load the monitor</>}
        </button>
        {monitor && monitor.length > 0 && <MonitorChart months={monitor} />}
        {monitor && monitor.length === 0 && <p className="text-xs text-gray-500">No monitoring rows yet — run the job first.</p>}
        <div className="flex flex-wrap gap-1.5"><LinkChip href={t.optimisation_monitoring} icon={Database} label="optimisation_monitoring" /></div>
      </Step>

      <Step n={7} icon={Bot} title="This is how I govern it — and the agent that helps">
        <p>Every strategy is a versioned <code>optimisation_config</code> row (a diffable audit trail), and
          a fair-value / no-price-walking rule plugs in as another constraint. Ask the <b>rate-change
          agent</b> to pressure-test the move:</p>
        <div className="flex flex-col gap-2">
          <textarea value={agentQ} onChange={(e) => setAgentQ(e.target.value)} rows={2}
            className="w-full text-sm border border-gray-300 rounded-lg p-2" />
          <div className="flex flex-wrap gap-2 items-center">
            <button onClick={askAgent} disabled={agentBusy} className={btnCls}>
              {agentBusy ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Asking…</> : <><Bot className="w-3.5 h-3.5" /> Ask the agent</>}
            </button>
            <LinkChip href={assets?.agent_url} icon={Bot} label="the agent endpoint" />
          </div>
          {agentAns && <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm text-gray-700 whitespace-pre-wrap">{agentAns}</div>}
        </div>
      </Step>

      <p className="text-xs text-gray-500 pt-1">
        Bricksurance SE is fictional; data synthetic. Every step above touches a real platform asset — the
        tables, the job, the MLflow run and the agent endpoint are live in this workspace.
      </p>
    </div>
  );
}

function Slider({ label, value, min, max, step, onChange, display }: {
  label: string; value: number; min: number; max: number; step: number;
  onChange: (v: number) => void; display: string;
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-gray-400 mb-1 flex justify-between">
        <span>{label}</span><span className="text-teal-700 font-semibold">{display}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-teal-600" />
    </div>
  );
}

function Kpi({ label, value, delta, up, big }: { label: string; value: string; delta?: string; up?: boolean; big?: boolean }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="text-[11px] uppercase tracking-wide text-gray-400">{label}</div>
      <div className={`font-bold ${big ? 'text-xl' : 'text-lg'} text-gray-800`}>{value}</div>
      {delta && <div className={`text-xs ${up === undefined ? 'text-gray-500' : up ? 'text-emerald-600' : 'text-rose-600'}`}>{delta}</div>}
    </div>
  );
}
function Cfg({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-gray-400">{label}</div>
      <div className="text-gray-700 capitalize">{value}</div>
    </div>
  );
}

function FrontierChart({ frontier, alpha }: { frontier: { alpha: number; pol: number; profit: number }[]; alpha: number }) {
  if (frontier.length < 2) return <div className="text-sm text-gray-400">No frontier.</div>;
  const W = 300, H = 240, pad = 40;
  const pols = frontier.map((f) => f.pol), profits = frontier.map((f) => f.profit);
  const minX = Math.min(...pols), maxX = Math.max(...pols), minY = Math.min(...profits), maxY = Math.max(...profits);
  const x = (v: number) => pad + (maxX === minX ? 0.5 : (v - minX) / (maxX - minX)) * (W - pad - 12);
  const y = (v: number) => H - pad - (maxY === minY ? 0.5 : (v - minY) / (maxY - minY)) * (H - pad - 12);
  const path = frontier.map((f, i) => `${i ? 'L' : 'M'}${x(f.pol).toFixed(1)},${y(f.profit).toFixed(1)}`).join(' ');
  const here = frontier.reduce((a, b) => Math.abs(b.alpha - alpha) < Math.abs(a.alpha - alpha) ? b : a);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
      <line x1={pad} y1={H - pad} x2={W - 12} y2={H - pad} stroke="#d1d5db" />
      <line x1={pad} y1={12} x2={pad} y2={H - pad} stroke="#d1d5db" />
      <text x={(pad + W) / 2} y={H - 8} textAnchor="middle" fontSize="10" fill="#6b7280">policies bound →</text>
      <text x={12} y={H / 2} textAnchor="middle" fontSize="10" fill="#6b7280" transform={`rotate(-90 12 ${H / 2})`}>expected profit →</text>
      <path d={path} fill="none" stroke="#0d9488" strokeWidth={2} />
      {frontier.map((f, i) => <circle key={i} cx={x(f.pol)} cy={y(f.profit)} r={2.5} fill="#0d9488" opacity={0.6} />)}
      <circle cx={x(here.pol)} cy={y(here.profit)} r={6} fill="none" stroke="#0d9488" strokeWidth={2.5} />
    </svg>
  );
}

function CurveChart({ pts, current, chosen, currentMult, rateCap }: {
  pts: CurvePt[]; current: CurvePt | null; chosen: CurvePt | null; currentMult: number; rateCap: number;
}) {
  if (!pts.length) return <div className="text-sm text-gray-400">No curve.</div>;
  const W = 620, H = 300, padL = 44, padR = 44, padT = 16, padB = 34;
  const xs = pts.map((c) => c.price_multiplier);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const profits = pts.map((c) => c.expected_profit_per_quote);
  const maxProfit = Math.max(...profits), minProfit = Math.min(0, ...profits);
  const x = (m: number) => padL + ((m - minX) / (maxX - minX)) * (W - padL - padR);
  const yC = (c: number) => padT + (1 - c) * (H - padT - padB);
  const yP = (p: number) => padT + (1 - (p - minProfit) / (maxProfit - minProfit)) * (H - padT - padB);
  const capX0 = x(Math.max(minX, currentMult - rateCap)), capX1 = x(Math.min(maxX, currentMult + rateCap));
  const dPath = pts.map((c, i) => `${i ? 'L' : 'M'}${x(c.price_multiplier).toFixed(1)},${yC(c.expected_conversion).toFixed(1)}`).join(' ');
  const pPath = pts.map((c, i) => `${i ? 'L' : 'M'}${x(c.price_multiplier).toFixed(1)},${yP(c.expected_profit_per_quote).toFixed(1)}`).join(' ');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
      <rect x={capX0} y={padT} width={Math.max(0, capX1 - capX0)} height={H - padT - padB} fill="#14b8a6" opacity={0.08} />
      <text x={(capX0 + capX1) / 2} y={padT + 12} textAnchor="middle" fontSize="10" fill="#0d9488">within rate cap</text>
      <line x1={padL} y1={H - padB} x2={W - padR} y2={H - padB} stroke="#d1d5db" />
      <text x={(padL + W - padR) / 2} y={H - 6} textAnchor="middle" fontSize="11" fill="#6b7280">price vs market</text>
      <path d={pPath} fill="none" stroke="#0d9488" strokeWidth={2.5} />
      <path d={dPath} fill="none" stroke="#6366f1" strokeWidth={2} strokeDasharray="4 3" />
      {current && (<>
        <line x1={x(current.price_multiplier)} y1={padT} x2={x(current.price_multiplier)} y2={H - padB} stroke="#9ca3af" strokeDasharray="3 3" />
        <text x={x(current.price_multiplier)} y={H - padB + 14} textAnchor="middle" fontSize="10" fill="#6b7280">current {current.price_multiplier.toFixed(2)}×</text>
      </>)}
      {chosen && (<>
        <line x1={x(chosen.price_multiplier)} y1={padT} x2={x(chosen.price_multiplier)} y2={H - padB} stroke="#0d9488" strokeWidth={1.5} />
        <text x={x(chosen.price_multiplier)} y={padT - 4} textAnchor="middle" fontSize="10" fill="#0d9488" fontWeight="bold">optimal {chosen.price_multiplier.toFixed(2)}×</text>
        <circle cx={x(chosen.price_multiplier)} cy={yP(chosen.expected_profit_per_quote)} r={4} fill="#0d9488" />
      </>)}
      <g fontSize="10">
        <rect x={W - padR - 150} y={padT} width={10} height={3} fill="#0d9488" /><text x={W - padR - 135} y={padT + 4} fill="#374151">expected profit</text>
        <rect x={W - padR - 150} y={padT + 14} width={10} height={3} fill="#6366f1" /><text x={W - padR - 135} y={padT + 18} fill="#374151">conversion</text>
      </g>
    </svg>
  );
}
