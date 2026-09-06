import { ArrowUpRight, MousePointer2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { Customer, RiskTier } from "../types";

type GapBand = "On cadence" | "Softening" | "Decaying" | "Critical lapse";
type FlowKey = `${GapBand}-${RiskTier}`;
type HelpKey = GapBand | RiskTier;
type HelpState = { key: HelpKey; side: "source" | "target"; x: number; y: number };

type Props = {
  customers: Customer[];
  filter?: "All" | RiskTier;
  onSelect: (customer: Customer) => void;
};

const SOURCES: Array<{ label: GapBand; range: string; y: number; test: (ratio: number) => boolean }> = [
  { label: "On cadence", range: "< 1.15× usual gap", y: 34, test: (ratio) => ratio < 1.15 },
  { label: "Softening", range: "1.15–1.50×", y: 126, test: (ratio) => ratio >= 1.15 && ratio < 1.5 },
  { label: "Decaying", range: "1.50–2.00×", y: 218, test: (ratio) => ratio >= 1.5 && ratio < 2 },
  { label: "Critical lapse", range: "> 2.00× usual gap", y: 310, test: (ratio) => ratio >= 2 },
];
const TARGETS: Array<{ tier: RiskTier; y: number; range: string }> = [
  { tier: "High", y: 52, range: "Score ≥ 0.70" },
  { tier: "Medium", y: 178, range: "0.45–0.70" },
  { tier: "Low", y: 304, range: "Score < 0.45" },
];
const STATUS_LABELS: Record<RiskTier, string> = { High: "Priority", Medium: "Watch", Low: "Stable" };
const HELP: Record<HelpKey, string> = {
  "On cadence": "Shopping is happening close to this customer’s usual rhythm.",
  Softening: "This customer is taking a little longer than usual to return.",
  Decaying: "The gap between purchases is now clearly longer than their normal pattern.",
  "Critical lapse": "This customer has gone more than twice as long as usual without buying.",
  High: "Review soon—the model found the strongest signs that this customer may not return.",
  Medium: "Keep an eye on this customer; some early signs of slowing are present.",
  Low: "Current shopping behavior remains comparatively steady.",
};

const ratioFor = (customer: Customer) => customer.historicAvgGap > 0 ? customer.lastPurchaseDays / customer.historicAvgGap : 0;

export default function RiskFlow({ customers, filter = "All", onSelect }: Props) {
  const [active, setActive] = useState<FlowKey | null>(null);
  const [hovered, setHovered] = useState<FlowKey | null>(null);
  const [help, setHelp] = useState<HelpState | null>(null);
  useEffect(() => setActive(null), [filter]);

  const flows = useMemo(() => SOURCES.flatMap((source, sourceIndex) => TARGETS.map((target, targetIndex) => {
    const members = customers.filter((customer) => customer.riskTier === target.tier && source.test(ratioFor(customer))).sort((a, b) => b.riskScore - a.riskScore);
    return { key: `${source.label}-${target.tier}` as FlowKey, source, target, sourceIndex, targetIndex, members };
  })), [customers]);
  const maxCount = Math.max(1, ...flows.map((flow) => flow.members.length));
  const selected = flows.find((flow) => flow.key === active) ?? null;
  const sourceTotals = SOURCES.map((source) => customers.filter((customer) => source.test(ratioFor(customer))).length);
  const targetTotals = TARGETS.map((target) => customers.filter((customer) => customer.riskTier === target.tier).length);

  if (!customers.length) return <div className="chart-empty">No customers are available for this view.</div>;

  return (
    <div className="risk-flow">
      <div className="flow-labels" aria-hidden="true"><span>Purchase cadence</span><span>Retention status</span></div>
      <div className="flow-canvas" role="group" aria-label="Interactive flow from purchase cadence change to retention status">
        <svg viewBox="0 0 960 400" preserveAspectRatio="xMidYMid meet">
          {flows.map((flow) => {
            const sourceY = flow.source.y + 29 + (flow.targetIndex - 1) * 13;
            const targetY = flow.target.y + 29 + (flow.sourceIndex - 1.5) * 12;
            const path = `M 188 ${sourceY} C 390 ${sourceY}, 570 ${targetY}, 772 ${targetY}`;
            const isDimmed = (filter !== "All" && filter !== flow.target.tier) || ((active || hovered) && (active || hovered) !== flow.key);
            const isActive = active === flow.key;
            return (
              <g key={flow.key} className={`flow-link ${flow.target.tier.toLowerCase()} ${isDimmed ? "dimmed" : ""} ${isActive ? "active" : ""}`}>
                <path d={path} className="flow-hit" onMouseEnter={() => setHovered(flow.key)} onMouseLeave={() => setHovered(null)} onClick={() => filter === "All" || filter === flow.target.tier ? setActive(active === flow.key ? null : flow.key) : null} tabIndex={filter === "All" || filter === flow.target.tier ? 0 : -1} role="button" aria-label={`${flow.members.length} customers flow from ${flow.source.label} to ${STATUS_LABELS[flow.target.tier]} status`} aria-pressed={isActive} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setActive(active === flow.key ? null : flow.key); } }} />
                <path d={path} className="flow-visible" style={{ strokeWidth: 3 + flow.members.length / maxCount * 19 }} />
                {isActive ? <circle r="4" className="flow-pulse"><animateMotion dur="1.8s" repeatCount="indefinite" path={path} /></circle> : null}
              </g>
            );
          })}

          {SOURCES.map((source, index) => (
            <g className="flow-node source" key={source.label} tabIndex={0} role="img" aria-label={`${source.label}. ${HELP[source.label]}`} onMouseEnter={() => setHelp({ key: source.label, side: "source", x: 20.5, y: (source.y + 29) / 4 })} onMouseLeave={() => setHelp(null)} onFocus={() => setHelp({ key: source.label, side: "source", x: 20.5, y: (source.y + 29) / 4 })} onBlur={() => setHelp(null)}>
              <rect x="18" y={source.y} width="170" height="58" rx="8" />
              <text x="34" y={source.y + 23} className="node-title">{source.label}</text>
              <text x="34" y={source.y + 42} className="node-meta">{source.range}</text>
              <text x="170" y={source.y + 34} textAnchor="end" className="node-count">{sourceTotals[index]}</text>
            </g>
          ))}
          {TARGETS.map((target, index) => (
            <g className={`flow-node target ${target.tier.toLowerCase()}`} key={target.tier} tabIndex={0} role="img" aria-label={`${STATUS_LABELS[target.tier]} status. ${HELP[target.tier]}`} onMouseEnter={() => setHelp({ key: target.tier, side: "target", x: 79.5, y: (target.y + 29) / 4 })} onMouseLeave={() => setHelp(null)} onFocus={() => setHelp({ key: target.tier, side: "target", x: 79.5, y: (target.y + 29) / 4 })} onBlur={() => setHelp(null)}>
              <rect x="772" y={target.y} width="170" height="58" rx="8" />
              <circle cx="790" cy={target.y + 20} r="5" />
              <text x="804" y={target.y + 24} className="node-title">{STATUS_LABELS[target.tier]}</text>
              <text x="790" y={target.y + 44} className="node-meta">{target.range}</text>
              <text x="925" y={target.y + 34} textAnchor="end" className="node-count">{targetTotals[index]}</text>
            </g>
          ))}
        </svg>
        {help ? <div className={`flow-hover-card ${help.side}`} role="tooltip" style={{ left: `${help.x}%`, top: `${help.y}%` }}><strong>{help.key === "High" || help.key === "Medium" || help.key === "Low" ? STATUS_LABELS[help.key] : help.key}</strong><span>{HELP[help.key]}</span></div> : null}
      </div>

      <div className={`flow-focus ${selected ? `open ${selected.target.tier.toLowerCase()}` : ""}`} aria-live="polite">
        {selected ? <><div className="flow-focus-head"><div><span>Selected flow</span><strong>{selected.source.label} → {STATUS_LABELS[selected.target.tier]}</strong></div><p>{selected.members.length} sampled customers</p></div><div className="flow-customers">{selected.members.slice(0, 5).map((customer) => <button type="button" key={customer.id} onClick={() => onSelect(customer)}><span><strong>CUST-{customer.id}</strong><small>{ratioFor(customer).toFixed(2)}× usual gap</small></span><span>{customer.riskScore.toFixed(3)}<ArrowUpRight size={14} aria-hidden="true" /></span></button>)}{!selected.members.length ? <span className="focus-empty">No sampled customers in this flow.</span> : null}</div></> : <div className="flow-hint"><MousePointer2 size={15} aria-hidden="true" /><span>Hover to trace a path. Select a flow to inspect its customers.</span></div>}
      </div>
    </div>
  );
}
