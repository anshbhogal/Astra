import React from "react";
import { Zap, Clock, PieChart, ShieldAlert } from "lucide-react";

interface SelectiveSuiteCardProps {
  totalSuiteCount: number;
  selectedTier1Count: number;
  deferredTier2Count: number;
  reductionPercent: number;
  safetyTriggered: boolean;
  onViewRationale: () => void;
}

export const SelectiveSuiteCard: React.FC<SelectiveSuiteCardProps> = ({
  totalSuiteCount,
  selectedTier1Count,
  deferredTier2Count,
  reductionPercent,
  safetyTriggered,
  onViewRationale,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 text-slate-100 shadow-xl relative overflow-hidden">
      {safetyTriggered && (
        <div className="absolute top-0 right-0 bg-amber-500/20 text-amber-300 text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-bl-lg border-l border-b border-amber-500/30 flex items-center gap-1">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-400" /> Safety Gate Expanded
        </div>
      )}

      <div className="flex items-center gap-2 mb-3">
        <PieChart className="w-5 h-5 text-emerald-400" />
        <h3 className="font-semibold text-base">Tiered Regression Suite Breakdown</h3>
      </div>

      <div className="grid grid-cols-3 gap-4 my-4">
        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-center">
          <span className="text-2xl font-extrabold text-slate-100 font-mono">{totalSuiteCount}</span>
          <p className="text-[11px] text-slate-400 mt-0.5">Total Suite Tests</p>
        </div>

        <div className="bg-emerald-500/10 p-3 rounded-lg border border-emerald-500/20 text-center">
          <span className="text-2xl font-extrabold text-emerald-400 font-mono">{selectedTier1Count}</span>
          <p className="text-[11px] text-emerald-300 mt-0.5 flex items-center justify-center gap-1">
            <Zap className="w-3 h-3 text-emerald-400" /> Tier 1 Targeted
          </p>
        </div>

        <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800 text-center">
          <span className="text-2xl font-extrabold text-slate-400 font-mono">{deferredTier2Count}</span>
          <p className="text-[11px] text-slate-400 mt-0.5 flex items-center justify-center gap-1">
            <Clock className="w-3 h-3" /> Tier 2 Deferred
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-slate-800 pt-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-slate-400">PR Execution Reduction:</span>
          <span className="font-bold text-emerald-400 font-mono text-sm">-{reductionPercent.toFixed(1)}%</span>
        </div>
        <button
          onClick={onViewRationale}
          className="text-indigo-400 hover:text-indigo-300 text-xs font-medium hover:underline transition"
        >
          View Rationale & Drawer →
        </button>
      </div>
    </div>
  );
};
