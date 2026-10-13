import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  X,
  ShieldAlert,
  Cpu,
  GitCommit,
  FileText,
  CheckCircle2,
  HelpCircle,
  MessageSquare,
  Send,
  FlaskConical,
  Code2,
  Eye,
  Shield,
  Clock,
  Sparkles,
} from 'lucide-react';
import { JsonDiffViewer } from './JsonDiffViewer';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { Button } from './common/Button';

interface RootCauseInspectorModalProps {
  analysis: any;
  projectId?: string;
  onClose: () => void;
}

interface CommentItem {
  id: string;
  defect_id: string;
  user_id: string;
  message: string;
  status_change?: string;
  created_at: string;
  user_name: string;
  user_role: string;
}

export const RootCauseInspectorModal: React.FC<RootCauseInspectorModalProps> = ({
  analysis,
  projectId: propProjectId,
  onClose,
}) => {
  const { projectId: urlProjectId } = useParams<{ projectId: string }>();
  const projectId = propProjectId || urlProjectId || analysis?.project_id;
  const defectId = analysis?.id || analysis?.analysis_id;

  const { user } = useAuthStore();
  const isViewer = user?.role === 'VIEWER';

  const [comments, setComments] = useState<CommentItem[]>([]);
  const [loadingComments, setLoadingComments] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [statusChange, setStatusChange] = useState<string>('');
  const [currentStatus, setCurrentStatus] = useState<string>(analysis?.status || 'OPEN');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (projectId && defectId) {
      fetchComments();
    }
  }, [projectId, defectId]);

  const fetchComments = async () => {
    setLoadingComments(true);
    try {
      const res = await api.get(`/projects/${projectId}/defects/${defectId}/comments`);
      setComments(res.data || []);
    } catch {
      // ignore
    } finally {
      setLoadingComments(false);
    }
  };

  const handlePostComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    setSubmitting(true);
    try {
      const res = await api.post(`/projects/${projectId}/defects/${defectId}/comments`, {
        message: commentText.trim(),
        status_change: statusChange || undefined,
      });
      setComments([...comments, res.data]);
      if (statusChange) {
        setCurrentStatus(statusChange);
        setStatusChange('');
      }
      setCommentText('');
    } catch (err) {
      console.error('Failed to post comment', err);
    } finally {
      setSubmitting(false);
    }
  };

  if (!analysis) return null;

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case 'SERVER_CRASH':
      case 'DATABASE_ERROR':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      case 'AUTHENTICATION_FAILURE':
      case 'AUTHORIZATION_FAILURE':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'CONTRACT_VIOLATION':
      case 'REQUEST_VALIDATION_DEFECT':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      default:
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
    }
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case 'FIXED':
      case 'VERIFIED':
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      case 'FIX_IN_PROGRESS':
        return 'bg-sky-500/15 text-sky-400 border-sky-500/30';
      case 'UNDER_INVESTIGATION':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      default:
        return 'bg-rose-500/15 text-rose-400 border-rose-500/30';
    }
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'TESTER':
        return <FlaskConical className="w-3 h-3 text-emerald-400" />;
      case 'DEVELOPER':
        return <Code2 className="w-3 h-3 text-sky-400" />;
      case 'ADMIN':
        return <Shield className="w-3 h-3 text-purple-400" />;
      default:
        return <Eye className="w-3 h-3 text-amber-400" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      <div className="w-full max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white">Root-Cause Diagnostic Inspector</h2>
                <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${getCategoryColor(analysis.category)}`}>
                  {analysis.category}
                </span>
                <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border uppercase ${getStatusBadge(currentStatus)}`}>
                  {currentStatus.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">Analysis ID: {defectId}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Multi-Metric Confidence Dashboard */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1">
              <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">Classification Confidence</span>
              <div className="text-lg font-bold text-indigo-400 font-mono">
                {Math.round((analysis.classification_confidence || 1.0) * 100)}%
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1">
              <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">Attribution Confidence</span>
              <div className="text-lg font-bold text-cyan-400 font-mono">
                {Math.round((analysis.attribution_confidence || 1.0) * 100)}%
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1">
              <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">Root-Cause Confidence</span>
              <div className="text-lg font-bold text-emerald-400 font-mono">
                {Math.round((analysis.root_cause_confidence || 0.0) * 100)}%
              </div>
            </div>
          </div>

          {/* Root-Cause Candidate Hypotheses */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              Root-Cause Hypotheses & Remediation
            </h3>
            {analysis.root_cause_candidates && analysis.root_cause_candidates.length > 0 ? (
              analysis.root_cause_candidates.map((cand: any, idx: number) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-emerald-300 flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      Candidate #{idx + 1}: {cand.reasoning_type}
                    </span>
                    <span className="text-xs font-mono font-bold text-emerald-400">
                      {Math.round((cand.confidence || 1.0) * 100)}% Confidence
                    </span>
                  </div>
                  <p className="text-xs text-slate-200">{cand.description}</p>
                  {cand.suggested_remediation && (
                    <div className="p-2.5 rounded-lg bg-indigo-950/30 border border-indigo-500/20 text-xs text-indigo-300">
                      <span className="font-semibold text-indigo-400">Suggested Remediation:</span> {cand.suggested_remediation}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="p-3 text-xs text-slate-400 bg-slate-950/40 rounded-xl border border-slate-800">
                Insufficient empirical evidence available.
              </div>
            )}
          </div>

          {/* Fault Location Ranking */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <FileText className="w-4 h-4 text-cyan-400" />
              Ranked Candidate Fault Locations (AST & PKG)
            </h3>
            {analysis.fault_locations && analysis.fault_locations.length > 0 ? (
              <div className="space-y-2">
                {analysis.fault_locations.map((loc: any, idx: number) => (
                  <div key={idx} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between text-xs font-mono">
                    <div className="space-y-0.5">
                      <div className="font-bold text-slate-200">
                        {loc.file_path}:{loc.line_number}
                        {loc.function_name && <span className="text-cyan-400 font-normal ml-2">in {loc.function_name}()</span>}
                      </div>
                      <div className="text-[11px] text-slate-400 flex items-center gap-2 font-sans">
                        <span>Reason: {loc.reason}</span>
                        {loc.pkg_node_id && <span className="text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded text-[10px] font-mono border border-indigo-500/20">PKG Graph Node</span>}
                      </div>
                    </div>
                    <span className="text-xs font-bold text-cyan-400 font-mono">{Math.round((loc.confidence || 1.0) * 100)}%</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-3 text-xs text-slate-400 bg-slate-950/40 rounded-xl border border-slate-800">
                No project source stack frames identified.
              </div>
            )}
          </div>

          {/* Structural Diff Viewer */}
          <JsonDiffViewer diffItems={analysis.diff_items || []} />

          {/* ----------------------------------------------------------------- */}
          {/* TESTER & DEVELOPER COLLABORATION PANEL                            */}
          {/* ----------------------------------------------------------------- */}
          <div className="p-5 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-indigo-300 uppercase tracking-wider flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-brand" />
                Tester & Developer Triage Collaboration ({comments.length})
              </h3>
              <span className="text-[11px] text-slate-400">
                Current Status:{' '}
                <strong className="text-white uppercase">{currentStatus.replace(/_/g, ' ')}</strong>
              </span>
            </div>

            {/* Conversation Log */}
            <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
              {comments.length === 0 ? (
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 text-center text-xs text-slate-500">
                  No collaboration messages yet. Tester and Developer can exchange reproduction steps, fix notes, and verification updates here.
                </div>
              ) : (
                comments.map((c) => (
                  <div key={c.id} className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-200">{c.user_name}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 flex items-center gap-1 border border-slate-700">
                          {getRoleIcon(c.user_role)}
                          {c.user_role}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>

                    {c.status_change && (
                      <div className="text-[11px] text-brand font-semibold flex items-center gap-1">
                        &bull; Changed status to {c.status_change.replace(/_/g, ' ')}
                      </div>
                    )}

                    <p className="text-xs text-slate-300 whitespace-pre-wrap">{c.message}</p>
                  </div>
                ))
              )}
            </div>

            {/* Post Note & Status Update Input */}
            {!isViewer ? (
              <form onSubmit={handlePostComment} className="space-y-3 pt-3 border-t border-slate-800">
                <textarea
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  placeholder={
                    user?.role === 'TESTER'
                      ? 'Tester note: describe reproduction steps, edge-cases, or verification check...'
                      : user?.role === 'DEVELOPER'
                      ? 'Developer note: explain patch, link commit/PR, or request clarification...'
                      : 'Admin note: high-level coordination feedback...'
                  }
                  rows={2}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
                  required
                />

                <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <span className="text-xs text-slate-400 shrink-0">Update Status:</span>
                    <select
                      value={statusChange}
                      onChange={(e) => setStatusChange(e.target.value)}
                      className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                    >
                      <option value="">(Keep current status)</option>
                      <option value="UNDER_INVESTIGATION">Under Investigation</option>
                      <option value="FIX_IN_PROGRESS">Fix In Progress</option>
                      <option value="FIXED">Fixed (Ready for Retest)</option>
                      <option value="VERIFIED">Verified (Resolved)</option>
                    </select>
                  </div>

                  <Button
                    variant="primary"
                    size="sm"
                    type="submit"
                    isLoading={submitting}
                    disabled={!commentText.trim()}
                    leftIcon={<Send className="w-3.5 h-3.5" />}
                  >
                    Post Triage Note
                  </Button>
                </div>
              </form>
            ) : (
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-500 italic text-center">
                Viewer accounts have read-only visibility into bug triage collaboration.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
