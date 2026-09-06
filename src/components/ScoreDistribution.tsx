import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Customer } from "../types";

function DistributionTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: { label: string; count: number } }> }) {
  const bin = payload?.[0]?.payload;
  if (!active || !bin) return null;
  return <div className="chart-tooltip compact"><strong>{bin.label}</strong><span>{bin.count} sampled customers</span></div>;
}

export default function ScoreDistribution({ customers }: { customers: Customer[] }) {
  const bins = useMemo(() => Array.from({ length: 10 }, (_, index) => {
    const start = index / 10;
    const end = (index + 1) / 10;
    return {
      midpoint: start + 0.05,
      label: `${start.toFixed(1)}–${end.toFixed(1)}`,
      count: customers.filter((customer) => customer.riskScore >= start && (index === 9 ? customer.riskScore <= end : customer.riskScore < end)).length,
    };
  }), [customers]);

  return (
    <div className="landscape-chart distribution-chart" role="img" aria-label="Distribution of sampled customer model scores from zero to one">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={bins} margin={{ top: 18, right: 20, bottom: 28, left: 4 }}>
          <CartesianGrid vertical={false} stroke="var(--color-chart-grid)" strokeDasharray="3 3" />
          <XAxis type="number" dataKey="midpoint" domain={[0, 1]} ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]} tickFormatter={(value) => Number(value).toFixed(1)} tick={{ fill: "var(--color-text-muted)", fontSize: 11 }} axisLine={{ stroke: "var(--color-border-default)" }} tickLine={false} label={{ value: "Model score", position: "insideBottom", offset: -18, fill: "var(--color-text-muted)", fontSize: 11 }} />
          <YAxis allowDecimals={false} tick={{ fill: "var(--color-text-muted)", fontSize: 11 }} axisLine={false} tickLine={false} width={42} />
          <Tooltip cursor={{ fill: "var(--color-bg-subtle)" }} content={<DistributionTooltip />} />
          <ReferenceLine x={0.45} stroke="var(--color-chart-threshold-medium)" strokeDasharray="5 5" label={{ value: "0.45", position: "insideTopLeft", fill: "var(--color-chart-threshold-medium)", fontSize: 11 }} />
          <ReferenceLine x={0.7} stroke="var(--color-chart-threshold-high)" strokeDasharray="5 5" label={{ value: "0.70", position: "insideTopLeft", fill: "var(--color-chart-threshold-high)", fontSize: 11 }} />
          <Bar dataKey="count" name="Customers" fill="var(--color-chart-primary)" radius={[3, 3, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
