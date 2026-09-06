import { AlertTriangle, CheckCircle2, Minus } from "lucide-react";
import type { RiskTier } from "../types";

const LABELS: Record<RiskTier, string> = { High: "Priority", Medium: "Watch", Low: "Stable" };

export default function RiskBadge({ tier, suffix = "" }: { tier: RiskTier; suffix?: string }) {
  const Icon = tier === "High" ? AlertTriangle : tier === "Medium" ? Minus : CheckCircle2;
  return (
    <span className={`risk-badge ${tier.toLowerCase()}`}>
      <Icon size={11} strokeWidth={2.4} aria-hidden="true" />
      {LABELS[tier]}{suffix ? ` ${suffix}` : ""}
    </span>
  );
}
