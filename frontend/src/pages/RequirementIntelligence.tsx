import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { FileCheck, Upload, Settings, RefreshCw, Layers, ShieldCheck, Cpu, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import { RequirementUploadModal } from '../components/RequirementUploadModal';
import { RequirementTraceabilityTable } from '../components/RequirementTraceabilityTable';
import { LLMConfigDrawer } from '../components/LLMConfigDrawer';
import { Button } from '../components/common/Button';

export const RequirementIntelligence: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [aiConfig, setAiConfig] = useState({ provider: 'gemini', model: 'gemini-1.5-pro', enable_ai: true });

  const fetchTraceability = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await api.get(`/projects/${projectId}/requirements/traceability`);
      setItems(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTraceability();
  }, [projectId]);

  const verifiedCount = items.filter((i) => i.coverage_status === 'VERIFIED').length;
  const coveragePct = items.length ? Math.round((verifiedCount / items.length) * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-brand/10 text-brand border border-brand/20 flex items-center justify-center">
              <FileCheck className="w-5 h-5" />
            </div>
            <span>Requirement Intelligence & Traceability</span>
          </h1>
          <p className="text-xs text-secondary mt-1">
            NLP specification extraction, multi-signal endpoint mapping, and AI boundary edge-case coverage matrix.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <Button
            variant="secondary"
            onClick={() => setIsConfigOpen(true)}
            leftIcon={<Settings className="w-4 h-4 text-brand" />}
          >
            AI Settings ({aiConfig.provider})
          </Button>
          <Button
            variant="primary"
            onClick={() => setIsUploadOpen(true)}
            leftIcon={<Upload className="w-4 h-4" />}
          >
            Upload Specification
          </Button>
        </div>
      </div>

      {/* Metrics Banner with 32px Icon Chips */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-card border border-border-card p-5 rounded-xl shadow-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted font-semibold uppercase tracking-wider">Total Requirements</span>
            <div className="w-8 h-8 rounded-lg bg-brand/10 border border-brand/20 flex items-center justify-center text-brand">
              <FileCheck className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-primary">{items.length}</div>
            <span className="text-[11px] text-muted">Parsed specifications</span>
          </div>
        </div>

        <div className="bg-card border border-border-card p-5 rounded-xl shadow-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted font-semibold uppercase tracking-wider">Mapped Endpoints</span>
            <div className="w-8 h-8 rounded-lg bg-status-passed-bg border border-status-passed/30 flex items-center justify-center text-status-passed">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-status-passed">
              {items.filter((i) => i.mapping_status === 'MAPPED').length}
            </div>
            <span className="text-[11px] text-muted">Verified routes</span>
          </div>
        </div>

        <div className="bg-card border border-border-card p-5 rounded-xl shadow-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted font-semibold uppercase tracking-wider">Ambiguous Mappings</span>
            <div className="w-8 h-8 rounded-lg bg-status-flaky-bg border border-status-flaky/30 flex items-center justify-center text-status-flaky">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-status-flaky">
              {items.filter((i) => i.mapping_status === 'AMBIGUOUS').length}
            </div>
            <span className="text-[11px] text-muted">Requires review</span>
          </div>
        </div>

        <div className="bg-card border border-border-card p-5 rounded-xl shadow-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted font-semibold uppercase tracking-wider">Requirement Coverage</span>
            <div className="w-8 h-8 rounded-lg bg-secondaryAccent/10 border border-secondaryAccent/20 flex items-center justify-center text-secondaryAccent">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-brand">{coveragePct}%</div>
            <span className="text-[11px] text-muted">{verifiedCount} of {items.length} verified</span>
          </div>
        </div>
      </div>

      {/* Traceability Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold text-primary">Requirement Coverage Traceability Matrix</div>
          <button onClick={fetchTraceability} className="text-xs text-secondary hover:text-primary flex items-center gap-1 font-medium transition-colors">
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        {loading ? (
          <div className="text-center py-12 text-muted text-sm">Loading requirement matrix...</div>
        ) : (
          <RequirementTraceabilityTable items={items} onSelectRequirement={() => {}} />
        )}
      </div>

      {projectId && (
        <RequirementUploadModal
          projectId={projectId}
          isOpen={isUploadOpen}
          onClose={() => setIsUploadOpen(false)}
          onSuccess={fetchTraceability}
        />
      )}

      <LLMConfigDrawer
        isOpen={isConfigOpen}
        onClose={() => setIsConfigOpen(false)}
        onSave={(cfg) => setAiConfig(cfg)}
      />
    </div>
  );
};
