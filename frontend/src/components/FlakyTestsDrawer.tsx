import React, { useState } from 'react';
import { AlertTriangle, ShieldAlert, CheckCircle, Clock, Zap, X } from 'lucide-react';

interface FlakyTestRecord {
  test_case_id: string;
  flakiness_score: number;
  transition_count: number;
  status: string;
  recommend_quarantine: boolean;
}

interface FlakyTestsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  flakyTests: FlakyTestRecord[];
  onToggleQuarantine: (testCaseId: string, quarantine: boolean) => Promise<void>;
}

export const FlakyTestsDrawer: React.FC<FlakyTestsDrawerProps> = ({
  isOpen,
  onClose,
  flakyTests,
  onToggleQuarantine,
}) => {
  const [loadingId, setLoadingId] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleToggle = async (testCaseId: string, currentStatus: string) => {
    setLoadingId(testCaseId);
    try {
      const isQuarantined = currentStatus === 'QUARANTINED';
      await onToggleQuarantine(testCaseId, !isQuarantined);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end">
      <div className="w-full max-w-2xl bg-slate-900 border-l border-slate-800 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">Flaky Test Quarantine Inspector</h2>
              <p className="text-xs text-slate-400">Automated outcome state transition & non-blocking execution management</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {flakyTests.length === 0 ? (
            <div className="text-center py-12 text-slate-400 border border-dashed border-slate-800 rounded-xl">
              <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto mb-3 opacity-80" />
              <p className="font-medium">No Flaky Tests Detected</p>
              <p className="text-xs text-slate-500 mt-1">All evaluated test cases maintain stable outcome sequences.</p>
            </div>
          ) : (
            flakyTests.map((test) => {
              const isQuarantined = test.status === 'QUARANTINED';
              const isRecommended = test.status === 'RECOMMENDED_QUARANTINE';

              return (
                <div
                  key={test.test_case_id}
                  className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex items-center justify-between hover:border-slate-700 transition-all shadow-sm"
                >
                  <div className="space-y-1 max-w-[65%]">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs text-slate-300 font-semibold truncate max-w-[280px]">
                        ID: {test.test_case_id}
                      </span>
                      {isQuarantined ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20">
                          QUARANTINED (Non-Blocking)
                        </span>
                      ) : isRecommended ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          RECOMMENDED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-400">
                          ACTIVE
                        </span>
                      )}
                    </div>
                    <div className="flex items-center space-x-4 text-xs text-slate-400 pt-1">
                      <span>Flakiness Index: <strong className="text-amber-400">{(test.flakiness_score * 100).toFixed(1)}%</strong></span>
                      <span>Transitions: <strong className="text-slate-200">{test.transition_count}</strong></span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleToggle(test.test_case_id, test.status)}
                    disabled={loadingId === test.test_case_id}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
                      isQuarantined
                        ? 'bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700'
                        : 'bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-bold hover:brightness-110 shadow-lg shadow-amber-500/20'
                    }`}
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>{isQuarantined ? 'Un-Quarantine' : 'Approve Quarantine'}</span>
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
