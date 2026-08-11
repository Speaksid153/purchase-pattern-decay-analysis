import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowUpRight, ChevronLeft, Leaf, Moon, Search, Sun, TrendingDown, TrendingUp, Users } from "lucide-react";
import type { Customer, ModelMetrics, PortfolioSummary, RiskTier } from "./types";

type View = "overview" | "customer" | "evaluation";
type CustomerResponse = { customers: Customer[]; total: number; totalPages: number };
type Insight = { risk_summary?: string; behavioral_interpretation?: string };

const API_TIMEOUT = 10_000;
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

async function api<T>(url: string, timeout = API_TIMEOUT): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    return response.json() as Promise<T>;
  } finally {
    window.clearTimeout(timer);
  }
}

const riskClass = (tier: RiskTier) => `risk ${tier.toLowerCase()}`;
const pct = (value: number) => `${(value * 100).toFixed(2)}%`;

export default function App() {
  const [view, setView] = useState<View>("overview");
  const [theme, setTheme] = useState<"light" | "dark">(() => localStorage.getItem("instacart-analysis-theme") === "dark" ? "dark" : "light");
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerTotal, setCustomerTotal] = useState(0);
  const [listError, setListError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [tier, setTier] = useState<"All" | RiskTier>("All");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Customer | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("instacart-analysis-theme", theme);
  }, [theme]);

  useEffect(() => {
    api<PortfolioSummary>(`${API_BASE}/api/portfolio-summary`)
      .then(setSummary)
      .catch(() => setSummaryError("Portfolio summary is unavailable."));
    api<ModelMetrics>(`${API_BASE}/api/model-metrics`, 12_000)
      .then(setMetrics)
      .catch(() => setMetricsError("Model evaluation is unavailable."));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const delayed = window.setTimeout(() => {
      const params = new URLSearchParams({ page: "1", pageSize: "20", tier, search, scoreRange: "0.00 - 1.00" });
      fetch(`${API_BASE}/api/customers?${params}`, { signal: controller.signal })
        .then((response) => response.ok ? response.json() : Promise.reject())
        .then((data: CustomerResponse) => {
          setCustomers(data.customers || []);
          setCustomerTotal(data.total || 0);
          setListError(null);
        })
        .catch((error) => { if (error.name !== "AbortError") setListError("Customer cohort is unavailable."); });
    }, 180);
    return () => { controller.abort(); window.clearTimeout(delayed); };
  }, [search, tier]);

  useEffect(() => {
    if (!selectedId) return;
    setSelected(null);
    setDetailError(null);
    api<Customer>(`${API_BASE}/api/customers/${selectedId}`)
      .then(setSelected)
      .catch(() => setDetailError("Customer evidence is unavailable."));
  }, [selectedId]);

  const elevated = summary ? summary.highRiskCount + summary.mediumRiskCount : 0;
  const distribution = summary ? [
    { label: "High", value: summary.highRiskCount, color: "#F7636B" },
    { label: "Medium", value: summary.mediumRiskCount, color: "#F26722" },
    { label: "Low", value: summary.lowRiskCount, color: "#009B3A" },
  ] : [];
  const insight = selected?.insightReport as Insight | undefined;
  const detail = (customer: Customer) => { setSelectedId(customer.id); setView("customer"); };

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="wordmark" onClick={() => setView("overview")} aria-label="Customer behavior analysis overview">
          <span className="mark" style={{ backgroundColor: "#003D1F" }}><Leaf size={17} /></span><span>Purchase pattern analysis</span>
        </button>
        <nav aria-label="Analysis views">
          <button className={view === "overview" ? "active" : ""} onClick={() => setView("overview")}>Overview</button>
          <button className={view === "evaluation" ? "active" : ""} onClick={() => setView("evaluation")}>Evaluation</button>
        </nav>
        <button className="icon-button" onClick={() => setTheme(theme === "light" ? "dark" : "light")} aria-label="Toggle color theme">
          {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}
        </button>
      </header>

      {view === "overview" && <main className="page overview">
        <section className="hero">
          <p className="eyebrow">Instacart dataset · behavioral analysis</p>
          <h1>See which customers need a retention review.</h1>
          <p className="lede">This dashboard highlights customers whose current purchase pattern differs from their usual cadence, so teams can focus their review and outreach. This is a dataset analysis, not an official Instacart system.</p>
        </section>

        {summaryError ? <Notice text={summaryError} /> : !summary ? <Loading text="Loading portfolio behavior…" /> : <>
          <section className="method-note overview-context"><p className="eyebrow">How to use this view</p><p>Start with customers in the High and Medium Risk Bands, review the behavior behind each score, then decide whether outreach is appropriate. The model score ranks model evidence; the risk band is an operational segmentation rule applied to that score, not a calibrated probability.</p></section>
          <section className="metric-grid" aria-label="Portfolio risk summary">
            <Metric label="Customers analyzed" value={summary.totalCustomers.toLocaleString()} tone="kale" />
              <Metric label="High + Medium Risk Bands" value={`${summary.elevatedRiskPercentage}%`} tone="carrot" note={`${elevated.toLocaleString()} customers to review`} />
            <Metric label="Most common change" value="Purchase-gap change" tone="mint" note={summary.primaryBehavioralSignal} />
          </section>
          <section className="overview-grid">
            <article className="card distribution-card">
              <div className="section-heading"><div><p className="eyebrow">Risk Bands</p><h2>Customers by churn risk</h2></div><span className="muted">Applied to the latest model score</span></div>
              <div className="distribution-list">{distribution.map((item) => <div className="distribution-row" key={item.label}><span className="dot" style={{ backgroundColor: item.color }} /><span>{item.label} risk</span><strong>{item.value.toLocaleString()}</strong><span className="bar-track"><span style={{ width: `${(item.value / summary.totalCustomers) * 100}%`, backgroundColor: item.color }} /></span></div>)}</div>
              <p className="footnote">Risk bands: High ≥ 0.70 · Medium 0.45–&lt;0.70 · Low &lt;0.45. Operational segmentation rules applied to the model score.</p>
            </article>
            <article className="card observation-card"><p className="eyebrow">What needs attention</p><h2>{elevated.toLocaleString()} customers are in the High or Medium Risk Bands.</h2><p>{summary.primaryBehavioralSignal} is the most common pattern contributing to their model scores. Open a customer record to review the purchase behavior behind that signal.</p><p className="segmentation-note">Risk bands help prioritize operational follow-up; they do not change the model score.</p></article>
          </section>
        </>}

        <section className="cohort-section">
          <div className="section-heading"><div><p className="eyebrow">Customer cohorts</p><h2>Review customers by risk band</h2></div><span className="muted">{customerTotal.toLocaleString()} matching customers</span></div>
          <div className="controls">
            <label className="search"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search customer ID" /></label>
            <div className="segmented" aria-label="Risk band filter">{(["All", "High", "Medium", "Low"] as const).map((item) => <button key={item} onClick={() => setTier(item)} className={tier === item ? "selected" : ""}>{item}</button>)}</div>
          </div>
          {listError ? <Notice text={listError} /> : <div className="table-card"><table><thead><tr><th>Customer</th><th>Model score</th><th>Why flagged</th><th>Latest purchase gap</th><th /></tr></thead><tbody>{customers.map((customer) => <tr key={customer.id}><td><strong>Customer {customer.id}</strong><span>{customer.orderVolume} observed orders</span></td><td><span className={riskClass(customer.riskTier)}>{customer.riskTier}</span><strong className="score">{pct(customer.riskScore)}</strong></td><td>{customer.primaryRiskDriver?.feature}</td><td>{customer.lastPurchaseDays} days <span className="muted">vs {customer.historicAvgGap} average</span></td><td><button className="detail-link" onClick={() => detail(customer)}>View evidence <ArrowUpRight size={15} /></button></td></tr>)}</tbody></table>{!customers.length && <div className="empty">No customer records match this view.</div>}</div>}
        </section>
      </main>}

      {view === "customer" && <main className="page evidence-page">
        <button className="back" onClick={() => setView("overview")}><ChevronLeft size={16} /> Back to cohort</button>
        {detailError ? <Notice text={detailError} /> : !selected ? <Loading text="Loading customer evidence…" /> : <>
          <section className="customer-header"><div><p className="eyebrow">Customer evidence</p><h1>Customer {selected.id}</h1><p>Review the purchase behavior behind this score before deciding whether to reach out.</p></div><div className="risk-panel"><span className={riskClass(selected.riskTier)}>{selected.riskTier}</span><strong>{pct(selected.riskScore)}</strong><small>Model score {selected.riskScore.toFixed(4)}; used for this risk band, not a calibrated probability</small></div></section>
          <section className="evidence-grid">
            <article className="card"><p className="eyebrow">Purchase behavior</p><h2>Gap compared with usual cadence</h2><div className="behavior-stat"><strong>{selected.lastPurchaseDays}</strong><span>days since prior purchase</span></div><p>Historical average gap: <strong>{selected.historicAvgGap} days</strong>. Recorded order history contains {selected.orderVolume} observed orders.</p></article>
            <article className="card"><p className="eyebrow">Retention opportunity</p><h2>Suggested next action</h2><p className="action-text">{selected.recommendedIntervention || "No action recommendation is available."}</p><span className="method-tag">Rule-based suggestion</span></article>
          </section>
          <section className="card chart-card"><div className="section-heading"><div><p className="eyebrow">Score over time</p><h2>How this customer’s model score changed across observed history</h2></div><span className="muted">Relative day</span></div><div className="chart"><ResponsiveContainer width="100%" height={260}><LineChart data={selected.timelineHistory}><CartesianGrid vertical={false} stroke="var(--chart-grid)" /><XAxis dataKey="day" tickFormatter={(value) => `Day ${value}`} stroke="var(--muted)" /><YAxis domain={[0, 1]} tickFormatter={(value) => `${Math.round(value * 100)}%`} stroke="var(--muted)" /><Tooltip formatter={(value) => pct(Number(value))} labelFormatter={(value) => `Relative day ${value}`} /><Line type="monotone" dataKey="score" stroke="#F7636B" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} /></LineChart></ResponsiveContainer></div></section>
          <section className="drivers-grid">
            <article className="card driver-card increase"><p className="eyebrow">Main pattern raising the score</p><h2>{selected.primaryRiskDriver.feature}</h2><strong>Model contribution +{(selected.primaryRiskDriver.shapValue ?? 0).toFixed(2)}</strong><p>This was the strongest model signal pushing the score upward. It does not prove the cause of the customer’s behavior.</p></article>
            <article className="card driver-card offset"><p className="eyebrow">Pattern reducing the score</p><h2>{selected.protectiveFactor.feature}</h2><strong>Model contribution {(selected.protectiveFactor.shapValue ?? 0).toFixed(2)}</strong><p>This model signal partially offsets the score at this snapshot; it does not remove the need for judgment.</p></article>
          </section>
          {insight?.risk_summary && <section className="method-note"><p className="eyebrow">What this risk band means</p><p>{insight.risk_summary}</p></section>}
        </>}
      </main>}

      {view === "evaluation" && <main className="page evaluation-page">
        <section className="hero compact"><p className="eyebrow">Model evidence</p><h1>How well does the behavioral signal rank early risk?</h1><p className="lede">Evaluation is based on the project’s user-level relative-time proxy split. It is not a calendar-time forecast or a guarantee of future customer behavior.</p></section>
        {metricsError ? <Notice text={metricsError} /> : !metrics ? <Loading text="Loading model evaluation…" /> : <>
          <section className="metric-grid evaluation-metrics"><Metric label="Held-out ROC-AUC" value={metrics.rocAuc.toFixed(4)} tone="kale" /><Metric label="Held-out PR-AUC" value={metrics.prAuc.toFixed(4)} tone="leaf" /><Metric label="Precision at evaluation cutoff" value={pct(metrics.precisionAtEvaluationThreshold)} tone="carrot" note={`Recall ${pct(metrics.recallAtEvaluationThreshold)}`} /></section>
          <section className="overview-grid"><article className="card chart-card"><p className="eyebrow">Deployed model evaluation</p><h2>{metrics.modelName}</h2><div className="chart"><ResponsiveContainer width="100%" height={260}><BarChart data={[{ metric: "ROC-AUC", Score: metrics.rocAuc }, { metric: "PR-AUC", Score: metrics.prAuc }, { metric: "Precision", Score: metrics.precisionAtEvaluationThreshold }, { metric: "Recall", Score: metrics.recallAtEvaluationThreshold }]}><CartesianGrid vertical={false} stroke="var(--chart-grid)" /><XAxis dataKey="metric" stroke="var(--muted)" /><YAxis domain={[0, 1]} stroke="var(--muted)" /><Tooltip /><Bar dataKey="Score" fill="#009B3A" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer></div></article><article className="card observation-card"><p className="eyebrow">Evaluation context</p><h2>{metrics.medianLeadTimeDays} days median lead time</h2><p>{metrics.correctlyFlaggedUsers.toLocaleString()} of {metrics.positiveEventUsers.toLocaleString()} positive-event users were flagged before the label-defined threshold. The evaluation cutoff is {metrics.evaluationThreshold.toFixed(4)} and is separate from the dashboard’s operational risk bands.</p><span className="method-tag">Relative-time evaluation</span></article></section>
          <section className="method-note"><p className="eyebrow">Methodology note</p><p>{metrics.methodology}</p></section>
        </>}
      </main>}
    </div>
  );
}

function Metric({ label, value, note, tone }: { label: string; value: string; note?: string; tone: string }) { return <article className={`metric-card ${tone}`}><span>{label}</span><strong>{value}</strong>{note && <small>{note}</small>}</article>; }
function Loading({ text }: { text: string }) { return <div className="state"><span className="loader" />{text}</div>; }
function Notice({ text }: { text: string }) { return <div className="notice">{text}</div>; }
