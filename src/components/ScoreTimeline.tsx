import { CartesianGrid, Line, LineChart, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Point = { day: number; score: number };

function TimelineTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value?: number }>; label?: number }) {
  if (!active || !payload?.length) return null;
  return <div className="chart-tooltip compact"><strong>Relative day {label}</strong><span>Model score {Number(payload[0].value).toFixed(3)}</span></div>;
}

export default function ScoreTimeline({ data, compact = false }: { data: Point[]; compact?: boolean }) {
  if (!data.length) return <div className="empty">No score history is available.</div>;

  const first = data[0];
  const latest = data[data.length - 1];
  const summary = `Across ${data.length} observed score snapshots, the model score moved from ${first.score.toFixed(3)} to ${latest.score.toFixed(3)}. The latest score is compared with Watch and Priority status cutoffs at 0.45 and 0.70.`;

  return (
    <>
      {!compact ? <p className="chart-summary">{summary}</p> : null}
      <div className={compact ? "chart compact-chart" : "chart"} role="img" aria-label={summary}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={compact ? { top: 8, right: 4, bottom: 2, left: 4 } : { top: 18, right: 24, bottom: 4, left: 0 }}>
            {!compact ? <CartesianGrid vertical={false} stroke="var(--color-chart-grid)" strokeDasharray="3 3" /> : null}
            {!compact ? <XAxis dataKey="day" tickFormatter={(value) => `Day ${value}`} tick={{ fill: "var(--color-text-muted)", fontSize: 11 }} axisLine={{ stroke: "var(--color-border-default)" }} tickLine={false} minTickGap={30} /> : null}
            {!compact ? <YAxis domain={[0, 1]} ticks={[0, 0.25, 0.45, 0.7, 1]} tickFormatter={(value) => Number(value).toFixed(2)} tick={{ fill: "var(--color-text-muted)", fontSize: 11 }} axisLine={false} tickLine={false} width={42} /> : null}
            {!compact ? <Tooltip content={<TimelineTooltip />} /> : null}
            {!compact ? <ReferenceLine y={0.45} stroke="var(--color-chart-threshold-medium)" strokeDasharray="5 5" label={{ value: "Watch 0.45", position: "insideBottomRight", fill: "var(--color-chart-threshold-medium)", fontSize: 11 }} /> : null}
            {!compact ? <ReferenceLine y={0.7} stroke="var(--color-chart-threshold-high)" strokeDasharray="5 5" label={{ value: "Priority 0.70", position: "insideTopRight", fill: "var(--color-chart-threshold-high)", fontSize: 11 }} /> : null}
            <Line type="linear" dataKey="score" stroke="var(--color-chart-primary)" strokeWidth={2} dot={false} activeDot={compact ? false : { r: 4 }} isAnimationActive={false} />
            {!compact ? <ReferenceDot x={latest.day} y={latest.score} r={5} fill="var(--color-chart-primary)" stroke="var(--color-bg-surface)" strokeWidth={2} /> : null}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}
