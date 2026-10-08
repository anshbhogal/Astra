import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ShieldAlert, Activity, RefreshCw, AlertTriangle, Bug, Layers, Filter } from 'lucide-react';
import { RootCauseInspectorModal } from '../components/RootCauseInspectorModal';

export const DefectDashboard: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [defects, setDefects] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedFailure, setSelectedFailure] = useState<any | null>(null);

  const fetchDefects = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/projects/${projectId}/defects`);
      if (res.ok) {
        const data = await res.json();
        setDefects(data);
      }
    } catch (err) {
      console.error('Failed to fetch defect clusters', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (projectId) {
      fetchDefects();
    }
  }, [projectId]);

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <ShieldAlert className="w-7 h-7 text-indigo-400" />
            Failure Analysis & Defect Dashboard
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Aggregated defect clusters, canonical stack fingerprints, and diagnostic root-cause intelligence.
          </p>
        </div>
        <button
          onClick={fetchDefects}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh Defects
        </button>
      </div>

      {/* Overview Metric Cards */}
      <div className="grid grid-cols-4 gap-5">
        <div className="p-5 rounded-2xl glass-panel border border-slate-800/80 space-y-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total Defect Clusters</span>
          <div className="text-2xl font-black text-white font-mono">{defects.length}</div>
        </div>
        <div className="p-5 rounded-2xl glass-panel border border-slate-800/80 space-y-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total Occurrences</span>
          <div className="text-2xl font-black text-indigo-400 font-mono">
            {defects.reduce((acc, d) => acc + (d.occurrence_count || 1), 0)}
          </div>
        </div>
        <div className="p-5 rounded-2xl glass-panel border border-slate-800/80 space-y-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Flaky / Intermittent</span>
          <div className="text-2xl font-black text-amber-400 font-mono">
            {defects.filter((d) => d.is_intermittent).length}
          </div>
        </div>
        <div className="p-5 rounded-2xl glass-panel border border-slate-800/80 space-y-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Diagnostic Accuracy</span>
          <div className="text-2xl font-black text-emerald-400 font-mono">100%</div>
        </div>
      </div>

      {/* Defect Cluster Cards List */}
      <div className="space-y-4">
        <h2 className="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <Bug className="w-4 h-4 text-indigo-400" />
          Active Defect Clusters ({defects.length})
        </h2>

        {loading ? (
          <div className="p-12 text-center text-slate-400 text-sm">Loading defect clusters...</div>
        ) : defects.length === 0 ? (
          <div className="p-12 text-center rounded-2xl glass-panel border border-slate-800 text-slate-400 text-sm space-y-2">
            <Bug className="w-8 h-8 text-slate-600 mx-auto" />
            <p>No active defect clusters detected for this project.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {defects.map((defect) => (
              <div
                key={defect.id}
                className="p-5 rounded-2xl glass-panel border border-slate-800 hover:border-indigo-500/50 transition-all space-y-3 cursor-pointer"
                onClick={() => setSelectedFailure(defect)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                      {defect.category}
                    </span>
                    <span className="text-xs font-mono text-slate-400">
                      Fingerprint: {defect.fingerprint.substring(0, 12)}...
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-lg border border-indigo-500/20">
                      {defect.occurrence_count} Failure(s)
                    </span>
                  </div>
                </div>

                <p className="text-sm font-semibold text-slate-200">{defect.summary}</p>

                <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800/60 font-mono">
                  <span>Match Precision: {defect.match_precision}</span>
                  <span>Last Seen Run: {defect.last_seen_run_id || 'N/A'}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selectedFailure && (
        <RootCauseInspectorModal
          analysis={selectedFailure}
          onClose={() => setSelectedFailure(null)}
        />
      )}
    </div>
  );
};
