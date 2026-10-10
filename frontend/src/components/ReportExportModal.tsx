import React, { useState } from 'react';
import { X, FileText, Download, CheckCircle2, Shield, Loader2, ExternalLink } from 'lucide-react';
import { api } from '../services/api';

interface ReportExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  projectName: string;
}

export const ReportExportModal: React.FC<ReportExportModalProps> = ({
  isOpen,
  onClose,
  projectId,
  projectName,
}) => {
  const [title, setTitle] = useState(`${projectName} - Comprehensive Software Quality Audit`);
  const [generating, setGenerating] = useState(false);
  const [generatedReport, setGeneratedReport] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const res = await api.post(`/analytics/projects/${projectId}/reports`, { title });
      setGeneratedReport(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to compile executive quality report.');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = (format: 'html' | 'pdf') => {
    if (!generatedReport) return;
    const url = `/api/v1/analytics/reports/${generatedReport.id}/export?format=${format}`;
    window.open(url, '_blank');
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-6 relative">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Generate Executive Quality Audit Report</h3>
              <p className="text-xs text-slate-400">Formal compliance artifact with cryptographic hash verification</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-xl transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400 font-medium">
            {error}
          </div>
        )}

        {!generatedReport ? (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Audit Report Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Q4 Executive Software Quality Audit"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 font-medium"
              />
            </div>

            <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-slate-400 space-y-2">
              <span className="font-bold text-slate-300 block">Report Specifications Included:</span>
              <ul className="list-disc list-inside space-y-1 text-slate-400">
                <li>Composite Quality Scorecard & breakdown metrics</li>
                <li>Defect Density per discovered endpoint</li>
                <li>Flaky test quarantine records & suppression actions</li>
                <li>Phase 8 Selective Regression avoidance savings (time & test count)</li>
                <li>Phase 9 CI/CD Quality Gate compliance and GitHub checks</li>
                <li>SHA256 digital fingerprint for immutability</li>
              </ul>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-lg shadow-indigo-500/25 flex items-center gap-2 disabled:opacity-50"
              >
                {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                {generating ? 'Compiling Report...' : 'Compile Audit Report'}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h4 className="text-sm font-bold text-emerald-300">Executive Report Compiled Successfully</h4>
                <p className="text-xs text-slate-300">{generatedReport.title}</p>
                <div className="pt-2 font-mono text-[11px] text-slate-400">
                  <span className="text-slate-500 block uppercase text-[9px] font-bold">SHA256 Fingerprint:</span>
                  <span className="text-indigo-400 break-all select-all font-bold">{generatedReport.sha256_hash}</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => handleDownload('html')}
                className="p-3.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-slate-600 transition-all text-left flex items-center justify-between"
              >
                <div>
                  <span className="text-xs font-bold text-white block">Interactive HTML5</span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">Standalone printable web artifact</span>
                </div>
                <ExternalLink className="w-4 h-4 text-indigo-400 shrink-0" />
              </button>

              <button
                onClick={() => handleDownload('pdf')}
                className="p-3.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/40 transition-all text-left flex items-center justify-between"
              >
                <div>
                  <span className="text-xs font-bold text-indigo-300 block">ReportLab PDF</span>
                  <span className="text-[10px] text-indigo-400/80 block mt-0.5">Formal executive paginated document</span>
                </div>
                <Download className="w-4 h-4 text-indigo-400 shrink-0" />
              </button>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={onClose}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
