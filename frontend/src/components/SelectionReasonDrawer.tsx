import React from "react";
import { X, CheckCircle, Clock, Info, ShieldAlert } from "lucide-react";

interface TestDetail {
  test_case_id: string;
  name: string;
  tier: string;
  selection_reason: string;
  confidence: number;
  estimated_duration_ms: number;
}

interface SelectionReasonDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  tier1Tests: TestDetail[];
  tier2Tests: TestDetail[];
  warnings: string[];
}

export const SelectionReasonDrawer: React.FC<SelectionReasonDrawerProps> = ({
  isOpen,
  onClose,
  tier1Tests,
  tier2Tests,
  warnings,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-slate-900 border-l border-slate-800 h-full overflow-y-auto p-6 text-slate-100 flex flex-col justify-between shadow-2xl">
        <div>
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Info className="w-5 h-5 text-indigo-400" /> Selective Partition Rationale
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">Machine-readable explainability log for Tier 1 vs Tier 2 allocation.</p>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {warnings.length > 0 && (
            <div className="mt-4 bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-xs text-amber-300">
              <div className="font-semibold flex items-center gap-1.5 mb-1">
                <ShieldAlert className="w-4 h-4 text-amber-400" /> Safety Gate Warnings:
              </div>
              <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                {warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Tier 1 Targeted Section */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-2 mb-3">
              <CheckCircle className="w-4 h-4" /> Tier 1 Targeted Tests ({tier1Tests.length})
            </h3>
            <div className="space-y-2">
              {tier1Tests.map((t, idx) => (
                <div key={idx} className="bg-slate-950 border border-emerald-500/20 rounded-lg p-3 text-xs">
                  <div className="flex items-center justify-between font-mono font-medium text-emerald-300 mb-1">
                    <span>{t.name}</span>
                    <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded">
                      {(t.confidence * 100).toFixed(0)}% conf
                    </span>
                  </div>
                  <p className="text-slate-300 text-[11px] font-sans">{t.selection_reason}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Tier 2 Deferred Section */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2 mb-3">
              <Clock className="w-4 h-4 text-slate-400" /> Tier 2 Deferred Full Suite ({tier2Tests.length})
            </h3>
            <div className="space-y-2">
              {tier2Tests.map((t, idx) => (
                <div key={idx} className="bg-slate-950/60 border border-slate-800 rounded-lg p-3 text-xs">
                  <div className="flex items-center justify-between font-mono font-medium text-slate-400 mb-1">
                    <span>{t.name}</span>
                    <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded">
                      Deferred
                    </span>
                  </div>
                  <p className="text-slate-400 text-[11px] font-sans">{t.selection_reason}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-800 mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition"
          >
            Close Drawer
          </button>
        </div>
      </div>
    </div>
  );
};
