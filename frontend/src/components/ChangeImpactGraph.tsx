import React from "react";
import { GitCommit, Layers, ArrowRight, ShieldCheck, CheckCircle } from "lucide-react";

interface ImpactedEndpoint {
  endpoint_id: string;
  path: string;
  method: string;
  impact_distance: number;
  confidence_score: number;
  impact_type: string;
  impact_path_trace: string[];
}

interface ChangeManifest {
  old_path?: string;
  new_path: string;
  change_type: string;
  change_category: string;
  modified_symbols: string[];
}

interface ChangeImpactGraphProps {
  manifests: ChangeManifest[];
  impactedEndpoints: ImpactedEndpoint[];
}

export const ChangeImpactGraph: React.FC<ChangeImpactGraphProps> = ({
  manifests,
  impactedEndpoints,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 text-slate-100 shadow-xl">
      <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <GitCommit className="w-5 h-5 text-indigo-400" />
          <h3 className="font-semibold text-lg">Git Diff & Reachability Impact Graph</h3>
        </div>
        <span className="text-xs bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2.5 py-1 rounded-full font-mono">
          Zero LLM Core
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Code Change Manifests */}
        <div className="space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-cyan-400" /> Modified Files & AST Symbols ({manifests.length})
          </h4>
          <div className="space-y-2 max-h-64 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-slate-700">
            {manifests.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No changed files detected.</p>
            ) : (
              manifests.map((m, idx) => (
                <div key={idx} className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 text-xs">
                  <div className="flex items-center justify-between font-mono text-cyan-300 mb-1">
                    <span className="truncate max-w-[200px]">{m.new_path}</span>
                    <span className="px-1.5 py-0.5 text-[10px] bg-slate-800 rounded text-slate-300">
                      {m.change_type}
                    </span>
                  </div>
                  {m.modified_symbols.length > 0 && (
                    <div className="mt-2 text-[11px] text-slate-400 space-y-0.5">
                      <span className="text-slate-500">Modified Symbols:</span>
                      {m.modified_symbols.map((sym, sIdx) => (
                        <div key={sIdx} className="font-mono text-slate-300 truncate bg-slate-900/80 px-2 py-0.5 rounded">
                          {sym}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Reachable Impacted Endpoints */}
        <div className="space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <ArrowRight className="w-4 h-4 text-emerald-400" /> Reachable API Endpoints ({impactedEndpoints.length})
          </h4>
          <div className="space-y-2 max-h-64 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-slate-700">
            {impactedEndpoints.length === 0 ? (
              <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4 text-center">
                <CheckCircle className="w-6 h-6 text-emerald-400 mx-auto mb-1" />
                <p className="text-xs text-emerald-300 font-medium">No API Endpoints Impacted</p>
                <p className="text-[11px] text-emerald-400/70 mt-0.5">Changes isolated from public API surface.</p>
              </div>
            ) : (
              impactedEndpoints.map((ep, idx) => (
                <div key={idx} className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] ${
                        ep.method === "POST" ? "bg-emerald-500/20 text-emerald-400" :
                        ep.method === "DELETE" ? "bg-rose-500/20 text-rose-400" :
                        ep.method === "PUT" ? "bg-amber-500/20 text-amber-400" : "bg-sky-500/20 text-sky-400"
                      }`}>
                        {ep.method}
                      </span>
                      <span className="font-mono text-slate-200">{ep.path}</span>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">
                      dist: {ep.impact_distance} | conf: {(ep.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  {ep.impact_path_trace.length > 0 && (
                    <div className="mt-1 text-[10px] font-mono text-slate-500 truncate">
                      Trace: {ep.impact_path_trace.join(" → ")}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
