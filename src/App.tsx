import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  AlertOctagon,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  BadgeCheck,
  BookOpen,
  CircleDot,
  Database,
  ExternalLink,
  Info,
  Moon,
  ScanLine,
  Store,
  Sun,
  X,
  Zap,
} from "lucide-react";
import CustomerCohort from "./components/CustomerCohort";
import type { CustomerSort, SortDirection } from "./components/CustomerCohort";
import RiskBadge from "./components/RiskBadge";
import RiskFlow from "./components/RiskFlow";
import ScoreDistribution from "./components/ScoreDistribution";
import ScoreTimeline from "./components/ScoreTimeline";
import type { Customer, CustomerFilter, CustomerResponse, ModelMetrics, PortfolioSummary, RiskTier } from "./types";

type View = "overview" | "explorer" | "customers" | "customer" | "evaluation";
type RouteState = { view: View; customerId: string | null; tier: CustomerFilter };
type ExplorerMode = "landscape" | "distribution";

const API_TIMEOUT = 10_000;
const PAGE_SIZE = 20;
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const RISK_ORDER: RiskTier[] = ["High", "Medium", "Low"];

async function api<T>(url: string, timeout = API_TIMEOUT): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, { signal: controller.signal, cache: "no-store" });
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    return response.json() as Promise<T>;
  } finally {
    window.clearTimeout(timer);
  }
}

function parseTier(raw: string | null): CustomerFilter {
  return raw === "High" || raw === "Medium" || raw === "Low" || raw === "Review" ? raw : "All";
}

function readRoute(): RouteState {
  const params = new URLSearchParams(window.location.search);
  const customerId = params.get("customer");
  if (customerId) return { view: "customer", customerId, tier: parseTier(params.get("tier")) };
  const requested = params.get("view");
  const view: View = requested === "explorer" || requested === "customers" || requested === "evaluation" ? requested : "overview";
  return { view, customerId: null, tier: parseTier(params.get("tier")) };
}

function routeUrl(view: View, customerId: string | null = null, tier: CustomerFilter = "All") {
  if (view === "customer" && customerId) return `/?customer=${encodeURIComponent(customerId)}`;
  if (view === "overview") return "/";
  const params = new URLSearchParams({ view });
  if (view === "customers" && tier !== "All") params.set("tier", tier);
  return `/?${params.toString()}`;
}

const formatScore = (value: number) => value.toFixed(3);
const formatRate = (value: number) => `${(value * 100).toFixed(1)}%`;
const formatDays = (value: number) => Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1);

export default function App() {
  const initialRoute = useMemo(readRoute, []);
  const [view, setView] = useState<View>(initialRoute.view);
  const [theme, setTheme] = useState<"light" | "dark">(() => (localStorage.getItem("theme") || localStorage.getItem("instacart-analysis-theme")) === "dark" ? "dark" : "light");
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [landscapeCustomers, setLandscapeCustomers] = useState<Customer[]>([]);
  const [landscapeLoading, setLandscapeLoading] = useState(true);
  const [landscapeError, setLandscapeError] = useState<string | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerTotal, setCustomerTotal] = useState(0);
  const [customerTotalPages, setCustomerTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<CustomerFilter>(initialRoute.tier);
  const [sortBy, setSortBy] = useState<CustomerSort>("score");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [selectedId, setSelectedId] = useState<string | null>(initialRoute.customerId);
  const [selected, setSelected] = useState<Customer | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [previewCustomer, setPreviewCustomer] = useState<Customer | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [explorerMode, setExplorerMode] = useState<ExplorerMode>("landscape");
  const [explorerFilter, setExplorerFilter] = useState<"All" | RiskTier>("All");
  const pageRef = useRef<HTMLElement | null>(null);
  const pendingScroll = useRef<number | null>(0);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    const previous = window.history.scrollRestoration;
    window.history.scrollRestoration = "manual";
    const onPopState = () => {
      const next = readRoute();
      setView(next.view);
      setSelectedId(next.customerId);
      setFilter(next.tier);
      pendingScroll.current = 0;
      setPreviewId(null);
    };
    window.addEventListener("popstate", onPopState);
    return () => { window.removeEventListener("popstate", onPopState); window.history.scrollRestoration = previous; };
  }, []);

  useLayoutEffect(() => {
    if (pendingScroll.current === null) return;
    pendingScroll.current = null;
    window.requestAnimationFrame(() => { window.scrollTo({ top: 0, left: 0, behavior: "instant" }); pageRef.current?.focus({ preventScroll: true }); });
  }, [view, selectedId]);

  useEffect(() => {
    api<PortfolioSummary>(`${API_BASE}/api/portfolio-summary`).then((data) => { setSummary(data); setSummaryError(null); }).catch(() => setSummaryError("Portfolio summary is unavailable."));
    api<ModelMetrics>(`${API_BASE}/api/model-metrics`, 12_000).then((data) => { setMetrics(data); setMetricsError(null); }).catch(() => setMetricsError("Model evaluation is unavailable."));
    Promise.all(RISK_ORDER.map((tier) => api<CustomerResponse>(`${API_BASE}/api/customers?page=1&pageSize=40&tier=${tier}`)))
      .then((responses) => { setLandscapeCustomers(responses.flatMap((response) => response.customers)); setLandscapeError(null); })
      .catch(() => setLandscapeError("Portfolio flow data is unavailable."))
      .finally(() => setLandscapeLoading(false));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const delayed = window.setTimeout(() => {
      setListLoading(true);
      const params = new URLSearchParams({ page: String(page), pageSize: String(PAGE_SIZE), tier: filter, search, sortBy, sortDir: sortDirection });
      fetch(`${API_BASE}/api/customers?${params}`, { signal: controller.signal, cache: "no-store" })
        .then((response) => { if (!response.ok) throw new Error(`Request failed (${response.status})`); return response.json() as Promise<CustomerResponse>; })
        .then((data) => { setCustomers(data.customers || []); setCustomerTotal(data.total || 0); setCustomerTotalPages(Math.max(1, data.totalPages || 1)); setListError(null); })
        .catch((error: unknown) => { if (!(error instanceof DOMException && error.name === "AbortError")) { setCustomers([]); setCustomerTotal(0); setCustomerTotalPages(1); setListError("Customer evidence is unavailable."); } })
        .finally(() => { if (!controller.signal.aborted) setListLoading(false); });
    }, 180);
    return () => { controller.abort(); window.clearTimeout(delayed); };
  }, [page, search, filter, sortBy, sortDirection]);

  useEffect(() => {
    if (!selectedId) return;
    setSelected(null);
    setDetailError(null);
    api<Customer>(`${API_BASE}/api/customers/${selectedId}`).then(setSelected).catch(() => setDetailError("Customer evidence is unavailable."));
  }, [selectedId]);

  useEffect(() => {
    if (!previewId) { setPreviewCustomer(null); return; }
    setPreviewLoading(true);
    setPreviewCustomer(null);
    api<Customer>(`${API_BASE}/api/customers/${previewId}`).then(setPreviewCustomer).catch(() => setPreviewCustomer(null)).finally(() => setPreviewLoading(false));
  }, [previewId]);

  const navigate = (nextView: View, customerId: string | null = null, tier: CustomerFilter = filter) => {
    pendingScroll.current = 0;
    window.history.pushState({}, "", routeUrl(nextView, customerId, tier));
    setSelectedId(customerId);
    setView(nextView);
    setPreviewId(null);
  };

  const openCustomers = (tier: CustomerFilter = "All") => { setFilter(tier); setPage(1); setSearch(""); navigate("customers", null, tier); };
  const inspectCustomer = (customer: Customer) => setPreviewId(customer.id);
  const initialLoading = !summary && !summaryError;

  return (
    <div className="app-shell">
      {initialLoading ? <LoadingScreen /> : null}
      <Topbar view={view} theme={theme} onTheme={() => setTheme(theme === "light" ? "dark" : "light")} onNavigate={navigate} />

      {view === "overview" ? <PortfolioOverview summary={summary} error={summaryError} customers={landscapeCustomers} chartLoading={landscapeLoading} chartError={landscapeError} onExplore={() => navigate("explorer")} onCustomers={() => openCustomers("All")} onInspect={inspectCustomer} /> : null}
      {view === "explorer" ? <PortfolioExplorer customers={landscapeCustomers} loading={landscapeLoading} error={landscapeError} mode={explorerMode} filter={explorerFilter} onMode={setExplorerMode} onFilter={setExplorerFilter} onInspect={inspectCustomer} onCustomers={() => openCustomers(explorerFilter)} /> : null}
      {view === "customers" ? (
        <main className="page retail-page" ref={pageRef} tabIndex={-1}>
          <RetailContext icon="store" label="Customer operations" location="Review floor" />
          <PageHeader title="Customer Explorer" subtitle="Search and review customers whose shopping rhythm has changed." />
          <CustomerCohort customers={customers} total={customerTotal} page={page} pageSize={PAGE_SIZE} totalPages={customerTotalPages} loading={listLoading} error={listError} search={search} filter={filter} sortBy={sortBy} sortDirection={sortDirection} onSearch={(value) => { setSearch(value); setPage(1); }} onFilter={(value) => { setFilter(value); setPage(1); window.history.replaceState({}, "", routeUrl("customers", null, value)); }} onSortBy={(value) => { setSortBy(value); setPage(1); }} onSortDirection={(value) => { setSortDirection(value); setPage(1); }} onReset={() => { setSearch(""); setFilter("All"); setSortBy("score"); setSortDirection("desc"); setPage(1); window.history.replaceState({}, "", routeUrl("customers", null, "All")); }} onPage={setPage} onSelect={(customer) => navigate("customer", customer.id)} />
        </main>
      ) : null}
      {view === "customer" ? (
        <main className="page evidence-page" ref={pageRef} tabIndex={-1}>
          <button className="back-action" type="button" onClick={() => openCustomers(filter)}><ArrowLeft size={16} aria-hidden="true" /> Back to Customer Explorer</button>
          {detailError ? <ErrorState text={detailError} /> : !selected ? <InlineLoading text="Loading customer evidence…" /> : <CustomerEvidence customer={selected} />}
        </main>
      ) : null}
      {view === "evaluation" ? (
        <main className="page retail-page evaluation-retail" ref={pageRef} tabIndex={-1}>
          <RetailContext icon="quality" label="Model assurance" location="Quality counter" />
          <PageHeader title="Model Evaluation" subtitle="Held-out performance metrics and operational threshold behavior." />
          {metricsError ? <ErrorState text={metricsError} /> : !metrics ? <InlineLoading text="Loading model evaluation…" /> : <EvaluationEvidence metrics={metrics} />}
        </main>
      ) : null}

      {previewId ? <CustomerDrawer customer={previewCustomer} loading={previewLoading} onClose={() => setPreviewId(null)} onViewEvidence={(id) => navigate("customer", id)} /> : null}
    </div>
  );
}

function Topbar({ view, theme, onTheme, onNavigate }: { view: View; theme: "light" | "dark"; onTheme: () => void; onNavigate: (view: View) => void }) {
  return (
    <header className="topbar">
      <button className="wordmark" type="button" onClick={() => onNavigate("overview")} aria-label="Purchase Pattern Decay Analysis overview"><span className="brand-mark"><img src="/instacart-carrot.svg" alt="" /></span><span>Purchase Pattern Decay</span></button>
      <nav aria-label="Primary navigation">
        <button type="button" className={view === "overview" || view === "explorer" ? "active" : ""} onClick={() => onNavigate("overview")}>Portfolio Overview</button>
        <button type="button" className={view === "evaluation" ? "active" : ""} onClick={() => onNavigate("evaluation")}>Model Evaluation</button>
        <button type="button" className={view === "customers" || view === "customer" ? "active" : ""} onClick={() => onNavigate("customers")}>Customer Explorer</button>
      </nav>
      <button className="theme-toggle" type="button" onClick={onTheme} aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}>{theme === "light" ? <Moon size={16} aria-hidden="true" /> : <Sun size={16} aria-hidden="true" />}</button>
    </header>
  );
}

function PageHeader({ title, subtitle, status = false }: { title: string; subtitle: string; status?: boolean }) {
  return <header className="page-header"><div><h1>{title}</h1><p>{subtitle}</p></div>{status ? <span className="data-status"><i /> Data refreshed recently</span> : null}</header>;
}

function RetailContext({ icon, label, location }: { icon: "store" | "quality"; label: string; location: string }) {
  const Icon = icon === "store" ? Store : BadgeCheck;
  return <div className="retail-context"><span className="retail-context-icon"><Icon size={15} aria-hidden="true" /></span><strong>{label}</strong><i /><span>{location}</span></div>;
}

function PortfolioOverview({ summary, error, customers, chartLoading, chartError, onExplore, onCustomers, onInspect }: { summary: PortfolioSummary | null; error: string | null; customers: Customer[]; chartLoading: boolean; chartError: string | null; onExplore: () => void; onCustomers: () => void; onInspect: (customer: Customer) => void }) {
  const elevated = summary ? summary.highRiskCount + summary.mediumRiskCount : 0;
  const priorities = customers.filter((customer) => customer.riskTier !== "Low").sort((a, b) => b.riskScore - a.riskScore).slice(0, 4);
  const featured = priorities[0];
  return (
    <main className="page" tabIndex={-1}>
      <PageHeader title="Portfolio Retention Overview" subtitle="Monitor changes in customer shopping rhythm and identify customers who may benefit from review." status />
      <section className="project-intro" aria-label="Project introduction"><span>Project brief</span><p>Built from anonymized Instacart order histories, this project identifies customers whose shopping rhythm may be slowing. It ranks behavioral changes for human review—not as a definitive prediction.</p></section>
      <AnalysisDisclosure />
      {error || !summary ? <ErrorState text={error || "Portfolio summary is unavailable."} /> : (
        <section className="portfolio-health" aria-label="Portfolio health">
          <div className="health-primary"><span className="eyebrow">Portfolio Health</span><strong>{elevated.toLocaleString()}</strong><h2>Customers merit attention</h2><p>{summary.elevatedRiskPercentage.toFixed(1)}% of the scored cohort is in a Priority or Watch retention status.</p></div>
          <div className="health-composition"><div className="composition-heading"><span>Operational priority</span><small>Severity is shown separately from portfolio prevalence.</small></div><div className="risk-lens">{RISK_ORDER.map((tier) => { const count = tier === "High" ? summary.highRiskCount : tier === "Medium" ? summary.mediumRiskCount : summary.lowRiskCount; const percent = summary.totalCustomers ? count / summary.totalCustomers * 100 : 0; return <div key={tier} className={`risk-lens-row ${tier.toLowerCase()}`}><span className="severity-mark"><i />{tier === "High" ? "Immediate review" : tier === "Medium" ? "Monitor closely" : "Stable signal"}</span><RiskBadge tier={tier} suffix="" /><strong>{count.toLocaleString()}</strong><span>{percent.toFixed(1)}% of portfolio</span></div>; })}</div><button className="text-action" type="button" onClick={onExplore}>Explore portfolio <ArrowRight size={15} aria-hidden="true" /></button></div>
        </section>
      )}
      <section className="analytics-surface flow-surface" aria-labelledby="retention-flow-title">
        <div className="section-header"><div><span className="eyebrow">Explore</span><h2 id="retention-flow-title">Shopping Rhythm to Retention Status</h2><p>See how changes in purchase timing connect to each customer status.</p></div><span className="interaction-note">Hover to understand · select to inspect</span></div>
        {chartError ? <ErrorState text={chartError} /> : chartLoading ? <InlineLoading text="Loading retention flow…" /> : <RiskFlow customers={customers} onSelect={onInspect} />}
      </section>
      <section className="priority-review">
        <div className="section-header"><div><span className="eyebrow">Investigate</span><h2>Priority Review</h2><p>A short operational queue, ranked by current model score.</p></div><button className="text-action" type="button" onClick={onCustomers}>Open full queue <ArrowRight size={15} aria-hidden="true" /></button></div>
        {featured ? <div className="priority-command">
          <article className="priority-featured">
            <div className="featured-topline"><span>01 · Next review</span><RiskBadge tier={featured.riskTier} suffix="" /></div>
            <strong className="featured-id">CUST-{featured.id}</strong>
            <p>{featured.primaryRiskDriver.feature}</p>
            <div className="featured-score"><span><small>Model score</small><strong>{formatScore(featured.riskScore)}</strong></span><span className="score-rail"><i style={{ width: `${featured.riskScore * 100}%` }} /></span></div>
            <button className="primary-action" type="button" onClick={() => onInspect(featured)}>Inspect evidence <ArrowRight size={15} aria-hidden="true" /></button>
          </article>
          <div className="priority-stack">{priorities.slice(1).map((customer, index) => <button type="button" key={customer.id} className="priority-row" onClick={() => onInspect(customer)}><span className="rank">{String(index + 2).padStart(2, "0")}</span><span className="priority-person"><strong>CUST-{customer.id}</strong><small>{customer.primaryRiskDriver.feature}</small></span><RiskBadge tier={customer.riskTier} suffix="" /><span className="row-metric"><small>Score</small><strong>{formatScore(customer.riskScore)}</strong></span><span className="row-metric"><small>Gap</small><strong>{formatDays(customer.lastPurchaseDays)}d</strong></span><ArrowRight size={15} aria-hidden="true" /></button>)}</div>
        </div> : null}
      </section>
    </main>
  );
}

function PortfolioExplorer({ customers, loading, error, mode, filter, onMode, onFilter, onInspect, onCustomers }: { customers: Customer[]; loading: boolean; error: string | null; mode: ExplorerMode; filter: "All" | RiskTier; onMode: (mode: ExplorerMode) => void; onFilter: (tier: "All" | RiskTier) => void; onInspect: (customer: Customer) => void; onCustomers: () => void }) {
  const highCount = customers.filter((customer) => customer.riskTier === "High").length;
  return (
    <main className="page explorer-page" tabIndex={-1}>
      <PageHeader title="Portfolio Explorer" subtitle="Explore changes in shopping rhythm and customer retention status." />
      <div className="explorer-toolbar"><div className="mode-switch" aria-label="Visualization mode"><button type="button" className={mode === "landscape" ? "selected" : ""} onClick={() => onMode("landscape")}><CircleDot size={15} aria-hidden="true" /> Retention Flow</button><button type="button" className={mode === "distribution" ? "selected" : ""} onClick={() => onMode("distribution")}><BarChart3 size={15} aria-hidden="true" /> Score Distribution</button></div>{mode === "landscape" ? <div className="filter-row" aria-label="Retention status filter">{(["All", ...RISK_ORDER] as const).map((tier) => <button key={tier} type="button" className={filter === tier ? "selected" : ""} onClick={() => onFilter(tier)}>{tier === "All" ? "All" : tier === "High" ? "Priority" : tier === "Medium" ? "Watch" : "Stable"}</button>)}</div> : null}</div>
      <section className="analytics-surface explorer-canvas flow-surface"><div className="section-header"><div><h2>{mode === "landscape" ? "Shopping Rhythm to Retention Status" : "Score Distribution"}</h2><p>{mode === "landscape" ? "Follow changes in purchase timing into each status and inspect any flow." : `${highCount} of ${customers.length} sampled customers are in the Priority range.`}</p></div>{mode === "landscape" ? <span className="interaction-note">Interactive retention flow</span> : null}</div>{error ? <ErrorState text={error} /> : loading ? <InlineLoading text="Loading portfolio analysis…" /> : mode === "landscape" ? <RiskFlow customers={customers} filter={filter} onSelect={onInspect} /> : <ScoreDistribution customers={customers} />}</section>
      <div className="explorer-footer"><span>Flow view uses a balanced sample from the existing customer API.</span><button className="text-action" type="button" onClick={onCustomers}>View matching customers <ArrowRight size={15} aria-hidden="true" /></button></div>
    </main>
  );
}

function CustomerDrawer({ customer, loading, onClose, onViewEvidence }: { customer: Customer | null; loading: boolean; onClose: () => void; onViewEvidence: (id: string) => void }) {
  useEffect(() => { const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); }; window.addEventListener("keydown", onKey); return () => window.removeEventListener("keydown", onKey); }, [onClose]);
  return <div className="drawer-layer" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><aside className="customer-drawer" role="dialog" aria-modal="true" aria-label="Customer preview"><button className="drawer-close" type="button" onClick={onClose} aria-label="Close preview"><X size={18} aria-hidden="true" /></button>{loading || !customer ? <InlineLoading text="Loading customer preview…" /> : <><div className="drawer-heading"><span className="eyebrow">Customer preview</span><h2>CUST-{customer.id}</h2><RiskBadge tier={customer.riskTier} /></div><dl className="drawer-metrics"><div><dt>Model Score</dt><dd>{formatScore(customer.riskScore)}</dd></div><div><dt>Latest Behavioral Gap</dt><dd>{formatDays(customer.lastPurchaseDays)} days</dd></div></dl><div className="drawer-signal"><span>Primary Signal</span><strong>{customer.primaryRiskDriver.feature}</strong></div><div className="drawer-history"><span>Historical trend</span><ScoreTimeline data={customer.timelineHistory || []} compact /></div><button className="primary-action" type="button" onClick={() => onViewEvidence(customer.id)}>View Full Evidence <ArrowRight size={16} aria-hidden="true" /></button></>}</aside></div>;
}

function CustomerEvidence({ customer }: { customer: Customer }) {
  const gapRatio = customer.historicAvgGap > 0 ? customer.lastPurchaseDays / customer.historicAvgGap : 0;
  const gapDelta = customer.lastPurchaseDays - customer.historicAvgGap;
  return <>
    <PageHeader title={`Customer Evidence — CUST-${customer.id}`} subtitle="Individual behavioral signals and model contributions for operational review." />
    <section className={`evidence-hero ${customer.riskTier.toLowerCase()}`}>
      <div className="evidence-identity"><span className="eyebrow">Scored snapshot · {customer.lastPurchaseDate}</span><h2>CUST-{customer.id}</h2><RiskBadge tier={customer.riskTier} /><p><strong>{gapRatio.toFixed(2)}×</strong> the customer’s historical purchase gap <span>{gapDelta >= 0 ? "+" : "−"}{Math.abs(gapDelta).toFixed(1)} days</span></p></div>
      <div className="evidence-score-block"><div><span>Retention position</span><strong>{formatScore(customer.riskScore)}</strong></div><div className="evidence-score-scale" aria-label={`Model score ${formatScore(customer.riskScore)}`}><i className="medium-threshold" /><i className="high-threshold" /><span style={{ left: `${customer.riskScore * 100}%` }} /></div><div className="score-labels"><span>Stable</span><span>Watch</span><span>Priority</span></div></div>
      <dl><div><dt>Latest Gap</dt><dd>{formatDays(customer.lastPurchaseDays)} days</dd></div><div><dt>Historical Avg Gap</dt><dd>{formatDays(customer.historicAvgGap)} days</dd></div><div><dt>Orders Observed</dt><dd>{customer.orderVolume.toLocaleString()}</dd></div></dl>
    </section>
    <section className="analytics-surface evidence-chart"><div className="section-header"><div><span className="eyebrow">Behavior over time</span><h2>Score History</h2><p>Observed model score across relative customer-lifecycle time.</p></div><span className="interaction-note">Hover to inspect a snapshot</span></div><ScoreTimeline data={customer.timelineHistory || []} /></section>
    <section className="contribution-section"><div className="section-header"><div><span className="eyebrow">Model explanation</span><h2>What moved the score</h2></div><span className="explain-key"><i /> raises attention <i /> lowers attention</span></div><div className="contribution-grid"><Contribution title="Strongest signal raising attention" kind="risk" feature={customer.primaryRiskDriver.feature} category={customer.primaryRiskDriver.category} value={customer.primaryRiskDriver.shapValue ?? 0} /><Contribution title="Strongest stabilizing signal" kind="offset" feature={customer.protectiveFactor.feature} category={customer.protectiveFactor.category} value={customer.protectiveFactor.shapValue ?? 0} /></div></section>
    <div className="evidence-actions"><aside className="intervention-callout"><Zap size={18} aria-hidden="true" /><div><strong>Suggested intervention</strong><p>{customer.recommendedIntervention || "No review guidance is available for this customer."}</p></div></aside><aside className="operational-note"><Info size={16} aria-hidden="true" /><p>Model scores are uncalibrated and carry uncertainty. Use this evidence for operational triage with human review—not as an automated decision or proof of customer intent.</p></aside></div>
  </>;
}

function Contribution({ title, kind, feature, category, value }: { title: string; kind: "risk" | "offset"; feature: string; category?: string; value: number }) {
  return <article className={`contribution ${kind}`}><span>{title}</span><small>{category || "Model contribution"}</small><h3>{feature}</h3><div className="contribution-value"><strong>{value >= 0 ? "+" : ""}{value.toFixed(2)}</strong><span className="contribution-track"><span style={{ width: `${Math.min(100, Math.abs(value) * 100)}%` }} /></span></div></article>;
}

function EvaluationEvidence({ metrics }: { metrics: ModelMetrics }) {
  const timingCoverage = metrics.positiveEventUsers ? metrics.correctlyFlaggedUsers / metrics.positiveEventUsers : 0;
  return <>
    <section className="model-masthead"><div className="model-brand"><span className="model-store-icon"><Store size={20} aria-hidden="true" /></span><div><span className="eyebrow">Model quality counter</span><h2>{metrics.modelName}</h2><p>Held-out evaluation · decision-support scoring</p></div></div><div><HelpLabel explanation="The score line used during testing to decide which customers counted as flagged." side="left">Evaluation cutoff</HelpLabel><strong>{metrics.evaluationThreshold.toFixed(4)}</strong><small>Development-derived</small></div><div className="model-status"><i /> Cleared for human review</div></section>
    <section className="quality-shelf" aria-labelledby="quality-shelf-heading"><div className="shelf-sign"><span><ScanLine size={16} aria-hidden="true" /> Inspection shelf</span><strong id="quality-shelf-heading">Held-out model checks</strong><small>Four measures · one operating threshold</small></div><div className="metric-grid" aria-label="Held-out model metrics"><Metric code="01" label="ROC-AUC" help="How consistently the model ranks a customer who later slowed down above one who remained steady. Higher is better." value={metrics.rocAuc.toFixed(3)} note="Discrimination across held-out samples" progress={metrics.rocAuc} /><Metric code="02" label="PR-AUC" help="A combined view of how accurate the flagged group was and how many relevant customers the model found." side="left" value={metrics.prAuc.toFixed(3)} note="Precision-recall ranking summary" progress={metrics.prAuc} /><Metric code="03" label="Precision" help="Of the customers flagged at this cutoff, the share who later matched the evaluated outcome." value={formatRate(metrics.precisionAtEvaluationThreshold)} note={`At evaluation cutoff ${metrics.evaluationThreshold.toFixed(3)}`} progress={metrics.precisionAtEvaluationThreshold} /><Metric code="04" label="Recall" help="Of all customers who later matched the evaluated outcome, the share the model flagged in advance." side="left" value={formatRate(metrics.recallAtEvaluationThreshold)} note={`At evaluation cutoff ${metrics.evaluationThreshold.toFixed(3)}`} progress={metrics.recallAtEvaluationThreshold} /></div></section>
    <section className="threshold-card checkout-counter"><span className="checkout-symbol"><ScanLine size={20} aria-hidden="true" /></span><div><span className="eyebrow">Decision checkout</span><h2>Operational cutoffs encode a tradeoff</h2></div><p>The development-derived cutoff of <strong>{metrics.evaluationThreshold.toFixed(4)}</strong> balances false positives against missed positive events. Scores support triage; they are not customer-level probabilities.</p></section>
    <section className="timing-section"><div><HelpLabel explanation="The typical number of days between the model’s flag and the evaluated customer event.">Median lead time</HelpLabel><strong>{formatDays(metrics.medianLeadTimeDays)} days</strong></div><div><HelpLabel explanation="Customers the model identified before they reached the event used in this evaluation.">Correctly flagged customers</HelpLabel><strong>{metrics.correctlyFlaggedUsers.toLocaleString()}</strong></div><div><HelpLabel explanation="All customers in the test group who eventually reached the event being measured." side="left">Customers with the measured event</HelpLabel><strong>{metrics.positiveEventUsers.toLocaleString()}</strong></div><p><strong>{formatRate(timingCoverage)}</strong> were flagged before the label-defined event threshold.</p></section>
    <section className="data-provenance" aria-labelledby="data-provenance-heading">
      <header><span className="provenance-icon"><Database size={18} aria-hidden="true" /></span><div><span className="eyebrow">Data provenance</span><h2 id="data-provenance-heading">From order history to review signal</h2></div></header>
      <div className="provenance-flow">
        <article><span>01 · Source</span><strong>Instacart Market Basket Analysis, 2017</strong><p>Anonymized grocery order histories released for a Kaggle competition. Customer IDs here are dataset identifiers, not real identities.</p><a href="https://www.kaggle.com/c/basket-analysis/overview" target="_blank" rel="noreferrer">View dataset <ExternalLink size={13} aria-hidden="true" /></a></article>
        <i aria-hidden="true" />
        <article><span>02 · Preparation</span><strong>Shopping-rhythm features</strong><p>We cleaned the order history and summarized changes in purchase gaps, basket size, reorder habits, and history depth.</p></article>
        <i aria-hidden="true" />
        <article><span>03 · Model use</span><strong>Human-review ranking</strong><p>An XGBoost model ranks early signs of slowing and was evaluated on an untouched final customer group. The score is not a probability.</p></article>
      </div>
      <footer>Independent analytical project using publicly released Instacart data. Not affiliated with or endorsed by Instacart.</footer>
    </section>
    <details className="analysis-details methodology"><summary>Methodology and scope limitations<DisclosureToggle /></summary><p>{metrics.methodology}</p><p>The dashboard’s Priority and Watch operational statuses are separate from the development-derived evaluation cutoff.</p></details>
  </>;
}

function Metric({ code, label, help, side = "right", value, note, progress }: { code: string; label: string; help: string; side?: "left" | "right"; value: string; note: string; progress?: number }) {
  return <article className="metric-surface"><span className="metric-ticket">QA-{code}</span><HelpLabel explanation={help} side={side}>{label}</HelpLabel><strong>{value}</strong><small>{note}</small>{progress !== undefined ? <span className="metric-progress"><span style={{ width: `${progress * 100}%` }} /></span> : null}</article>;
}

function HelpLabel({ children, explanation, side = "right" }: { children: string; explanation: string; side?: "left" | "right" }) {
  const tooltipId = useId();
  return <span className={`help-label ${side}`} tabIndex={0} aria-describedby={tooltipId}><span>{children}</span><Info size={13} aria-hidden="true" /><span className="floating-definition" id={tooltipId} role="tooltip">{explanation}</span></span>;
}

function DisclosureToggle() { return <span className="disclosure-toggle" aria-hidden="true"><i /><i /></span>; }

function AnalysisDisclosure() {
  const [open, setOpen] = useState(false);
  return <section className={`analysis-drawer ${open ? "open" : ""}`}><button type="button" aria-expanded={open} aria-controls="analysis-explanation" onClick={() => setOpen(!open)}><span className="analysis-drawer-title"><span className="analysis-drawer-icon"><BookOpen size={15} aria-hidden="true" /></span><span><strong>What is this analysis?</strong><small>{open ? "Close the explanation" : "A plain-language guide to the score"}</small></span></span><span className="analysis-drawer-control"><i /><i /><i /></span></button><div className="analysis-reveal" id="analysis-explanation" aria-hidden={!open}><div><p>We compare each customer’s recent shopping rhythm with their usual pattern. When purchases slow down, the model raises that customer’s retention status so a person can decide whether follow-up is useful.</p><p>The score helps teams decide who to review first. It is not a probability, a diagnosis, or an automated decision.</p></div></div></section>;
}

function LoadingScreen() { return <div className="loading-screen" role="status"><div className="loading-brand"><span className="brand-mark"><img src="/instacart-carrot.svg" alt="" /></span><strong>Purchase Pattern Decay Analysis</strong></div><div className="loading-dots" aria-hidden="true"><i /><i /><i /></div><span>Loading analysis data...</span></div>; }
function InlineLoading({ text }: { text: string }) { return <div className="inline-loading" role="status"><span className="loading-dots" aria-hidden="true"><i /><i /><i /></span>{text}</div>; }
function ErrorState({ text }: { text: string }) { return <div className="error-state" role="alert"><AlertOctagon size={22} aria-hidden="true" /><strong>Something went wrong</strong><span>{text} Refresh the page or check the API connection.</span></div>; }
