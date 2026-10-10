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
  FileCode,
  Sliders,
  ChevronRight,
  Zap
} from 'lucide-react';
import { api } from '../services/api';
import { TestGenerationDrawer } from '../components/TestGenerationDrawer';

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

interface TestSuite {
  id: string;
  name: string;
  total_cases: number;
  version: string;
  created_at: string;
}

interface TestRun {
  id: string;
  status: string;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  error_tests: number;
  duration_ms: number;
  created_at: string;
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
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [testRuns, setTestRuns] = useState<TestRun[]>([]);
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [generatingSuite, setGeneratingSuite] = useState(false);
  const [dispatchingRun, setDispatchingRun] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'endpoints' | 'graph' | 'testruns'>('overview');

  useEffect(() => {
    if (!id) return;

    let isMounted = true;
    const loadProject = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.get(`/projects/${id}`);
        if (!isMounted) return;
        setProject(res.data);

        // Project exists and is loaded successfully; now fetch child telemetry
        loadChildResources();
      } catch (err: any) {
        if (!isMounted) return;
        setError(err.response?.data?.detail || 'Project not found or accessible.');
        setProject(null);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadProject();
    return () => {
      isMounted = false;
    };
  }, [id]);

  const loadChildResources = () => {
    fetchLatestAnalysis();
    fetchTestSuites();
    fetchTestRuns();
  };

  useEffect(() => {
    if (analysis && (analysis.status === 'QUEUED' || analysis.status === 'RUNNING')) {
      const timer = setInterval(() => {
        fetchLatestAnalysis();
      }, 3000);
      return () => clearInterval(timer);
    }
  }, [analysis]);

  const fetchProjectDetail = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const res = await api.get(`/projects/${id}`);
      setProject(res.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Project not found or accessible.');
      setProject(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchLatestAnalysis = async () => {
    if (!id) return;
    try {
      const res = await api.get(`/projects/${id}/analysis`);
      setAnalysis(res.data);

      if (res.data && (res.data.status === 'COMPLETED' || res.data.status === 'COMPLETED_WITH_WARNINGS')) {
        fetchEndpoints();
        fetchGraph();
      }
    } catch (err) {
      setAnalysis(null);
    }
  };

  const fetchEndpoints = async () => {
    if (!id) return;
    try {
      const res = await api.get(`/projects/${id}/endpoints?page_size=100`);
      setEndpoints(res.data.items || []);
    } catch (err) {
      setEndpoints([]);
    }
  };

  const fetchGraph = async () => {
    if (!id) return;
    try {
      const res = await api.get(`/projects/${id}/graph`);
      setGraph(res.data);
    } catch (err) {
      setGraph(null);
    }
  };

  const fetchTestSuites = async () => {
    if (!id) return;
    try {
      const res = await api.get(`/projects/${id}/test-suites`);
      setSuites(res.data.items || []);
    } catch (err) {
      setSuites([]);
    }
  };

  const fetchTestRuns = async () => {
    if (!id) return;
    try {
      const res = await api.get(`/projects/${id}/test-runs`);
      setTestRuns(res.data.items || []);
    } catch (err) {
      setTestRuns([]);
    }
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

  const generateTestSuite = async () => {
    setGeneratingSuite(true);
    try {
      const res = await api.post(`/projects/${id}/test-suites/generate`, {
        name: `Synthetic Suite v${suites.length + 1}`
      });
      fetchTestSuites();
      alert(`Successfully generated synthetic test suite '${res.data.name}' with ${res.data.total_cases} test cases!`);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to generate test suite. Ensure repository is analyzed first.');
    } finally {
      setGeneratingSuite(false);
    }
  };

  const dispatchRun = async (suiteId: string) => {
    setDispatchingRun(true);
    try {
      const res = await api.post(`/projects/${id}/test-runs`, {
        suite_id: suiteId,
        target_base_url: 'http://localhost:8000',
        environment_type: 'LOCAL_SANDBOX',
        health_check_path: '/health'
      });
      fetchTestRuns();
      setActiveTab('testruns');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to dispatch test run.');
    } finally {
      setDispatchingRun(false);
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

            <button
              onClick={() => setIsDrawerOpen(true)}
              disabled={!analysis || endpoints.length === 0}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 hover:border-indigo-500/40 text-xs font-semibold text-indigo-300 transition-colors shrink-0 disabled:opacity-50"
            >
              <Sliders className="w-3.5 h-3.5 text-indigo-400" /> Advanced Suite Generator
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
          <Activity className="w-4 h-4" /> Test Executions ({testRuns.length})
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
          <h3 className="text-base font-bold text-white">Project Infrastructure & Execution Platform</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Astra executes synthetic HTTP test cases deterministically against target applications with full SSRF protection and secret redaction.
          </p>
        </div>
      )}

      {activeTab === 'endpoints' && (
        <div className="space-y-4">
          {endpoints.length === 0 ? (
            <div className="glass-card rounded-2xl p-8 text-center space-y-3 border border-slate-800">
              <Cpu className="w-10 h-10 text-indigo-400 mx-auto" />
              <h3 className="text-base font-bold text-white">No Endpoints Discovered Yet</h3>
            </div>
          ) : (
            <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Method</th>
                    <th className="px-4 py-3">Path</th>
                    <th className="px-4 py-3">Handler Function</th>
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
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
            </div>
          )}
        </div>
      )}

      {activeTab === 'testruns' && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white">Test Suites & Execution Telemetry</h3>
              <p className="text-xs text-slate-400">Generate synthetic test specifications and execute async HTTP test runs.</p>
            </div>

            <button
              onClick={generateTestSuite}
              disabled={generatingSuite || endpoints.length === 0}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-xs font-bold text-white transition-all shadow-lg shadow-emerald-600/20 shrink-0"
            >
              <Zap className="w-4 h-4 fill-current" /> Generate Synthetic Suite
            </button>
          </div>

          {/* Generated Test Suites */}
          <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-3">
            <h4 className="text-sm font-bold text-white">Generated Test Suites ({suites.length})</h4>
            {suites.length === 0 ? (
              <p className="text-xs text-slate-500">No test suites generated yet. Click "Generate Synthetic Suite" above.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {suites.map(s => (
                  <div key={s.id} className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between text-xs font-mono">
                    <div className="space-y-1">
                      <span className="text-slate-200 font-bold block">{s.name}</span>
                      <span className="text-slate-500 text-[10px] block">{s.total_cases} test cases • v{s.version}</span>
                    </div>
                    <button
                      onClick={() => dispatchRun(s.id)}
                      disabled={dispatchingRun}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[11px] transition-all flex items-center gap-1"
                    >
                      <Play className="w-3 h-3 fill-current" /> Run Suite
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Past Execution Runs Table */}
          <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden space-y-3 p-5">
            <h4 className="text-sm font-bold text-white">Execution History ({testRuns.length})</h4>
            {testRuns.length === 0 ? (
              <p className="text-xs text-slate-500">No test runs executed yet.</p>
            ) : (
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Run ID</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Tests Passed / Total</th>
                    <th className="px-4 py-3">Duration</th>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {testRuns.map(run => (
                    <tr key={run.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-4 py-3 font-bold text-white">#{run.id.substring(0, 8)}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded font-bold border ${
                          run.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                          run.status === 'FAILED' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-slate-500/10 text-slate-400 border-slate-500/20'
                        }`}>
                          {run.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-300 font-bold">
                        <span className="text-emerald-400">{run.passed_tests}</span> / {run.total_tests}
                      </td>
                      <td className="px-4 py-3 text-slate-400">{run.duration_ms.toFixed(0)} ms</td>
                      <td className="px-4 py-3 text-slate-500">{new Date(run.created_at).toLocaleTimeString()}</td>
                      <td className="px-4 py-3">
                        <Link
                          to={`/projects/${project.id}/test-runs/${run.id}`}
                          className="inline-flex items-center gap-1 text-indigo-400 hover:underline font-bold"
                        >
                          View Results <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
      {/* Advanced Test Suite Generation Drawer */}
      {id && (
        <TestGenerationDrawer
          isOpen={isDrawerOpen}
          onClose={() => setIsDrawerOpen(false)}
          projectId={id}
          endpointCount={endpoints.length}
          onSuiteGenerated={() => {
            fetchTestSuites();
            fetchTestRuns();
          }}
        />
      )}
    </div>
  );
};
