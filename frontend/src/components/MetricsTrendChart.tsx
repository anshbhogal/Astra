import React, { useState } from 'react';
import { TrendingUp, Calendar, Activity, BarChart2 } from 'lucide-react';

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
    <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Quality & Pass Rate Trajectory</h3>
            <p className="text-xs text-slate-400">Rolling regression pass rate and execution volume</p>
          </div>
        </div>

        {/* Time Window Buttons */}
        <div className="flex items-center gap-1.5 bg-slate-950/80 p-1 rounded-xl border border-slate-800">
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
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* SVG Time-Series Chart */}
      <div className="relative w-full overflow-hidden bg-slate-950/50 rounded-xl p-3 border border-slate-800/60">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-48 overflow-visible select-none"
        >
          <defs>
            <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#818cf8" />
              <stop offset="100%" stopColor="#38bdf8" />
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
                  stroke="#334155"
                  strokeDasharray="4 4"
                  strokeWidth="0.8"
                />
                <text
                  x={padding - 6}
                  y={y + 3}
                  textAnchor="end"
                  className="text-[9px] fill-slate-500 font-mono"
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
                  className="fill-indigo-500 stroke-slate-900 stroke-2 hover:r-6 transition-all"
                />
                <text
                  x={x}
                  y={height - 10}
                  textAnchor="middle"
                  className="text-[9px] fill-slate-400 font-mono"
                >
                  {pt.date.slice(5) || pt.date}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Floating Tooltip */}
        {hoveredPoint && (
          <div className="absolute top-4 right-4 bg-slate-900 border border-indigo-500/40 rounded-xl p-3 shadow-2xl backdrop-blur-md pointer-events-none text-xs space-y-1">
            <div className="font-bold text-white flex items-center justify-between gap-4">
              <span>{hoveredPoint.date}</span>
              <span className="text-emerald-400 font-mono">{hoveredPoint.pass_rate.toFixed(1)}% Pass</span>
            </div>
            <div className="text-[11px] text-slate-400 flex items-center justify-between gap-4 font-mono">
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
