import React from "react";
import { Timer, TrendingUp, ShieldCheck, Activity } from "lucide-react";

interface RegressionTelemetryCardProps {
  timeAvoidedMs: number;
  reductionPercent: number;
  impactConfidence: number;
  safetyTriggered: boolean;
}

export const RegressionTelemetryCard: React.FC<RegressionTelemetryCardProps> = ({
  timeAvoidedMs,
  reductionPercent,
  impactConfidence,
  safetyTriggered,
}) => {
  const timeAvoidedSec = (timeAvoidedMs / 1000).toFixed(1);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 text-slate-100 shadow-xl">
      <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-3">
        <Activity className="w-5 h-5 text-cyan-400" />
        <h3 className="font-semibold text-base">Regression Optimization Telemetry</h3>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="flex items-center gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800">
          <div className="p-2 bg-cyan-500/10 rounded-lg text-cyan-400">
            <Timer className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xl font-bold font-mono text-cyan-300">{timeAvoidedSec}s</div>
            <div className="text-[11px] text-slate-400">CI Execution Saved</div>
          </div>
        </div>

        <div className="flex items-center gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800">
          <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xl font-bold font-mono text-emerald-400">{(impactConfidence * 100).toFixed(0)}%</div>
            <div className="text-[11px] text-slate-400">Impact Confidence</div>
          </div>
        </div>

        <div className="flex items-center gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800">
          <div className={`p-2 rounded-lg ${safetyTriggered ? "bg-amber-500/10 text-amber-400" : "bg-emerald-500/10 text-emerald-400"}`}>
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className={`text-sm font-bold ${safetyTriggered ? "text-amber-400" : "text-emerald-400"}`}>
              {safetyTriggered ? "Safety Expansion" : "Zero False Negatives"}
            </div>
            <div className="text-[11px] text-slate-400">Safety Axiom Status</div>
          </div>
        </div>
      </div>
    </div>
  );
};
