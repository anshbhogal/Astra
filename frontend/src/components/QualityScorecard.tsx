import React from 'react';
import { Award, ShieldCheck, AlertTriangle, Activity, Cpu, Clock, CheckCircle2, XCircle } from 'lucide-react';

interface QualityScorecardProps {
  qualityScore: number;
  testPassRate: number;
  defectDensity: number;
  flakyRatio: number;
  requirementCoverage: number;
  totalRuns: number;
  totalTests: number;
  testsAvoided?: number;
  timeSavedMs?: number;
  ciGatePassRate?: number;
}

export const QualityScorecard: React.FC<QualityScorecardProps> = ({
  qualityScore = 0,
  testPassRate = 0,
  defectDensity = 0,
  flakyRatio = 0,
  requirementCoverage = 0,
  totalRuns = 0,
  totalTests = 0,
  testsAvoided = 0,
  timeSavedMs = 0,
  ciGatePassRate = 100,
}) => {
  const getScoreColor = (score: number = 0) => {
    const s = Number(score ?? 0);
    if (s >= 90) return { text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', label: 'EXCELLENT' };
    if (s >= 75) return { text: 'text-indigo-400', bg: 'bg-indigo-500/10', border: 'border-indigo-500/30', label: 'GOOD' };
    if (s >= 60) return { text: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30', label: 'MODERATE' };
    return { text: 'text-rose-400', bg: 'bg-rose-500/10', border: 'border-rose-500/30', label: 'NEEDS ATTENTION' };
  };

  const badge = getScoreColor(qualityScore);

  return (
    <div className="space-y-4">
      {/* Primary Scorecard Hero Banner */}
      <div className={`p-6 rounded-2xl border ${badge.border} ${badge.bg} backdrop-blur-sm shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6`}>
        <div className="flex items-center gap-5">
          <div className="relative w-24 h-24 rounded-2xl bg-slate-950/80 border border-slate-800 flex flex-col items-center justify-center shrink-0 shadow-inner">
            <span className={`text-3xl font-black font-mono tracking-tight ${badge.text}`}>
              {Number(qualityScore ?? 0).toFixed(1)}
            </span>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-0.5">/ 100</span>
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-extrabold tracking-wider border ${badge.border} ${badge.text}`}>
                {badge.label} QUALITY
              </span>
              <span className="text-xs text-slate-400 font-medium">Weighted Engineering Scorecard</span>
            </div>
            <h3 className="text-lg font-bold text-white">Repository Software Quality Rating</h3>
            <p className="text-xs text-slate-400 max-w-xl leading-relaxed">
              Synthesized from test pass rates, defect density per endpoint, flaky test quarantine ratios, requirement coverage, and CI/CD quality gate enforcement.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 shrink-0 w-full md:w-auto">
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-center">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Test Runs</span>
            <span className="text-base font-bold text-white font-mono mt-0.5 block">{totalRuns}</span>
          </div>
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-center">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Tests Executed</span>
            <span className="text-base font-bold text-indigo-400 font-mono mt-0.5 block">{totalTests}</span>
          </div>
        </div>
      </div>

      {/* Six Component KPI Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Metric 1: Pass Rate */}
        <div className="glass-card rounded-xl p-4 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Test Pass Rate</span>
            <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <p className="text-2xl font-extrabold text-white font-mono">{Number(testPassRate ?? 0).toFixed(1)}%</p>
            <span className="text-[11px] text-slate-400 font-medium">Target: ≥ 95%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500" style={{ width: `${Math.min(100, Number(testPassRate ?? 0))}%` }} />
          </div>
        </div>

        {/* Metric 2: Defect Density */}
        <div className="glass-card rounded-xl p-4 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Defect Density</span>
            <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <p className="text-2xl font-extrabold text-white font-mono">{Number(defectDensity ?? 0).toFixed(2)}</p>
            <span className="text-[11px] text-slate-400 font-medium">Bugs / Endpoint</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-1.5 rounded-full transition-all duration-500 ${Number(defectDensity ?? 0) > 1.0 ? 'bg-rose-500' : Number(defectDensity ?? 0) > 0.3 ? 'bg-amber-500' : 'bg-emerald-500'}`}
              style={{ width: `${Math.min(100, Number(defectDensity ?? 0) * 50)}%` }}
            />
          </div>
        </div>

        {/* Metric 3: Flakiness Ratio */}
        <div className="glass-card rounded-xl p-4 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Flakiness Ratio</span>
            <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <p className="text-2xl font-extrabold text-white font-mono">{Number(flakyRatio ?? 0).toFixed(1)}%</p>
            <span className="text-[11px] text-slate-400 font-medium">Quarantine Ratio</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-1.5 rounded-full transition-all duration-500 ${Number(flakyRatio ?? 0) > 10 ? 'bg-rose-500' : 'bg-indigo-500'}`}
              style={{ width: `${Math.min(100, Number(flakyRatio ?? 0) * 5)}%` }}
            />
          </div>
        </div>

        {/* Metric 4: Requirement Coverage */}
        <div className="glass-card rounded-xl p-4 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">API & Spec Coverage</span>
            <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <p className="text-2xl font-extrabold text-white font-mono">{Number(requirementCoverage ?? 0).toFixed(1)}%</p>
            <span className="text-[11px] text-slate-400 font-medium">Discovered Specs</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div className="bg-blue-500 h-1.5 rounded-full transition-all duration-500" style={{ width: `${Math.min(100, Number(requirementCoverage ?? 0))}%` }} />
          </div>
        </div>

        {/* Metric 5: Regression Efficiency */}
        <div className="glass-card rounded-xl p-4 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Selective Execution</span>
            <div className="p-1.5 rounded-lg bg-violet-500/10 text-violet-400 border border-violet-500/20">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <p className="text-2xl font-extrabold text-white font-mono">{testsAvoided ?? 0}</p>
            <span className="text-[11px] text-slate-400 font-medium">Tests Avoided</span>
          </div>
          <p className="text-[11px] text-slate-400">
            Saved approx <span className="text-emerald-400 font-mono font-bold">{(Number(timeSavedMs ?? 0) / 1000).toFixed(1)}s</span> CI pipeline latency
          </p>
        </div>

        {/* Metric 6: CI Quality Gate */}
        <div className="glass-card rounded-xl p-4 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">CI Gate Compliance</span>
            <div className="p-1.5 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <p className="text-2xl font-extrabold text-white font-mono">{Number(ciGatePassRate ?? 100).toFixed(1)}%</p>
            <span className="text-[11px] text-slate-400 font-medium">GitHub PR Checks</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div className="bg-teal-500 h-1.5 rounded-full transition-all duration-500" style={{ width: `${Math.min(100, Number(ciGatePassRate ?? 100))}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
};
