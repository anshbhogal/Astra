import React from 'react';
import { Zap, Clock, ShieldAlert, BarChart3 } from 'lucide-react';

interface PrioritizedItem {
  test_case_id: string;
  failure_probability: number;
  execution_cost_ms: number;
  severity_weight: number;
  priority_score: number;
  rank_order: number;
  strategy: string;
  rationale: string;
}

interface PriorityHeatmapCardProps {
  items: PrioritizedItem[];
  strategy: string;
  onStrategyChange: (strategy: string) => void;
}

export const PriorityHeatmapCard: React.FC<PriorityHeatmapCardProps> = ({
  items,
  strategy,
  onStrategyChange,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-100">ML Test Execution Plan</h3>
            <p className="text-xs text-slate-400">XGBoost failure probability & cost-aware priority ranking</p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {['BALANCED', 'RISK_FIRST', 'FAST_FEEDBACK', 'SEVERITY_FIRST'].map((s) => (
            <button
              key={s}
              onClick={() => onStrategyChange(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                strategy === s
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700'
              }`}
            >
              {s.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Test List */}
      <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
        {items.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs">
            No prioritization data available. Train ML model or run test suites.
          </div>
        ) : (
          items.map((item) => {
            const probPct = (item.failure_probability * 100).toFixed(1);
            return (
              <div
                key={item.test_case_id}
                className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3.5 flex items-center justify-between hover:border-slate-700 transition-all"
              >
                <div className="flex items-center space-x-3 max-w-[60%]">
                  <span className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center font-mono text-xs font-bold text-indigo-400">
                    #{item.rank_order}
                  </span>
                  <div>
                    <p className="font-mono text-xs text-slate-200 font-semibold truncate max-w-[320px]">
                      {item.test_case_id}
                    </p>
                    <p className="text-[11px] text-slate-400 truncate max-w-[360px] mt-0.5">
                      {item.rationale}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-6 text-xs">
                  <div className="text-right">
                    <span className="block text-[10px] text-slate-500 uppercase tracking-wider font-semibold">P(Fail)</span>
                    <span className="font-bold text-amber-400">{probPct}%</span>
                  </div>
                  <div className="text-right">
                    <span className="block text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Latency</span>
                    <span className="font-mono text-slate-300">{item.execution_cost_ms.toFixed(0)}ms</span>
                  </div>
                  <div className="text-right">
                    <span className="block text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Score</span>
                    <span className="font-bold text-indigo-400">{item.priority_score.toFixed(3)}</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
