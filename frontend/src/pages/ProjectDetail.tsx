import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  ExternalLink,
  GitBranch,
  Calendar,
  Shield,
  Cpu,
  Activity,
  Info,
  Code2,
  Play,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Layers,
  Network,
  FileCode
} from 'lucide-react';
import { api } from '../services/api';

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

interface Analysis {
  id: string;
  project_id: string;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'COMPLETED_WITH_WARNINGS' | 'FAILED' | 'CANCELLED';
  current_stage: 'CLONING' | 'SCANNING' | 'AST_PARSING' | 'GRAPH_BUILDING' | 'PERSISTING' | 'FINISHED';
  progress_percent: number;
  repository_url: string;
  branch: string;
  commit_sha: string | null;
  detected_language: string | null;
  detected_framework: string | null;
  framework_confidence: number;
  scanned_files_count: number;
  parsed_files_count: number;
  endpoint_count: number;
  graph_node_count: number;
  graph_edge_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
}

interface DiscoveredEndpoint {
  id: string;
  method: string;
  path: string;
  function_name: string;
  parameters: Array<{ name: string; type?: string; default?: string }>;
  request_model: string | null;
  response_model: string | null;
  framework: string;
  confidence: number;
  file_path: string;
  line_number: number;
}

interface KnowledgeGraph {
  nodes: Array<{ id: string; label: string; type: string; properties: any }>;
  edges: Array<{ source: string; target: string; type: string; properties: any }>;
}

export const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [endpoints, setEndpoints] = useState<DiscoveredEndpoint[]>([]);
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);

  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'endpoints' | 'graph' | 'testruns'>('overview');

  useEffect(() => {
    fetchProjectDetail();
    fetchLatestAnalysis();
  }, [id]);

  useEffect(() => {
    if (analysis && (analysis.status === 'QUEUED' || analysis.status === 'RUNNING')) {
      const timer = setInterval(() => {
        fetchLatestAnalysis();
      }, 3000);
      return () => clearInterval(timer);
    }
  }, [analysis]);

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

  const fetchLatestAnalysis = async () => {
    try {
      const res = await api.get(`/projects/${id}/analysis`);
      setAnalysis(res.data);

      if (res.data && (res.data.status === 'COMPLETED' || res.data.status === 'COMPLETED_WITH_WARNINGS')) {
        fetchEndpoints();
        fetchGraph();
      }
    } catch (err) {
      // No analysis run yet
    }
  };

  const fetchEndpoints = async () => {
    try {
      const res = await api.get(`/projects/${id}/endpoints?page_size=100`);
      setEndpoints(res.data.items || []);
    } catch (err) {}
  };

  const fetchGraph = async () => {
    try {
      const res = await api.get(`/projects/${id}/graph`);
      setGraph(res.data);
    } catch (err) {}
  };

  const triggerAnalysis = async () => {
    setAnalyzing(true);
    try {
      const res = await api.post(`/projects/${id}/analyze`);
      setAnalysis(res.data);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to start repository analysis.');
    } finally {
      setAnalyzing(false);
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

  const getMethodBadgeClass = (method: string) => {
    switch (method.toUpperCase()) {
      case 'GET': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'POST': return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
      case 'PUT': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'DELETE': return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      default: return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

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

          <div className="flex items-center gap-3">
            <button
              onClick={triggerAnalysis}
              disabled={analyzing || (analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-xs font-bold text-white transition-all shadow-lg shadow-indigo-600/20 disabled:cursor-not-allowed"
            >
              {analyzing || analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED' ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-300" /> Analyzing...
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" /> Analyze Repository
                </>
              )}
            </button>

            <a
              href={project.repository_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs font-medium text-slate-300 transition-colors shrink-0"
            >
              <ExternalLink className="w-3.5 h-3.5 text-indigo-400" /> View Repository
            </a>
          </div>
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
            <span className="text-slate-500 block text-[10px] uppercase">Latest Analysis SHA</span>
            <span className="text-slate-200 font-semibold mt-0.5 block font-mono text-[11px] truncate">
              {analysis?.commit_sha ? analysis.commit_sha.substring(0, 8) : 'Not Analyzed'}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase">Detected Framework</span>
            <span className="text-indigo-400 font-semibold mt-0.5 block">
              {analysis?.detected_framework || 'Unknown'}
            </span>
          </div>
        </div>
      </div>

      {/* Analysis Status Banner */}
      {analysis && (
        <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              {analysis.status === 'COMPLETED' && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
              {analysis.status === 'RUNNING' && <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin" />}
              {analysis.status === 'FAILED' && <AlertTriangle className="w-5 h-5 text-rose-400" />}
              <div>
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  Static Analysis Snapshot #{analysis.id.substring(0, 8)}
                  <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold border ${
                    analysis.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                    analysis.status === 'RUNNING' ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  }`}>
                    {analysis.status}
                  </span>
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Stage: <span className="text-slate-200 font-semibold font-mono">{analysis.current_stage}</span> ({analysis.progress_percent}%)
                </p>
              </div>
            </div>

            <div className="flex items-center gap-6 text-xs font-mono text-slate-400">
              <div><span className="text-slate-500">Files:</span> {analysis.scanned_files_count}</div>
              <div><span className="text-slate-500">Endpoints:</span> {analysis.endpoint_count}</div>
              <div><span className="text-slate-500">Graph Nodes:</span> {analysis.graph_node_count}</div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
            <div
              className="bg-indigo-500 h-full transition-all duration-500 ease-out"
              style={{ width: `${analysis.progress_percent}%` }}
            />
          </div>
        </div>
      )}

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
          <Code2 className="w-4 h-4" /> Discovered Endpoints ({endpoints.length})
        </button>
        <button
          onClick={() => setActiveTab('graph')}
          className={`pb-3 transition-all relative flex items-center gap-1.5 ${
            activeTab === 'graph' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500' : 'hover:text-slate-200'
          }`}
        >
          <Network className="w-4 h-4" /> Knowledge Graph ({graph?.nodes.length || 0})
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
          <h3 className="text-base font-bold text-white">Project Infrastructure & Static Intelligence</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Astra static analyzer parses source code using deterministic Python AST parsers without executing target application code.
          </p>

          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2 font-mono text-xs text-slate-300">
            <p className="text-indigo-400 font-semibold">// Repository & Analysis Metadata</p>
            <pre className="overflow-x-auto">{JSON.stringify({ project, latest_analysis: analysis }, null, 2)}</pre>
          </div>
        </div>
      )}

      {activeTab === 'endpoints' && (
        <div className="space-y-4">
          {endpoints.length === 0 ? (
            <div className="glass-card rounded-2xl p-8 text-center space-y-3 border border-slate-800">
              <Cpu className="w-10 h-10 text-indigo-400 mx-auto" />
              <h3 className="text-base font-bold text-white">No Endpoints Discovered Yet</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Click "Analyze Repository" to run the static code parser and discover API routes automatically.
              </p>
            </div>
          ) : (
            <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Method</th>
                    <th className="px-4 py-3">Path</th>
                    <th className="px-4 py-3">Handler Function</th>
                    <th className="px-4 py-3">Parameters</th>
                    <th className="px-4 py-3">Source Location</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {endpoints.map((ep) => (
                    <tr key={ep.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded font-bold border ${getMethodBadgeClass(ep.method)}`}>
                          {ep.method}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-white font-semibold">{ep.path}</td>
                      <td className="px-4 py-3 text-indigo-400">{ep.function_name}()</td>
                      <td className="px-4 py-3 text-slate-400 max-w-xs truncate">
                        {ep.parameters.map(p => p.name).join(', ') || 'None'}
                      </td>
                      <td className="px-4 py-3 text-slate-400 flex items-center gap-1">
                        <FileCode className="w-3.5 h-3.5 text-slate-500" />
                        {ep.file_path}:{ep.line_number}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'graph' && (
        <div className="space-y-4">
          {!graph || graph.nodes.length === 0 ? (
            <div className="glass-card rounded-2xl p-8 text-center space-y-3 border border-slate-800">
              <Network className="w-10 h-10 text-indigo-400 mx-auto" />
              <h3 className="text-base font-bold text-white">Knowledge Graph Not Available</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Run repository analysis to generate the directed Project Knowledge Graph (PKG).
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Nodes List Card */}
              <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-3">
                <h4 className="text-sm font-bold text-white flex items-center justify-between">
                  <span>Graph Nodes</span>
                  <span className="text-xs font-mono text-indigo-400">{graph.nodes.length} nodes</span>
                </h4>
                <div className="space-y-2 max-h-96 overflow-y-auto pr-2">
                  {graph.nodes.map((node) => (
                    <div key={node.id} className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between text-xs font-mono">
                      <div>
                        <span className="text-slate-200 font-semibold block">{node.label}</span>
                        <span className="text-[10px] text-slate-500">{node.id}</span>
                      </div>
                      <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[10px]">
                        {node.type}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Edges List Card */}
              <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-3">
                <h4 className="text-sm font-bold text-white flex items-center justify-between">
                  <span>Graph Relationships (Edges)</span>
                  <span className="text-xs font-mono text-emerald-400">{graph.edges.length} edges</span>
                </h4>
                <div className="space-y-2 max-h-96 overflow-y-auto pr-2">
                  {graph.edges.map((edge, idx) => (
                    <div key={idx} className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs font-mono space-y-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-indigo-400">{edge.source}</span>
                        <span className="px-1.5 py-0.5 rounded bg-slate-800 text-emerald-400 text-[10px] font-bold">
                          {edge.type}
                        </span>
                        <span className="text-indigo-400">{edge.target}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
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
