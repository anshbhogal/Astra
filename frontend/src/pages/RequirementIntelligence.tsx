import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { FileCheck, Upload, Settings, RefreshCw, Layers, ShieldCheck, CheckCircle, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import { RequirementUploadModal } from '../components/RequirementUploadModal';
import { RequirementTraceabilityTable } from '../components/RequirementTraceabilityTable';
import { LLMConfigDrawer } from '../components/LLMConfigDrawer';

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <FileCheck className="w-6 h-6 text-indigo-400" />
            <span>Requirement Intelligence & Traceability</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            NLP specification extraction, multi-signal endpoint mapping, and AI boundary edge-case coverage matrix.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsConfigOpen(true)}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-lg text-xs font-medium flex items-center gap-2"
          >
            <Settings className="w-4 h-4 text-indigo-400" />
            <span>AI Settings ({aiConfig.provider})</span>
          </button>
          <button
            onClick={() => setIsUploadOpen(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-lg shadow-indigo-500/20"
          >
            <Upload className="w-4 h-4" />
            <span>Upload Specification Document</span>
          </button>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="text-xs text-slate-400 font-semibold uppercase">Total Requirements</div>
          <div className="text-2xl font-bold text-slate-100 mt-1">{items.length}</div>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="text-xs text-slate-400 font-semibold uppercase">Mapped Endpoints</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            {items.filter((i) => i.mapping_status === 'MAPPED').length}
          </div>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="text-xs text-slate-400 font-semibold uppercase">Ambiguous Mappings</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">
            {items.filter((i) => i.mapping_status === 'AMBIGUOUS').length}
          </div>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="text-xs text-slate-400 font-semibold uppercase">Requirement Coverage</div>
          <div className="text-2xl font-bold text-indigo-400 mt-1">{coveragePct}%</div>
        </div>
      </div>

      {/* Traceability Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold text-slate-200">Requirement Coverage Traceability Matrix</div>
          <button onClick={fetchTraceability} className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1">
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        {loading ? (
          <div className="text-center py-12 text-slate-500 text-sm">Loading requirement matrix...</div>
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
