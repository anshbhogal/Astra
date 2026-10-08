import React from 'react';
import { AlertTriangle, CheckCircle, ArrowRight } from 'lucide-react';

export interface JsonDiffItem {
  path: str;
  expected: any;
  actual: any;
  diff_type: string;
  message: string;
}

interface JsonDiffViewerProps {
  diffItems: JsonDiffItem[];
}

export const JsonDiffViewer: React.FC<JsonDiffViewerProps> = ({ diffItems }) => {
  if (!diffItems || diffItems.length === 0) {
    return (
      <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
        <CheckCircle className="w-4 h-4 text-emerald-400" />
        No structural JSON schema or HTTP header deltas detected.
      </div>
    );
  }

  const getDiffBadgeColor = (diffType: string) => {
    switch (diffType) {
      case 'MISSING_KEY':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'TYPE_MISMATCH':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      case 'ARRAY_LENGTH_MISMATCH':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      default:
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
        <span className="flex items-center gap-1.5 text-rose-400">
          <AlertTriangle className="w-4 h-4" />
          Structural Response Deltas ({diffItems.length})
        </span>
        <span className="text-slate-500 font-mono text-[11px]">JSONPath Mismatches</span>
      </div>

      <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
        {diffItems.map((item, idx) => (
          <div
            key={idx}
            className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2 text-xs font-mono"
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-indigo-400">{item.path}</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getDiffBadgeColor(item.diff_type)}`}>
                {item.diff_type}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-slate-800/60">
              <div className="p-2 rounded bg-emerald-950/20 border border-emerald-500/20 text-emerald-300">
                <span className="text-[10px] uppercase tracking-wider text-emerald-500 block mb-0.5">Expected</span>
                {JSON.stringify(item.expected) || 'null'}
              </div>
              <div className="p-2 rounded bg-rose-950/20 border border-rose-500/20 text-rose-300">
                <span className="text-[10px] uppercase tracking-wider text-rose-500 block mb-0.5">Actual</span>
                {JSON.stringify(item.actual) || 'null'}
              </div>
            </div>

            {item.message && (
              <p className="text-[11px] text-slate-400 font-sans italic pt-0.5">{item.message}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
