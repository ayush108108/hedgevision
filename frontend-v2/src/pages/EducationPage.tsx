import React from "react";
import { Link } from "react-router-dom";
import {
  BookOpen,
  TrendingUp,
  BarChart2,
  Zap,
  AlertTriangle,
  ArrowRight,
  ExternalLink,
  CheckCircle,
  GitCompare,
  Activity,
  Scale,
} from "lucide-react";

function Section({ id, children }: { id?: string; children: React.ReactNode }) {
  return (
    <section id={id} className="space-y-4">
      {children}
    </section>
  );
}

function SectionTitle({ icon: Icon, children }: { icon?: React.ElementType; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      {Icon && (
        <div className="w-9 h-9 rounded-xl bg-blue-500/20 flex items-center justify-center shrink-0">
          <Icon size={18} className="text-blue-400" />
        </div>
      )}
      <h2 className="text-xl sm:text-2xl font-bold text-white">{children}</h2>
    </div>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`premium-card rounded-xl p-5 sm:p-6 ${className}`}>
      {children}
    </div>
  );
}

function ConceptCard({
  term,
  plain,
  technical,
}: {
  term: string;
  plain: string;
  technical: string;
}) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/3 p-4 space-y-2">
      <div className="text-sm font-semibold text-blue-300">{term}</div>
      <div className="text-sm text-white leading-relaxed">{plain}</div>
      <div className="text-xs text-gray-500 leading-relaxed border-t border-white/5 pt-2">{technical}</div>
    </div>
  );
}

function PaperCard({
  authors,
  year,
  title,
  finding,
}: {
  authors: string;
  year: number;
  title: string;
  finding: string;
}) {
  return (
    <Card>
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center shrink-0 mt-0.5">
          <ExternalLink size={14} className="text-purple-400" />
        </div>
        <div className="space-y-1.5 min-w-0">
          <div className="text-xs text-purple-400 font-medium">
            {authors} · {year}
          </div>
          <div className="text-sm font-semibold text-white leading-snug">{title}</div>
          <div className="text-xs text-gray-400 leading-relaxed">{finding}</div>
        </div>
      </div>
    </Card>
  );
}

export function EducationPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-14 pb-16">
      {/* ── Hero ─────────────────────────────────────────────── */}
      <div className="text-center space-y-4 pt-4">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-500/15 border border-blue-500/25 text-blue-300 text-sm font-medium">
          <BookOpen size={14} />
          Learn
        </div>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white leading-tight">
          What is Statistical Arbitrage?
        </h1>
        <p className="text-gray-400 text-base sm:text-lg max-w-2xl mx-auto leading-relaxed">
          A plain-English guide to pairs trading — a strategy used by hedge funds and quantitative traders
          to profit from <em>relative mispricing</em> between two linked assets.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
          <Link
            to="/cointegration"
            className="premium-button px-5 py-2.5 rounded-xl text-sm font-medium flex items-center justify-center gap-2"
          >
            <TrendingUp size={15} />
            Try the Screener
          </Link>
          <a
            href="#concepts"
            className="px-5 py-2.5 rounded-xl text-sm font-medium border border-white/10 text-gray-300 hover:text-white hover:border-white/25 flex items-center justify-center gap-2 transition-colors"
          >
            Jump to Concepts
            <ArrowRight size={14} />
          </a>
        </div>
      </div>

      {/* ── What is it? ──────────────────────────────────────── */}
      <Section>
        <SectionTitle icon={BookOpen}>What is Statistical Arbitrage?</SectionTitle>
        <Card>
          <p className="text-gray-300 text-sm sm:text-base leading-relaxed">
            Imagine two boats tied together with a rope floating on the ocean. When waves push
            them apart, the rope eventually pulls them back together. Statistical arbitrage (stat-arb)
            finds pairs of assets that behave like those boats — they tend to move together over time.
          </p>
          <p className="text-gray-300 text-sm sm:text-base leading-relaxed mt-4">
            When the "rope" between two assets stretches (the spread widens), a trader buys the
            underperforming asset and shorts the outperforming one, betting the gap will close.
            The profit comes from the <strong className="text-white">relative movement between the two</strong>,
            not from the overall market direction.
          </p>
          <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-emerald-900/20 border border-emerald-700/25 rounded-lg p-4">
              <div className="text-emerald-400 font-semibold text-sm mb-1">✓ What you're betting on</div>
              <div className="text-gray-300 text-sm leading-relaxed">
                That two correlated assets will return to their historical price relationship — not that
                the market goes up or down.
              </div>
            </div>
            <div className="bg-blue-900/20 border border-blue-700/25 rounded-lg p-4">
              <div className="text-blue-400 font-semibold text-sm mb-1">~ Market neutral</div>
              <div className="text-gray-300 text-sm leading-relaxed">
                Because you hold both a long and short position simultaneously, a broad market crash
                affects both legs — limiting your exposure to systematic risk.
              </div>
            </div>
          </div>
        </Card>
      </Section>

      {/* ── Why it works ─────────────────────────────────────── */}
      <Section>
        <SectionTitle icon={Activity}>Why Does It Work?</SectionTitle>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            {
              icon: Scale,
              title: "Law of One Price",
              body: "Two assets exposed to the same underlying economic factors should trade at a consistent ratio over time. Deviations are temporary mispricings.",
            },
            {
              icon: Activity,
              title: "Mean Reversion",
              body: "Markets tend to overcorrect and then snap back. Extreme spreads between related assets are statistically likely to narrow again.",
            },
            {
              icon: TrendingUp,
              title: "Shared Fundamentals",
              body: "Two companies in the same industry often have correlated revenues, input costs, and investors — making persistent divergence unusual.",
            },
          ].map(({ icon: Icon, title, body }) => (
            <Card key={title} className="space-y-3">
              <div className="w-9 h-9 rounded-xl bg-blue-500/15 flex items-center justify-center">
                <Icon size={18} className="text-blue-400" />
              </div>
              <div className="font-semibold text-white text-sm">{title}</div>
              <div className="text-gray-400 text-xs leading-relaxed">{body}</div>
            </Card>
          ))}
        </div>
      </Section>

      {/* ── How it works — step by step ──────────────────────── */}
      <Section>
        <SectionTitle icon={GitCompare}>How It Works — Step by Step</SectionTitle>
        <div className="space-y-3">
          {[
            {
              step: "1",
              title: "Find candidates",
              body: "Use HedgeVision's Screener to scan for pairs of assets with high historical correlation. Think Coca-Cola & Pepsi, Bitcoin & Ethereum, Gold & Gold Miners.",
              color: "blue",
            },
            {
              step: "2",
              title: "Test for cointegration",
              body: "Correlation measures how assets move in the short term. Cointegration tests whether they share a long-run equilibrium — that's what matters for this strategy.",
              color: "purple",
            },
            {
              step: "3",
              title: "Measure the spread",
              body: "Compute the spread: the difference between the actual price ratio and the historical average. Normalize it by converting to a z-score.",
              color: "cyan",
            },
            {
              step: "4",
              title: "Enter when the spread stretches",
              body: "When |z-score| > 1.5–2.0, the spread is statistically extreme. Buy the lagging asset, short the leading one. Use the Hedge Ratio Calculator to size the trade.",
              color: "amber",
            },
            {
              step: "5",
              title: "Exit when spread closes",
              body: "Close both positions when the z-score returns near zero — the spread has mean-reverted and you lock in profit.",
              color: "emerald",
            },
          ].map(({ step, title, body, color }) => (
            <div key={step} className={`flex gap-4 p-4 rounded-xl border border-${color}-700/20 bg-${color}-900/10`}>
              <div
                className={`w-8 h-8 rounded-full bg-${color}-500/25 text-${color}-300 font-bold text-sm flex items-center justify-center shrink-0`}
              >
                {step}
              </div>
              <div>
                <div className={`text-${color}-300 font-semibold text-sm mb-1`}>{title}</div>
                <div className="text-gray-400 text-xs sm:text-sm leading-relaxed">{body}</div>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* ── Key Concepts ─────────────────────────────────────── */}
      <Section id="concepts">
        <SectionTitle icon={BookOpen}>Key Concepts Explained Simply</SectionTitle>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <ConceptCard
            term="Correlation"
            plain="How closely two assets move in the same direction at the same time. Two friends who always laugh at the same jokes — 100% correlated."
            technical="Pearson correlation coefficient ρ ∈ [−1, 1]. For pairs trading, we typically require ρ > 0.7 as a preliminary filter."
          />
          <ConceptCard
            term="Cointegration"
            plain="Two assets that always drift back toward each other over the long run, even if they wander in the short term. Like two friends who always meet for dinner eventually, no matter how far apart they roam during the day."
            technical="Two I(1) time series are cointegrated if a linear combination produces a stationary I(0) series. Tested via Engle-Granger or Johansen tests."
          />
          <ConceptCard
            term="Z-Score"
            plain="A number that tells you how unusual the current spread is compared to history. A z-score of 2.0 means the spread is wider than 97.7% of all historical observations — very unusual."
            technical="z = (spread − μ) / σ, where μ and σ are the rolling mean and standard deviation of the spread. Trade signals typically use |z| > 1.5–2."
          />
          <ConceptCard
            term="Hedge Ratio"
            plain="The exact ratio of how much money to put on each asset so the trade is balanced. If you put $1 on Asset A, the hedge ratio tells you exactly how much to put on Asset B."
            technical="β from OLS regression: Y = α + βX + ε. For every unit of X held long, β units of Y are held short. Ensures the position is market-neutral."
          />
          <ConceptCard
            term="Half-Life"
            plain="How long, on average, it takes for a spread to close halfway to the mean after it opens. A half-life of 7 days means your money is typically tied up for about 1–2 weeks."
            technical="Derived from the Ornstein-Uhlenbeck mean-reversion model: Δspread_t = λ·spread_{t-1} + ε_t. Half-life = −ln(2) / ln(1 + λ)."
          />
          <ConceptCard
            term="Spread"
            plain="The gap between where the price ratio is now and where it normally sits. Think of it as the distance the boats have drifted apart before the rope pulls them back."
            technical="spread_t = Y_t − (α + β·X_t). The residual from the cointegrating regression. Normalized to z-score for interpretability."
          />
          <ConceptCard
            term="Mean Reversion"
            plain="The tendency for extreme values to return to normal over time. Like a rubber band: the more it stretches, the harder it snaps back."
            technical="Quantified by the speed-of-adjustment parameter λ in the error-correction model. Faster λ ≈ shorter half-life ≈ quicker opportunities."
          />
          <ConceptCard
            term="P-Value"
            plain="A measure of how confident we are that the pattern we see isn't just random luck. We want p-values below 0.05 — meaning there's less than a 5% chance the cointegration is a coincidence."
            technical="From the Augmented Dickey-Fuller (ADF) test on the regression residuals. Lower p-value = stronger evidence of cointegration."
          />
        </div>
      </Section>

      {/* ── Literature Insights ───────────────────────────────── */}
      <Section>
        <SectionTitle icon={BarChart2}>What Academic Research Shows</SectionTitle>
        <p className="text-gray-400 text-sm leading-relaxed">
          Pairs trading has been studied extensively in academic finance. Here are the key findings:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <PaperCard
            authors="Gatev, Goetzmann & Rouwenhorst"
            year={2006}
            title="Pairs Trading: Performance of a Relative‑Value Arbitrage Rule"
            finding='The landmark study. Found annualised excess returns of ~11% using a simple pairs approach on US equities (1962–2002). Returns persisted even after transaction costs. Published in the Review of Financial Studies — widely cited as the "proof of concept" for the strategy.'
          />
          <PaperCard
            authors="Rad, Low & Faff"
            year={2016}
            title="The Profitability of Pairs Trading Strategies: a Comprehensive Review"
            finding="Broad survey of pairs strategies across different markets and time periods. Confirmed profitability in most regimes but noted declining returns in recent years as the strategy became more popular. Better results emerged from cointegration-based approaches vs. distance methods."
          />
          <PaperCard
            authors="Do & Faff"
            year={2010}
            title="Does Simple Pairs Trading Still Work?"
            finding="Examined whether profits declined post-2000. Found reduced but still positive returns, suggesting the strategy remains viable when implemented with discipline. The decline was attributed to increased arbitrage capital chasing the same opportunities."
          />
          <PaperCard
            authors="Vidyamurthy"
            year={2004}
            title="Pairs Trading: Quantitative Methods and Analysis"
            finding='The definitive practitioner textbook. Introduced the cointegration framework for pairs trading that most systematic desks now use — replacing the older "distance" method with a more statistically rigorous approach based on OLS regression and ADF testing.'
          />
        </div>
        <div className="bg-blue-900/20 border border-blue-700/25 rounded-xl p-4 text-xs text-blue-200 leading-relaxed">
          <strong className="text-blue-300">Key takeaway:</strong> The strategy works best with careful pair selection
          (cointegration over simple correlation), disciplined position sizing, and fast execution.
          Returns have compressed in mature markets — edge comes from finding pairs others miss
          (less-covered assets, cross-sector pairs, international markets).
        </div>
      </Section>

      {/* ── Risks ────────────────────────────────────────────── */}
      <Section>
        <SectionTitle icon={AlertTriangle}>Risks You Must Understand</SectionTitle>
        <div className="space-y-3">
          {[
            {
              risk: "Relationship Breakdown",
              body: "The biggest risk. Two assets that were correlated for years can diverge permanently — for example, if one company merges, changes business model, or faces regulatory change. Always monitor for regime changes.",
            },
            {
              risk: "Spread Can Widen Before It Closes",
              body: "A stretched z-score of 2.0 can become 3.0 or 4.0 before reversing. Trades need enough capital buffer to survive wider-than-expected swings. Never use 100% of your capital on entry.",
            },
            {
              risk: "Short-Selling Costs and Availability",
              body: "Short-selling requires borrowing shares and paying a borrow rate. In volatile markets, shares can become hard to borrow and the cost can erode returns significantly.",
            },
            {
              risk: "Execution Risk",
              body: "In fast-moving markets, both legs of the trade may not fill at the expected prices simultaneously. Slippage can eat into the small profit margins this strategy generates.",
            },
            {
              risk: "Overfitting",
              body: "Finding pairs that worked historically doesn't guarantee they'll work in the future. Always validate out-of-sample and treat very low p-values with skepticism on short data histories.",
            },
          ].map(({ risk, body }) => (
            <div
              key={risk}
              className="flex gap-3 p-4 rounded-xl border border-amber-700/20 bg-amber-900/10"
            >
              <AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" />
              <div>
                <div className="text-amber-300 font-semibold text-sm mb-1">{risk}</div>
                <div className="text-gray-400 text-xs sm:text-sm leading-relaxed">{body}</div>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* ── Getting Started CTA ───────────────────────────────── */}
      <Section>
        <Card className="text-center space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-blue-500/20 flex items-center justify-center mx-auto">
            <Zap size={22} className="text-blue-400" />
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white">Ready to try it?</h2>
          <p className="text-gray-400 text-sm sm:text-base max-w-lg mx-auto leading-relaxed">
            HedgeVision's Screener scans hundreds of asset pairs, runs cointegration tests automatically,
            and surfaces the strongest opportunities. No PhD required.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              to="/cointegration"
              className="premium-button px-6 py-2.5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2"
            >
              <TrendingUp size={15} />
              Open Screener
            </Link>
            <Link
              to="/pair-analysis"
              className="px-6 py-2.5 rounded-xl text-sm font-medium border border-white/10 text-gray-300 hover:text-white hover:border-white/25 flex items-center justify-center gap-2 transition-colors"
            >
              <GitCompare size={15} />
              Analyse a Pair
            </Link>
          </div>
          <div className="flex flex-wrap justify-center gap-4 pt-2 text-xs text-gray-500">
            {["No account required", "Paper trading only", "SQLite — runs locally", "Open source"].map(
              (fact) => (
                <span key={fact} className="flex items-center gap-1">
                  <CheckCircle size={11} className="text-emerald-500" />
                  {fact}
                </span>
              )
            )}
          </div>
        </Card>
      </Section>
    </div>
  );
}
