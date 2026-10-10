import React, { useState } from 'react';
import { TrendingUp } from 'lucide-react';

export interface TrendPoint {
  date: string;
  pass_rate: number;
  total_runs: number;
  total_tests: number;
  mean_duration_ms: number;
}

interface MetricsTrendChartProps {
  trendData: TrendPoint[];
  timeRange: string;
  onTimeRangeChange: (range: string) => void;
}

export const MetricsTrendChart: React.FC<MetricsTrendChartProps> = ({
  trendData,
  timeRange,
  onTimeRangeChange,
}) => {
  const [hoveredPoint, setHoveredPoint] = useState<TrendPoint | null>(null);

  // Fallback points if no historical data yet
  const displayPoints = trendData && trendData.length > 0 ? trendData : [
    { date: 'Day 1', pass_rate: 85.0, total_runs: 1, total_tests: 20, mean_duration_ms: 120 },
    { date: 'Day 2', pass_rate: 88.5, total_runs: 2, total_tests: 40, mean_duration_ms: 110 },
    { date: 'Day 3', pass_rate: 92.0, total_runs: 2, total_tests: 45, mean_duration_ms: 95 },
    { date: 'Day 4', pass_rate: 90.0, total_runs: 3, total_tests: 50, mean_duration_ms: 105 },
    { date: 'Day 5', pass_rate: 94.5, total_runs: 4, total_tests: 65, mean_duration_ms: 85 },
  ];

  const width = 640;
  const height = 180;
  const padding = 32;

  // Scale calculations
  const minRate = 60;
  const maxRate = 100;
  const xStep = displayPoints.length > 1 ? (width - padding * 2) / (displayPoints.length - 1) : 0;

  const pointsString = displayPoints
    .map((pt, i) => {
      const x = padding + i * xStep;
      const normalizedRate = Math.max(minRate, Math.min(maxRate, pt.pass_rate));
      const y = height - padding - ((normalizedRate - minRate) / (maxRate - minRate)) * (height - padding * 2);
      return `${x},${y}`;
    })
    .join(' ');

  const areaString = displayPoints.length > 1
    ? `${pointsString} ${padding + (displayPoints.length - 1) * xStep},${height - padding} ${padding},${height - padding}`
    : '';

  return (
    <div className="bg-card rounded-2xl p-6 border border-border-card space-y-4 shadow-card">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-card pb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand/10 text-brand border border-brand/20 flex items-center justify-center">
            <TrendingUp className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-primary">Quality & Pass Rate Trajectory</h3>
            <p className="text-xs text-secondary">Rolling regression pass rate and execution volume</p>
          </div>
        </div>

        {/* Time Window Buttons */}
        <div className="flex items-center gap-1.5 bg-field p-1 rounded-xl border border-border-card">
          {[
            { id: '7d', label: '7 Days' },
            { id: '30d', label: '30 Days' },
            { id: '90d', label: '90 Days' },
            { id: 'all', label: 'All Time' },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => onTimeRangeChange(t.id)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                timeRange === t.id
                  ? 'bg-brand text-on-brand shadow-sm'
                  : 'text-secondary hover:text-primary'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* SVG Time-Series Chart */}
      <div className="relative w-full overflow-hidden bg-field rounded-xl p-3 border border-border-card">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-48 overflow-visible select-none"
        >
          <defs>
            <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--brand)" stopOpacity="0.25" />
              <stop offset="100%" stopColor="var(--brand)" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="var(--brand)" />
              <stop offset="100%" stopColor="var(--secondary)" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[100, 90, 80, 70].map((rate) => {
            const y = height - padding - ((rate - minRate) / (maxRate - minRate)) * (height - padding * 2);
            return (
              <g key={rate}>
                <line
                  x1={padding}
                  y1={y}
                  x2={width - padding}
                  y2={y}
                  stroke="var(--border-card)"
                  strokeDasharray="4 4"
                  strokeWidth="1"
                />
                <text
                  x={padding - 6}
                  y={y + 3}
                  textAnchor="end"
                  className="text-[9px] fill-[var(--text-muted)] font-mono"
                >
                  {rate}%
                </text>
              </g>
            );
          })}

          {/* Area Fill */}
          {areaString && (
            <polygon points={areaString} fill="url(#areaGradient)" />
          )}

          {/* Line Path */}
          {pointsString && (
            <polyline
              points={pointsString}
              fill="none"
              stroke="url(#lineGradient)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Interactive Plot Points */}
          {displayPoints.map((pt, i) => {
            const x = padding + i * xStep;
            const normalizedRate = Math.max(minRate, Math.min(maxRate, pt.pass_rate));
            const y = height - padding - ((normalizedRate - minRate) / (maxRate - minRate)) * (height - padding * 2);
            return (
              <g
                key={i}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredPoint(pt)}
                onMouseLeave={() => setHoveredPoint(null)}
              >
                <circle
                  cx={x}
                  cy={y}
                  r="4.5"
                  className="fill-[var(--brand)] stroke-[var(--bg-card)] stroke-2 hover:r-6 transition-all"
                />
                <text
                  x={x}
                  y={height - 10}
                  textAnchor="middle"
                  className="text-[9px] fill-[var(--text-muted)] font-mono"
                >
                  {pt.date.slice(5) || pt.date}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Floating Tooltip on bg-card with shadow */}
        {hoveredPoint && (
          <div className="absolute top-4 right-4 bg-card border border-border-card rounded-xl p-3 shadow-card text-xs space-y-1 pointer-events-none">
            <div className="font-bold text-primary flex items-center justify-between gap-4">
              <span>{hoveredPoint.date}</span>
              <span className="text-status-passed font-mono">{hoveredPoint.pass_rate.toFixed(1)}% Pass</span>
            </div>
            <div className="text-[11px] text-muted flex items-center justify-between gap-4 font-mono">
              <span>Runs: {hoveredPoint.total_runs}</span>
              <span>Tests: {hoveredPoint.total_tests}</span>
              <span>Latency: {hoveredPoint.mean_duration_ms}ms</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
