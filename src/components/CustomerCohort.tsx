import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, RotateCcw, ScanLine, Search, SearchX, SlidersHorizontal, Store } from "lucide-react";
import { useRef } from "react";
import type { Customer, CustomerFilter } from "../types";
import RiskBadge from "./RiskBadge";

type Props = {
  customers: Customer[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  loading: boolean;
  error: string | null;
  search: string;
  filter: CustomerFilter;
  sortBy: CustomerSort;
  sortDirection: SortDirection;
  onSearch: (value: string) => void;
  onFilter: (value: CustomerFilter) => void;
  onSortBy: (value: CustomerSort) => void;
  onSortDirection: (value: SortDirection) => void;
  onReset: () => void;
  onPage: (value: number) => void;
  onSelect: (customer: Customer) => void;
};

export type CustomerSort = "score" | "status" | "latestGap" | "historicGap" | "orders" | "customerId";
export type SortDirection = "asc" | "desc";

const FILTERS: { value: CustomerFilter; label: string }[] = [
  { value: "All", label: "All" },
  { value: "High", label: "Priority" },
  { value: "Medium", label: "Watch" },
  { value: "Low", label: "Stable" },
];

const SORTS: { value: CustomerSort; label: string }[] = [
  { value: "score", label: "Score" },
  { value: "status", label: "Status" },
  { value: "latestGap", label: "Latest gap" },
  { value: "historicGap", label: "Usual gap" },
  { value: "orders", label: "Orders" },
  { value: "customerId", label: "Customer ID" },
];

const STATUS_LABELS: Record<Exclude<CustomerFilter, "All" | "Review">, string> = { High: "priority", Medium: "watch", Low: "stable" };

const score = (value: number) => value.toFixed(3);
const number = (value: number) => value.toLocaleString();
const days = (value: number) => Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1);

export default function CustomerCohort({ customers, total, page, pageSize, totalPages, loading, error, search, filter, sortBy, sortDirection, onSearch, onFilter, onSortBy, onSortDirection, onReset, onPage, onSelect }: Props) {
  const resultsRef = useRef<HTMLDivElement>(null);
  const start = total ? (page - 1) * pageSize + 1 : 0;
  const end = Math.min(page * pageSize, total);
  const pageHigh = customers.filter((customer) => customer.riskTier === "High").length;
  const pageMedium = customers.filter((customer) => customer.riskTier === "Medium").length;
  const pageLow = customers.filter((customer) => customer.riskTier === "Low").length;
  const isDefaultView = !search && filter === "All" && sortBy === "score" && sortDirection === "desc" && page === 1;
  const movePage = (nextPage: number) => {
    onPage(nextPage);
    window.requestAnimationFrame(() => {
      resultsRef.current?.scrollTo({ top: 0, behavior: "smooth" });
      document.getElementById("customer-list-heading")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  return (
    <section className="customer-directory" aria-labelledby="customer-list-heading">
      <div className="working-set">
        <div className="working-set-count"><span className="floor-label"><Store size={14} aria-hidden="true" /> Review floor</span><strong>{number(total)}</strong><small>{filter === "All" ? "customers across all retention statuses" : `${filter === "Review" ? "review" : STATUS_LABELS[filter]} customers`} {search ? `matching “${search}”` : ""}</small></div>
        <PageMix high={pageHigh} medium={pageMedium} low={pageLow} />
      </div>
      <div className="customer-controls">
        <div className="tab-group" aria-label="Retention status filter">
          {FILTERS.map((item) => (
            <button key={item.value} type="button" aria-pressed={filter === item.value} onClick={() => onFilter(item.value)} className={filter === item.value ? "selected" : ""}>
              {item.label}
            </button>
          ))}
        </div>
        <label className="search-field">
          <Search size={16} aria-hidden="true" />
          <span className="sr-only">Search customer ID</span>
          <input aria-label="Search customer ID" value={search} onChange={(event) => onSearch(event.target.value)} placeholder="Search customer ID" inputMode="numeric" />
        </label>
      </div>

      <div className="sort-shelf" aria-label="Customer sorting controls">
        <span className="sort-label"><SlidersHorizontal size={14} aria-hidden="true" /> Sort by</span>
        <div className="sort-options" role="group" aria-label="Sort criterion">
          {SORTS.map((item) => <button key={item.value} type="button" aria-pressed={sortBy === item.value} className={sortBy === item.value ? "selected" : ""} onClick={() => onSortBy(item.value)}>{item.label}</button>)}
        </div>
        <button className="sort-direction" type="button" onClick={() => onSortDirection(sortDirection === "desc" ? "asc" : "desc")} aria-label={`Sort ${sortDirection === "desc" ? "low to high" : "high to low"}`}>
          {sortDirection === "desc" ? <ArrowDown size={15} aria-hidden="true" /> : <ArrowUp size={15} aria-hidden="true" />}
          {sortDirection === "desc" ? "High to low" : "Low to high"}
        </button>
      </div>

      <div className="table-heading">
        <div><span className="shelf-kicker"><ScanLine size={14} aria-hidden="true" /> Ranked review shelf</span><h2 id="customer-list-heading">Customer inventory</h2><p>Sorted by {SORTS.find((item) => item.value === sortBy)?.label.toLowerCase()} · {sortDirection === "desc" ? "high to low" : "low to high"}.</p></div>
        <div className="table-meta"><span>{number(start)}–{number(end)} of {number(total)}</span><button type="button" onClick={onReset} disabled={isDefaultView || loading}><RotateCcw size={14} aria-hidden="true" /> Reset table</button></div>
      </div>

      {error ? <div className="notice" role="alert">{error}</div> : (
        <>
          <div className="customer-table-wrap desktop-results" aria-busy={loading} ref={resultsRef}>
            <table className="customer-table">
              <thead><tr><th>Customer ID</th><th>Retention Status</th><th className="numeric">Model Score</th><th className="numeric">Latest Gap</th><th className="numeric">Historical Avg Gap</th><th>Evidence Review</th></tr></thead>
              <tbody>
                {customers.map((customer, index) => (
                  <tr key={customer.id} className={`risk-row ${customer.riskTier.toLowerCase()}`}>
                    <td><div className="customer-identity"><span className="shelf-position">{String(start + index).padStart(2, "0")}</span><span><strong>CUST-{customer.id}</strong><small>{number(customer.orderVolume)} observed orders</small></span></div></td>
                    <td><RiskBadge tier={customer.riskTier} /></td>
                    <td className="numeric score-cell"><strong>{score(customer.riskScore)}</strong><span className="score-track"><span style={{ width: `${customer.riskScore * 100}%` }} /></span></td>
                    <td className="numeric">{days(customer.lastPurchaseDays)} days</td>
                    <td className="numeric">{days(customer.historicAvgGap)} days</td>
                    <td><button className="grid-action" type="button" onClick={() => onSelect(customer)} aria-label={`Review evidence for customer ${customer.id}`}>Open evidence <ChevronRight size={15} aria-hidden="true" /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {loading && !customers.length ? <div className="inline-loading">Loading customers…</div> : null}
            {!loading && !customers.length ? <EmptyState /> : null}
          </div>

          <div className="mobile-results" aria-busy={loading}>
            {customers.map((customer) => (
              <article className="customer-result" key={customer.id}>
                <div className="customer-result-head"><div><strong>CUST-{customer.id}</strong><small>{number(customer.orderVolume)} observed orders</small></div><RiskBadge tier={customer.riskTier} /></div>
                <dl><div><dt>Model Score</dt><dd>{score(customer.riskScore)}</dd></div><div><dt>Latest Gap</dt><dd>{days(customer.lastPurchaseDays)} days</dd></div><div><dt>Historical Avg</dt><dd>{days(customer.historicAvgGap)} days</dd></div></dl>
                <button className="primary-action" type="button" onClick={() => onSelect(customer)}>Review evidence <ChevronRight size={16} aria-hidden="true" /></button>
              </article>
            ))}
            {loading && !customers.length ? <div className="inline-loading">Loading customers…</div> : null}
            {!loading && !customers.length ? <EmptyState /> : null}
          </div>

          {totalPages > 1 ? (
            <nav className="pagination" aria-label="Customer result pages">
              <button type="button" onClick={() => movePage(Math.max(1, page - 1))} disabled={page === 1 || loading}><ChevronLeft size={15} aria-hidden="true" /> Previous</button>
              <span>Page {number(page)} of {number(totalPages)}</span>
              <button type="button" onClick={() => movePage(Math.min(totalPages, page + 1))} disabled={page === totalPages || loading}>Next <ChevronRight size={15} aria-hidden="true" /></button>
            </nav>
          ) : null}
        </>
      )}
    </section>
  );
}

function PageMix({ high, medium, low }: { high: number; medium: number; low: number }) {
  const total = high + medium + low;
  let offset = 0;
  const segments = [
    { key: "high", label: "Priority", count: high },
    { key: "medium", label: "Watch", count: medium },
    { key: "low", label: "Stable", count: low },
  ].map((item) => {
    const percent = total ? item.count / total * 100 : 0;
    const segment = { ...item, percent, offset };
    offset += percent;
    return segment;
  });

  return <div className="page-mix-radial"><div className="mix-ring" role="img" aria-label={`Current page: ${high} priority, ${medium} watch, ${low} stable customers`}><svg viewBox="0 0 64 64" aria-hidden="true"><circle className="mix-ring-base" cx="32" cy="32" r="24" pathLength="100" />{segments.filter((segment) => segment.count > 0).map((segment) => <circle key={segment.key} className={`mix-ring-segment ${segment.key}`} cx="32" cy="32" r="24" pathLength="100" strokeDasharray={`${segment.percent} ${100 - segment.percent}`} strokeDashoffset={-segment.offset} />)}</svg><span><strong>{total}</strong><small>shown</small></span></div><div className="mix-summary"><span>Current page mix</span><ul>{segments.map((segment) => <li key={segment.key}><i className={segment.key} /><span>{segment.label}</span><strong>{segment.count}</strong></li>)}</ul></div></div>;
}

function EmptyState() {
  return <div className="empty-state"><SearchX size={24} aria-hidden="true" /><strong>No customers found</strong><span>Try adjusting your filters or search criteria.</span></div>;
}
