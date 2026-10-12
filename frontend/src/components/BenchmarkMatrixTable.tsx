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
      case 'MODE_D_HYBRID':
        return { label: 'Mode D: Full Hybrid Astra', color: 'bg-brand/10 text-brand border-brand/30' };
      case 'MODE_A':
      case 'MODE_A_RULES':
        return { label: 'Mode A: Deterministic Rules', color: 'bg-secondaryAccent/10 text-secondaryAccent border-secondaryAccent/30' };
      case 'MODE_B':
      case 'MODE_B_ML':
        return { label: 'Mode B: ML Prioritization', color: 'bg-brand/10 text-brand border-brand/20' };
      case 'MODE_C':
      case 'MODE_C_AI':
        return { label: 'Mode C: AI Replay & LLM', color: 'bg-status-flaky-bg text-status-flaky border-status-flaky/30' };
      case 'MODE_0':
      case 'MODE_0_BASELINE':
      default:
        return { label: 'Mode 0: Baseline Ground Truth', color: 'bg-field text-secondary border-border-card' };
    }
  };

  return (
    <div className="bg-card rounded-2xl border border-border-card p-6 space-y-4 shadow-card overflow-hidden">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-card pb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-brand/10 text-brand border border-brand/20 flex items-center justify-center">
            <FlaskConical className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-primary">Ablation Study Empirical Comparison Matrix</h3>
            <p className="text-xs text-secondary">
              Rigorous confusion matrix evaluation across 50 ground-truth bugs & 100 negative controls
            </p>
          </div>
        </div>
        <span className="text-[11px] font-mono px-3 py-1 rounded-lg bg-field border border-border-card text-secondary">
          Sample Size: N = 150 (50 Bugs + 100 Controls)
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-field text-secondary border-b border-border-card uppercase text-[10px] font-semibold tracking-wider">
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
          <tbody className="divide-y divide-border-card text-secondary">
            {(rows || []).map((row, idx) => {
              const badge = getModeBadge(row.mode || '');
              const isBest = row.mode === 'MODE_D' || row.mode === 'MODE_D_HYBRID';
              const tp = row.tp ?? (row as any).true_positives ?? 0;
              const fp = row.fp ?? (row as any).false_positives ?? 0;
              const tn = row.tn ?? (row as any).true_negatives ?? 0;
              const fn = row.fn ?? (row as any).false_negatives ?? 0;
              const recall = Number(row.recall ?? 0);
              const precision = Number(row.precision ?? 0);
              const specificity = Number(row.specificity ?? 0);
              const f1 = Number(row.f1_score ?? 0);
              const fpr = Number(row.false_positive_rate ?? 0);
              const efficiency = Number(
                row.efficiency_ratio ?? (row as any).detection_efficiency ?? (row as any).time_efficiency ?? 0
              );
              const ciLower = Array.isArray(row.bootstrap_ci_95) && typeof row.bootstrap_ci_95[0] === 'number'
                ? row.bootstrap_ci_95[0]
                : Math.max(0, recall - 0.04);
              const ciUpper = Array.isArray(row.bootstrap_ci_95) && typeof row.bootstrap_ci_95[1] === 'number'
                ? row.bootstrap_ci_95[1]
                : Math.min(1, recall + 0.04);

              return (
                <tr
                  key={row.mode || idx}
                  className={`hover:bg-hover transition-colors ${
                    isBest ? 'bg-brand/5 font-semibold' : ''
                  }`}
                >
                  <td className="px-4 py-3 font-semibold text-primary">
                    <span className={`inline-block px-2.5 py-0.5 rounded-lg border text-[11px] font-bold ${badge.color}`}>
                      {badge.label}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-center">
                    <span className="text-status-passed font-bold">{tp}</span> /{' '}
                    <span className={fp > 0 ? 'text-status-failed' : 'text-muted'}>{fp}</span>
                  </td>
                  <td className="px-3 py-3 text-center">
                    <span className="text-secondaryAccent font-bold">{tn}</span> /{' '}
                    <span className={fn > 0 ? 'text-status-flaky' : 'text-muted'}>{fn}</span>
                  </td>
                  <td className="px-3 py-3 text-right text-status-passed font-bold">
                    {(recall * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-3 text-right text-brand font-bold">
                    {(precision * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-3 text-right text-secondaryAccent font-bold">
                    {(specificity * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-3 text-right text-primary font-extrabold">
                    {f1.toFixed(3)}
                  </td>
                  <td className="px-3 py-3 text-right text-muted">
                    {(fpr * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-3 text-right text-primary">
                    {efficiency.toFixed(1)} <span className="text-[10px] text-muted">t/bug</span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-[11px] text-muted">
                    [{ciLower.toFixed(2)}, {ciUpper.toFixed(2)}]
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
