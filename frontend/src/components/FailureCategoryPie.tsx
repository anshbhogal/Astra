import React from 'react';
import { ShieldAlert } from 'lucide-react';

export interface FailureCategoryItem {
  category: string;
  count: number;
  color: string;
}

interface FailureCategoryPieProps {
  categories: FailureCategoryItem[];
  totalFailures: number;
}

const CHART_SERIES = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
  'var(--chart-6)',
];

export const FailureCategoryPie: React.FC<FailureCategoryPieProps> = ({
  categories,
  totalFailures,
}) => {
  const displayItems = categories && categories.length > 0 ? categories.map((cat, idx) => ({
    ...cat,
    color: cat.color || CHART_SERIES[idx % CHART_SERIES.length],
  })) : [
    { category: 'APPLICATION_BUG', count: 12, color: CHART_SERIES[0] },
    { category: 'BUSINESS_LOGIC_DEFECT', count: 6, color: CHART_SERIES[1] },
    { category: 'TEST_SCRIPT_ISSUE', count: 3, color: CHART_SERIES[2] },
    { category: 'SCHEMA_VIOLATION', count: 2, color: CHART_SERIES[3] },
    { category: 'ENVIRONMENT_ISSUE', count: 1, color: CHART_SERIES[4] },
  ];

  const sumCount = Math.max(1, displayItems.reduce((acc, curr) => acc + curr.count, 0));

  // Compute donut slices
  let cumulativeAngle = 0;
  const radius = 54;
  const cx = 80;
  const cy = 80;

  const slices = displayItems.map((item) => {
    const sliceAngle = (item.count / sumCount) * 360;
    const startAngle = cumulativeAngle;
    const endAngle = cumulativeAngle + sliceAngle;
    cumulativeAngle = endAngle;

    const startRad = (startAngle - 90) * (Math.PI / 180);
    const endRad = (endAngle - 90) * (Math.PI / 180);

    const x1 = cx + radius * Math.cos(startRad);
    const y1 = cy + radius * Math.sin(startRad);
    const x2 = cx + radius * Math.cos(endRad);
    const y2 = cy + radius * Math.sin(endRad);

    const largeArc = sliceAngle > 180 ? 1 : 0;
    const pathData = sliceAngle >= 359.9
      ? `M ${cx} ${cy - radius} A ${radius} ${radius} 0 1 1 ${cx - 0.01} ${cy - radius}`
      : `M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`;

    return {
      ...item,
      pathData,
      percent: ((item.count / sumCount) * 100).toFixed(1),
    };
  });

  return (
    <div className="bg-card rounded-2xl p-6 border border-border-card space-y-4 shadow-card">
      <div className="flex items-center gap-3 border-b border-border-card pb-4">
        <div className="w-8 h-8 rounded-lg bg-status-failed-bg text-status-failed border border-status-failed/30 flex items-center justify-center">
          <ShieldAlert className="w-4 h-4" />
        </div>
        <div>
          <h3 className="text-base font-bold text-primary">Failure Root Cause Categorization</h3>
          <p className="text-xs text-secondary">Semantic classification distribution</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center pt-2">
        {/* SVG Donut Visualizer */}
        <div className="relative flex items-center justify-center">
          <svg viewBox="0 0 160 160" className="w-44 h-44 drop-shadow-sm">
            {slices.map((slice, i) => (
              <path
                key={i}
                d={slice.pathData}
                fill={slice.color}
                className="opacity-95 hover:opacity-100 transition-opacity cursor-pointer stroke-[var(--bg-card)] stroke-2"
              />
            ))}
            {/* Center Cutout for Donut Shape */}
            <circle cx={cx} cy={cy} r="34" className="fill-[var(--bg-card)] stroke-[var(--border-card)] stroke-1" />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-xl font-bold text-primary font-mono">{sumCount}</span>
            <span className="text-[9px] uppercase tracking-wider font-semibold text-muted">Defects</span>
          </div>
        </div>

        {/* Legend & Breakdown List */}
        <div className="space-y-2 max-h-52 overflow-y-auto pr-2">
          {displayItems.map((item, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2 rounded-lg bg-field border border-border-card text-xs hover:border-brand transition-colors"
            >
              <div className="flex items-center gap-2 truncate">
                <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                <span className="text-primary font-medium truncate">{item.category.replace(/_/g, ' ')}</span>
              </div>
              <span className="font-mono text-secondary font-semibold shrink-0 ml-2">
                {item.count} <span className="text-[10px] text-muted">({((item.count / sumCount) * 100).toFixed(0)}%)</span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
