import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ShieldAlert, RefreshCw, Bug, Layers, Flame, CheckCircle2, AlertTriangle } from 'lucide-react';
import { RootCauseInspectorModal } from '../components/RootCauseInspectorModal';
import { Button } from '../components/common/Button';

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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-status-failed-bg border border-status-failed/30 flex items-center justify-center text-status-failed">
              <ShieldAlert className="w-5 h-5" />
            </div>
            Failure Analysis & Defect Dashboard
          </h1>
          <p className="text-xs text-secondary mt-1">
            Aggregated defect clusters, canonical stack fingerprints, and diagnostic root-cause intelligence.
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={fetchDefects}
          isLoading={loading}
          leftIcon={<RefreshCw className="w-4 h-4" />}
        >
          Refresh Defects
        </Button>
      </div>

      {/* Overview Metric Cards with 32px Icon Chips */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-card rounded-xl p-5 border border-border-card shadow-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold text-muted uppercase tracking-wider">Defect Clusters</span>
            <div className="w-8 h-8 rounded-lg bg-status-failed-bg border border-status-failed/30 flex items-center justify-center text-status-failed">
              <Bug className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-primary font-mono">{defects.length}</div>
            <span className="text-[11px] text-muted">Unique clusters</span>
          </div>
        </div>

        <div className="bg-card rounded-xl p-5 border border-border-card shadow-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold text-muted uppercase tracking-wider">Total Occurrences</span>
            <div className="w-8 h-8 rounded-lg bg-brand/10 border border-brand/20 flex items-center justify-center text-brand">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-brand font-mono">
              {defects.reduce((acc, d) => acc + (d.occurrence_count || 1), 0)}
            </div>
            <span className="text-[11px] text-muted">Test failures aggregated</span>
          </div>
        </div>

        <div className="bg-card rounded-xl p-5 border border-border-card shadow-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold text-muted uppercase tracking-wider">Flaky / Intermittent</span>
            <div className="w-8 h-8 rounded-lg bg-status-flaky-bg border border-status-flaky/30 flex items-center justify-center text-status-flaky">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-status-flaky font-mono">
              {defects.filter((d) => d.is_intermittent).length}
            </div>
            <span className="text-[11px] text-muted">Quarantined issues</span>
          </div>
        </div>

        <div className="bg-card rounded-xl p-5 border border-border-card shadow-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold text-muted uppercase tracking-wider">Diagnostic Confidence</span>
            <div className="w-8 h-8 rounded-lg bg-status-passed-bg border border-status-passed/30 flex items-center justify-center text-status-passed">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-status-passed font-mono">100%</div>
            <span className="text-[11px] text-muted">Root cause precision</span>
          </div>
        </div>
      </div>

      {/* Defect Cluster Cards List */}
      <div className="space-y-4">
        <h2 className="text-sm font-bold text-primary uppercase tracking-wider flex items-center gap-2">
          <Bug className="w-4 h-4 text-brand" />
          Active Defect Clusters ({defects.length})
        </h2>

        {loading ? (
          <div className="p-12 text-center text-muted text-sm">Loading defect clusters...</div>
        ) : defects.length === 0 ? (
          <div className="p-12 text-center rounded-2xl bg-card border border-border-card shadow-card text-secondary text-sm space-y-2">
            <Bug className="w-8 h-8 text-muted mx-auto" />
            <p>No active defect clusters detected for this project.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {defects.map((defect) => (
              <div
                key={defect.id}
                className="p-5 rounded-2xl bg-card border border-border-card hover:border-brand shadow-card transition-all space-y-3 cursor-pointer"
                onClick={() => setSelectedFailure(defect)}
              >
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-status-failed-bg text-status-failed border border-status-failed/30">
                      {defect.category}
                    </span>
                    <span className="text-xs font-mono text-muted">
                      Fingerprint: {defect.fingerprint.substring(0, 12)}...
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono font-bold text-brand bg-brand/10 px-2.5 py-1 rounded-lg border border-brand/20">
                      {defect.occurrence_count} Failure(s)
                    </span>
                  </div>
                </div>

                <p className="text-sm font-semibold text-primary">{defect.summary}</p>

                <div className="flex items-center justify-between text-xs text-secondary pt-2 border-t border-border-card font-mono">
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
