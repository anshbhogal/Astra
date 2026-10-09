import React, { useState, useEffect } from "react";
import { GitCompare, Play, AlertCircle, RefreshCw } from "lucide-react";
import { ChangeImpactGraph } from "./ChangeImpactGraph";
import { SelectiveSuiteCard } from "./SelectiveSuiteCard";
import { RegressionTelemetryCard } from "./RegressionTelemetryCard";
import { SelectionReasonDrawer } from "./SelectionReasonDrawer";

interface RegressionDashboardTabProps {
  projectId: string;
}

export const RegressionDashboardTab: React.FC<RegressionDashboardTabProps> = ({ projectId }) => {
  const [baseCommit, setBaseCommit] = useState("main~1");
  const [targetCommit, setTargetCommit] = useState("HEAD");
  const [diffText, setDiffText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisData, setAnalysisData] = useState<any | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleRunAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/v1/projects/${projectId}/regression/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_commit: baseCommit,
          target_commit: targetCommit,
          diff_text: diffText || undefined,
          async_mode: false,
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Regression impact analysis failed.");
      }

      const data = await response.json();
      setAnalysisData(data);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Commit Trigger Form */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 text-slate-100 shadow-xl">
        <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-bold">Phase 8: Selective Regression & AST Change Impact</h2>
          </div>
          <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full font-mono">
            Zero False Negatives Core
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">Base Commit / Ref</label>
            <input
              type="text"
              value={baseCommit}
              onChange={(e) => setBaseCommit(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
              placeholder="e.g. main~1 or SHA"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">Target Commit / Ref</label>
            <input
              type="text"
              value={targetCommit}
              onChange={(e) => setTargetCommit(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
              placeholder="e.g. HEAD or feature-branch"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={handleRunAnalysis}
              disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs px-4 py-2.5 rounded-lg flex items-center justify-center gap-2 transition shadow-lg shadow-indigo-600/20"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Analyzing AST & Reachability...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" /> Run Selective Analysis
                </>
              )}
            </button>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-400 mb-1">Optional Unified Diff Text (Paste Git Diff)</label>
          <textarea
            rows={3}
            value={diffText}
            onChange={(e) => setDiffText(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs font-mono text-slate-300 focus:outline-none focus:border-indigo-500"
            placeholder="diff --git a/app/services/user.py b/app/services/user.py..."
          />
        </div>

        {error && (
          <div className="mt-4 bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded-lg p-3 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Analysis Results Display */}
      {analysisData && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <SelectiveSuiteCard
              totalSuiteCount={analysisData.summary?.total_suite_tests || 0}
              selectedTier1Count={analysisData.summary?.selected_tier1_count || 0}
              deferredTier2Count={analysisData.summary?.deferred_tier2_count || 0}
              reductionPercent={analysisData.summary?.test_reduction_percent || 0}
              safetyTriggered={analysisData.summary?.safety_expansion_triggered || false}
              onViewRationale={() => setDrawerOpen(true)}
            />

            <RegressionTelemetryCard
              timeAvoidedMs={analysisData.summary?.estimated_time_avoided_ms || 0}
              reductionPercent={analysisData.summary?.test_reduction_percent || 0}
              impactConfidence={analysisData.summary?.impact_confidence || 1.0}
              safetyTriggered={analysisData.summary?.safety_expansion_triggered || false}
            />
          </div>

          <ChangeImpactGraph
            manifests={analysisData.manifests || []}
            impactedEndpoints={analysisData.impacted_endpoints || []}
          />

          <SelectionReasonDrawer
            isOpen={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            tier1Tests={analysisData.tier1_tests || []}
            tier2Tests={analysisData.tier2_tests || []}
            warnings={analysisData.warnings || []}
          />
        </>
      )}
    </div>
  );
};
