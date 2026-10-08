import React from 'react';
import { X, ShieldAlert, Cpu, GitCommit, FileText, CheckCircle2, HelpCircle } from 'lucide-react';
import { JsonDiffViewer } from './JsonDiffViewer';

interface RootCauseInspectorModalProps {
  analysis: any;
  onClose: () => void;
}

export const RootCauseInspectorModal: React.FC<RootCauseInspectorModalProps> = ({
  analysis,
  onClose,
}) => {
  if (!analysis) return null;

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case 'SERVER_CRASH':
      case 'DATABASE_ERROR':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      case 'AUTHENTICATION_FAILURE':
      case 'AUTHORIZATION_FAILURE':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'CONTRACT_VIOLATION':
      case 'REQUEST_VALIDATION_DEFECT':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      default:
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      <div className="w-full max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                Root-Cause Diagnostic Inspector
                <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${getCategoryColor(analysis.category)}`}>
                  {analysis.category}
                </span>
              </h2>
              <p className="text-xs text-slate-400 font-mono">Analysis ID: {analysis.id || analysis.analysis_id}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Multi-Metric Confidence Dashboard */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1">
              <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">Classification Confidence</span>
              <div className="text-lg font-bold text-indigo-400 font-mono">
                {Math.round((analysis.classification_confidence || 1.0) * 100)}%
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1">
              <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">Attribution Confidence</span>
              <div className="text-lg font-bold text-cyan-400 font-mono">
                {Math.round((analysis.attribution_confidence || 1.0) * 100)}%
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1">
              <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">Root-Cause Confidence</span>
              <div className="text-lg font-bold text-emerald-400 font-mono">
                {Math.round((analysis.root_cause_confidence || 0.0) * 100)}%
              </div>
            </div>
          </div>

          {/* Root-Cause Candidate Hypotheses */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              Root-Cause Hypotheses & Remediation
            </h3>
            {analysis.root_cause_candidates && analysis.root_cause_candidates.length > 0 ? (
              analysis.root_cause_candidates.map((cand: any, idx: number) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-emerald-300 flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      Candidate #{idx + 1}: {cand.reasoning_type}
                    </span>
                    <span className="text-xs font-mono font-bold text-emerald-400">
                      {Math.round((cand.confidence || 1.0) * 100)}% Confidence
                    </span>
                  </div>
                  <p className="text-xs text-slate-200">{cand.description}</p>
                  {cand.suggested_remediation && (
                    <div className="p-2.5 rounded-lg bg-indigo-950/30 border border-indigo-500/20 text-xs text-indigo-300">
                      <span className="font-semibold text-indigo-400">Suggested Remediation:</span> {cand.suggested_remediation}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="p-3 text-xs text-slate-400 bg-slate-950/40 rounded-xl border border-slate-800">
                Insufficient empirical evidence available.
              </div>
            )}
          </div>

          {/* Fault Location Ranking & PKG Nodes */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <FileText className="w-4 h-4 text-cyan-400" />
              Ranked Candidate Fault Locations (AST & PKG)
            </h3>
            {analysis.fault_locations && analysis.fault_locations.length > 0 ? (
              <div className="space-y-2">
                {analysis.fault_locations.map((loc: any, idx: number) => (
                  <div key={idx} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between text-xs font-mono">
                    <div className="space-y-0.5">
                      <div className="font-bold text-slate-200">
                        {loc.file_path}:{loc.line_number}
                        {loc.function_name && <span className="text-cyan-400 font-normal ml-2">in {loc.function_name}()</span>}
                      </div>
                      <div className="text-[11px] text-slate-400 flex items-center gap-2 font-sans">
                        <span>Reason: {loc.reason}</span>
                        {loc.pkg_node_id && <span className="text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded text-[10px] font-mono border border-indigo-500/20">PKG Graph Node</span>}
                      </div>
                    </div>
                    <span className="text-xs font-bold text-cyan-400 font-mono">{Math.round((loc.confidence || 1.0) * 100)}%</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-3 text-xs text-slate-400 bg-slate-950/40 rounded-xl border border-slate-800">
                No project source stack frames identified.
              </div>
            )}
          </div>

          {/* Structural Diff Viewer */}
          <JsonDiffViewer diffItems={analysis.diff_items || []} />
        </div>
      </div>
    </div>
  );
};
