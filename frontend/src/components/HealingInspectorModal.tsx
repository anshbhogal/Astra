import React, { useState } from 'react';
import { GitPullRequest, CheckCircle2, RotateCcw, AlertOctagon, X, ArrowRight } from 'lucide-react';

interface HealingCandidate {
  id: string;
  test_case_id: string;
  failure_analysis_id: string;
  original_specification: any;
  proposed_specification: any;
  patch_operations: any[];
  confidence: number;
  status: string;
  rollback_available: boolean;
}

interface HealingInspectorModalProps {
  candidate: HealingCandidate | null;
  isOpen: boolean;
  onClose: () => void;
  onApprove: (candidateId: string) => Promise<void>;
  onRollback: (candidateId: string) => Promise<void>;
}

export const HealingInspectorModal: React.FC<HealingInspectorModalProps> = ({
  candidate,
  isOpen,
  onClose,
  onApprove,
  onRollback,
}) => {
  const [loading, setLoading] = useState(false);

  if (!isOpen || !candidate) return null;

  const handleApprove = async () => {
    setLoading(true);
    try {
      await onApprove(candidate.id);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async () => {
    setLoading(true);
    try {
      await onRollback(candidate.id);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const isApproved = candidate.status === 'APPROVED';

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/75 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
              <GitPullRequest className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-100">Human-in-the-Loop Test Healing Inspector</h3>
              <p className="text-xs text-slate-400">Structural spec patch preview with safety validation gate</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
          {/* Operations Badge */}
          <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-3">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Proposed Patch Operations</h4>
            <div className="space-y-2">
              {candidate.patch_operations.map((op, i) => (
                <div key={i} className="flex items-center justify-between bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80 text-xs">
                  <span className="font-mono font-bold text-purple-400">{op.op_type}</span>
                  <span className="text-slate-400">{op.reason}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Side-by-side spec comparison */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Original Specification</h4>
              <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs text-slate-300 font-mono overflow-x-auto h-56">
                {JSON.stringify(candidate.original_specification, null, 2)}
              </pre>
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-bold text-purple-400 uppercase tracking-wider">Proposed Specification</h4>
              <pre className="bg-purple-950/20 p-4 rounded-xl border border-purple-500/30 text-xs text-purple-200 font-mono overflow-x-auto h-56">
                {JSON.stringify(candidate.proposed_specification, null, 2)}
              </pre>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-800 bg-slate-950/50 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-xs text-slate-400">
            <AlertOctagon className="w-4 h-4 text-amber-400" />
            <span>Patches update test specifications. Target application code is not mutated.</span>
          </div>

          <div className="flex items-center space-x-3">
            {isApproved && candidate.rollback_available && (
              <button
                onClick={handleRollback}
                disabled={loading}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700 flex items-center space-x-2"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Rollback Specification</span>
              </button>
            )}

            {!isApproved && (
              <button
                onClick={handleApprove}
                disabled={loading}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:brightness-110 shadow-lg shadow-purple-500/25 flex items-center space-x-2"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Approve & Apply Patch</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
