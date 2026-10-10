import React from 'react';
import { Award, CheckCircle2, XCircle, AlertCircle, TrendingUp, Cpu, Zap, Shield, FlaskConical } from 'lucide-react';

export interface AblationRow {
  mode: string;
  mode_name: string;
  total_bugs: number;
  total_controls: number;
  tp: number;
  fp: number;
  tn: number;
  fn: number;
  recall: number;
  precision: number;
  specificity: number;
  f1_score: number;
  false_positive_rate: number;
  efficiency_ratio: number;
  bootstrap_ci_95: [number, number];
  execution_profile?: string;
  completed_at?: string;
}

interface BenchmarkMatrixTableProps {
  rows: AblationRow[];
}

export const BenchmarkMatrixTable: React.FC<BenchmarkMatrixTableProps> = ({ rows }) => {
  const getModeBadge = (mode: string) => {
    switch (mode) {
      case 'MODE_D':
        return { label: 'Mode D: Full Hybrid Astra', color: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30' };
      case 'MODE_A':
        return { label: 'Mode A: Deterministic Rules', color: 'bg-blue-500/10 text-blue-400 border-blue-500/30' };
      case 'MODE_B':
        return { label: 'Mode B: ML Prioritization', color: 'bg-purple-500/10 text-purple-400 border-purple-500/30' };
      case 'MODE_C':
        return { label: 'Mode C: AI Replay & LLM', color: 'bg-amber-500/10 text-amber-400 border-amber-500/30' };
      case 'MODE_0':
      default:
        return { label: 'Mode 0: Baseline Ground Truth', color: 'bg-slate-800 text-slate-400 border-slate-700' };
    }
  };

  return (
    <div className="glass-card rounded-2xl border border-slate-800 p-6 space-y-4 shadow-xl overflow-hidden">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <FlaskConical className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Ablation Study Empirical Comparison Matrix</h3>
            <p className="text-xs text-slate-400">
              Rigorous confusion matrix evaluation across 50 ground-truth bugs & 100 negative controls
            </p>
          </div>
        </div>
        <span className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-400">
          Sample Size: N = 150 (50 Bugs + 100 Controls)
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
            <tr>
              <th className="px-4 py-3">Ablation Mode</th>
              <th className="px-3 py-3 text-center">TP / FP</th>
              <th className="px-3 py-3 text-center">TN / FN</th>
              <th className="px-3 py-3 text-right">Recall (TPR)</th>
              <th className="px-3 py-3 text-right">Precision</th>
              <th className="px-3 py-3 text-right">Specificity</th>
              <th className="px-3 py-3 text-right">F1 Score</th>
              <th className="px-3 py-3 text-right">FPR</th>
              <th className="px-3 py-3 text-right">Efficiency</th>
              <th className="px-4 py-3 text-right">95% Bootstrap CI</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {rows.map((row) => {
              const badge = getModeBadge(row.mode);
              const isBest = row.mode === 'MODE_D';
              return (
                <tr
                  key={row.mode}
                  className={`hover:bg-slate-800/40 transition-colors ${
                    isBest ? 'bg-indigo-950/20 font-bold' : ''
                  }`}
                >
                  <td className="px-4 py-3 font-semibold text-white">
                    <span className={`inline-block px-2 py-0.5 rounded-lg border text-[11px] ${badge.color}`}>
                      {badge.label}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-center">
                    <span className="text-emerald-400 font-bold">{row.tp}</span> /{' '}
                    <span className={row.fp > 0 ? 'text-rose-400' : 'text-slate-500'}>{row.fp}</span>
                  </td>
                  <td className="px-3 py-3 text-center">
                    <span className="text-teal-400 font-bold">{row.tn}</span> /{' '}
                    <span className={row.fn > 0 ? 'text-amber-400' : 'text-slate-500'}>{row.fn}</span>
                  </td>
                  <td className="px-3 py-3 text-right text-emerald-400 font-bold">
                    {(row.recall * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-3 text-right text-indigo-400 font-bold">
                    {(row.precision * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-3 text-right text-teal-400 font-bold">
                    {(row.specificity * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-3 text-right text-white font-extrabold">
                    {row.f1_score.toFixed(3)}
                  </td>
                  <td className="px-3 py-3 text-right text-slate-400">
                    {(row.false_positive_rate * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-3 text-right text-slate-300">
                    {row.efficiency_ratio.toFixed(1)} <span className="text-[10px] text-slate-500">t/bug</span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-indigo-300 text-[11px]">
                    [{row.bootstrap_ci_95[0].toFixed(3)}, {row.bootstrap_ci_95[1].toFixed(3)}]
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="pt-2 border-t border-slate-800/60 text-[11px] text-slate-500 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
        <span>* Metrics computed via empirical multi-trial execution without predetermined assumptions.</span>
        <span>Bootstrap CI computed via 1,000 iterations at α = 0.05.</span>
      </div>
    </div>
  );
};
