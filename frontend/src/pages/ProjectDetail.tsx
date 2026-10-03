import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ExternalLink, GitBranch, Calendar, Shield, Cpu, Activity, Info, Code2 } from 'lucide-react';
import { api } from '../services/api';
import { StatusBadge } from '../components/common/StatusBadge';

interface Project {
  id: string;
  name: string;
  description: string | null;
  repository_url: string;
  default_branch: string;
  language_framework: string;
  owner_id: string;
  owner?: { full_name: string; email: string };
  created_at: string;
  updated_at: string;
}

export const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'endpoints' | 'testruns'>('overview');

  useEffect(() => {
    fetchProjectDetail();
  }, [id]);

  const fetchProjectDetail = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/projects/${id}`);
      setProject(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Project not found or accessible.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-16 text-slate-500 text-sm">Loading project details...</div>;
  }

  if (error || !project) {
    return (
      <div className="glass-card rounded-2xl p-8 text-center space-y-4 border border-slate-800 max-w-md mx-auto">
        <Info className="w-10 h-10 text-rose-400 mx-auto" />
        <h3 className="text-lg font-bold text-slate-200">Project Not Found</h3>
        <p className="text-xs text-slate-400">{error}</p>
        <Link to="/projects" className="inline-block text-xs font-semibold text-indigo-400 hover:underline">
          &larr; Return to Projects List
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb Header */}
      <div className="flex items-center gap-3 text-xs text-slate-400">
        <Link to="/projects" className="hover:text-slate-200 transition-colors flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> Projects
        </Link>
        <span>/</span>
        <span className="text-slate-200 font-semibold">{project.name}</span>
      </div>

      {/* Project Banner Card */}
      <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-extrabold text-white">{project.name}</h1>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                {project.language_framework}
              </span>
            </div>
            <p className="text-xs text-slate-400">{project.description || 'No description provided.'}</p>
          </div>

          <a
            href={project.repository_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs font-medium text-slate-300 transition-colors shrink-0"
          >
            <ExternalLink className="w-3.5 h-3.5 text-indigo-400" /> View Repository
          </a>
        </div>

        {/* Metadata Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-800/80 text-xs font-mono text-slate-400">
          <div>
            <span className="text-slate-500 block text-[10px] uppercase">Default Branch</span>
            <span className="text-slate-200 flex items-center gap-1 font-semibold mt-0.5">
              <GitBranch className="w-3.5 h-3.5 text-slate-400" /> {project.default_branch}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase">Project Owner</span>
            <span className="text-slate-200 font-semibold mt-0.5 block truncate">
              {project.owner?.full_name || 'System'}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase">Created Date</span>
            <span className="text-slate-200 flex items-center gap-1 font-semibold mt-0.5">
              <Calendar className="w-3.5 h-3.5 text-slate-400" /> {new Date(project.created_at).toLocaleDateString()}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase">Framework Spec</span>
            <span className="text-slate-200 font-semibold mt-0.5 block">
              {project.language_framework}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-slate-800 gap-6 text-sm font-medium text-slate-400">
        <button
          onClick={() => setActiveTab('overview')}
          className={`pb-3 transition-all relative ${
            activeTab === 'overview' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500' : 'hover:text-slate-200'
          }`}
        >
          Workspace Overview
        </button>
        <button
          onClick={() => setActiveTab('endpoints')}
          className={`pb-3 transition-all relative flex items-center gap-1.5 ${
            activeTab === 'endpoints' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500' : 'hover:text-slate-200'
          }`}
        >
          <Code2 className="w-4 h-4" /> Extracted Endpoints
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-500 font-mono">Phase 2</span>
        </button>
        <button
          onClick={() => setActiveTab('testruns')}
          className={`pb-3 transition-all relative flex items-center gap-1.5 ${
            activeTab === 'testruns' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500' : 'hover:text-slate-200'
          }`}
        >
          <Activity className="w-4 h-4" /> Test Executions
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-500 font-mono">Phase 3</span>
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
          <h3 className="text-base font-bold text-white">Project Infrastructure Verification</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            This project entity has been stored in PostgreSQL with UUID key <code className="text-indigo-400">{project.id}</code>.
            In Phase 2, Astra will clone <code className="text-indigo-400">{project.repository_url}</code>, parse source code using Python AST & Tree-Sitter, and construct the Project Knowledge Graph.
          </p>

          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2 font-mono text-xs text-slate-300">
            <p className="text-indigo-400 font-semibold">// Database Record Telemetry</p>
            <pre className="overflow-x-auto">{JSON.stringify(project, null, 2)}</pre>
          </div>
        </div>
      )}

      {activeTab === 'endpoints' && (
        <div className="glass-card rounded-2xl p-8 text-center space-y-3 border border-slate-800">
          <Cpu className="w-10 h-10 text-indigo-400 mx-auto" />
          <h3 className="text-base font-bold text-white">AST Endpoint Analyzer (Phase 2 Placeholder)</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Repository static analysis, AST route discovery, and parameter extraction will be activated during Phase 2 implementation.
          </p>
        </div>
      )}

      {activeTab === 'testruns' && (
        <div className="glass-card rounded-2xl p-8 text-center space-y-3 border border-slate-800">
          <Activity className="w-10 h-10 text-emerald-400 mx-auto" />
          <h3 className="text-base font-bold text-white">Test Execution Engine (Phase 3 Placeholder)</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Deterministic HTTPX test execution, assertion evaluating, and failure logging will be implemented in Phase 3.
          </p>
        </div>
      )}
    </div>
  );
};
