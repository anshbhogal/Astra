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
  Zap,
  Check,
  Clock,
  Sparkles
} from 'lucide-react';
import { api } from '../services/api';
import { TestGenerationDrawer } from '../components/TestGenerationDrawer';
import { KnowledgeGraphVisualizer } from '../components/KnowledgeGraphVisualizer';

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

const PIPELINE_STAGES = [
  { key: 'CLONING', label: '1. Git Clone', desc: 'Fetch source tree & branch' },
  { key: 'SCANNING', label: '2. File Scan', desc: 'Scan files & detect language' },
  { key: 'AST_PARSING', label: '3. AST Parsing', desc: 'Parse AST & extract endpoints' },
  { key: 'GRAPH_BUILDING', label: '4. Knowledge Graph', desc: 'Build code dependency graph' },
  { key: 'PERSISTING', label: '5. Database Index', desc: 'Persist endpoints & graph nodes' },
];

const getStageInfo = (stage?: string, status?: string) => {
  if (!status) {
    return { title: 'Pipeline Idle', desc: 'Ready to clone repository and begin static AST analysis.', step: 0 };
  }
  if (status === 'COMPLETED' || status === 'COMPLETED_WITH_WARNINGS') {
    return { title: 'Analysis Complete', desc: 'Static analysis pipeline completed and knowledge graph indexed.', step: 6 };
  }
  if (status === 'FAILED') {
    return { title: 'Analysis Failed', desc: 'The analysis pipeline encountered an error.', step: 0 };
  }
  switch (stage) {
    case 'CLONING':
      return { title: 'Cloning Repository', desc: 'Fetching repository files and verifying git tree...', step: 1 };
    case 'SCANNING':
      return { title: 'Scanning Source Code', desc: 'Detecting languages, frameworks, and project structure...', step: 2 };
    case 'AST_PARSING':
      return { title: 'Parsing Abstract Syntax Trees', desc: 'Extracting route handlers, parameter schemas, and decorators...', step: 3 };
    case 'GRAPH_BUILDING':
      return { title: 'Building Knowledge Graph', desc: 'Resolving dependency graphs, controller links, and schema nodes...', step: 4 };
    case 'PERSISTING':
      return { title: 'Indexing & Saving Records', desc: 'Persisting discovered endpoints and graph nodes into database...', step: 5 };
    case 'FINISHED':
      return { title: 'Analysis Complete', desc: 'All static analysis stages completed successfully.', step: 6 };
    default:
      return { title: 'Queued in Pipeline', desc: 'Worker queued, preparing workspace sandbox...', step: 0 };
  }
};

const getStageStatus = (stageKey: string, currentStage?: string, overallStatus?: string) => {
  if (!overallStatus) {
    return 'pending';
  }
  if (overallStatus === 'COMPLETED' || overallStatus === 'COMPLETED_WITH_WARNINGS') {
    return 'completed';
  }
  const stageOrder = ['CLONING', 'SCANNING', 'AST_PARSING', 'GRAPH_BUILDING', 'PERSISTING', 'FINISHED'];
  const currentIndex = currentStage ? stageOrder.indexOf(currentStage) : -1;
  const targetIndex = stageOrder.indexOf(stageKey);

  if (overallStatus === 'FAILED') {
    if (targetIndex < currentIndex) return 'completed';
    if (targetIndex === currentIndex) return 'failed';
    return 'pending';
  }

  if (targetIndex < currentIndex) {
    return 'completed';
  } else if (targetIndex === currentIndex) {
    return 'active';
  } else {
    return 'pending';
  }
};

const formatFrameworkName = (raw?: string | null): string => {
  if (!raw) return 'Not Detected';
  const MAP: Record<string, string> = {
    PYTHON_FASTAPI: 'FastAPI',
    PYTHON_FLASK: 'Flask',
    PYTHON_DJANGO: 'Django',
    PYTHON_TORNADO: 'Tornado',
    PYTHON_SANIC: 'Sanic',
    PYTHON_PYSIDE_QT: 'PySide / Qt (Desktop GUI)',
    PYTHON_TKINTER: 'Tkinter (Desktop GUI)',
    PYTHON_KIVY: 'Kivy (GUI)',
    PYTHON_STREAMLIT: 'Streamlit (Data App)',
    PYTHON_GRADIO: 'Gradio (ML App)',
    PYTHON_ML_HUGGINGFACE: 'HuggingFace / PyTorch (ML)',
    PYTHON_ML_PYTORCH: 'PyTorch (Deep Learning)',
    PYTHON_ML_TENSORFLOW: 'TensorFlow / Keras',
    PYTHON_CELERY: 'Celery (Worker)',
    PYTHON_GENERIC: 'Python (Generic)',
    JAVA_SPRING: 'Spring Boot',
    JAVA_QUARKUS: 'Quarkus',
    JAVA_MICRONAUT: 'Micronaut',
    JAVA_JAKARTA: 'Jakarta EE / JAX-RS',
    JAVA_PLAY: 'Play Framework',
    JAVA_VERTX: 'Eclipse Vert.x',
    JAVA_GENERIC: 'Java (Generic)',
    CPP_DROGON: 'Drogon (C++ Web)',
    CPP_CROW: 'Crow (C++ Micro)',
    CPP_OATPP: 'Oat++ (C++ Web)',
    CPP_PISTACHE: 'Pistache (C++ REST)',
    CPP_BOOST_BEAST: 'Boost.Beast (C++)',
    CPP_GRPC: 'gRPC (C++)',
    CPP_QT: 'Qt (C++ Desktop)',
    CPP_WXWIDGETS: 'wxWidgets (C++ GUI)',
    CPP_IMGUI: 'Dear ImGui (C++)',
    CPP_CMAKE_NATIVE: 'CMake (Native C++)',
    CPP_GENERIC: 'C/C++ (Generic)',
    REACT: 'React',
    NEXTJS: 'Next.js',
    VUE: 'Vue.js',
    NUXT: 'Nuxt.js',
    ANGULAR: 'Angular',
    SVELTE: 'Svelte',
    SVELTEKIT: 'SvelteKit',
    NODE_EXPRESS: 'Express.js',
    NODE_NESTJS: 'NestJS',
    NODE_FASTIFY: 'Fastify',
    ELECTRON: 'Electron (Desktop)',
    TAURI: 'Tauri (Desktop)',
    REACT_NATIVE: 'React Native',
    OTHER: 'Other / Custom Stack',
  };
  return MAP[raw] || raw;
};

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
    let timer: ReturnType<typeof setInterval> | null = null;
    if (analysis && (analysis.status === 'QUEUED' || analysis.status === 'RUNNING')) {
      timer = setInterval(() => {
        fetchLatestAnalysis();
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [analysis?.status, id]);

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
        fetchTestSuites();
        fetchTestRuns();
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
    setAnalysis((prev) => ({
      id: prev?.id || '',
      project_id: id || '',
      status: 'RUNNING',
      current_stage: 'CLONING',
      progress_percent: 15,
      repository_url: project?.repository_url || '',
      branch: project?.default_branch || 'main',
      commit_sha: null,
      detected_language: null,
      detected_framework: null,
      framework_confidence: 0,
      scanned_files_count: 0,
      parsed_files_count: 0,
      endpoint_count: 0,
      graph_node_count: 0,
      graph_edge_count: 0,
      error_message: null,
      started_at: new Date().toISOString(),
      completed_at: null,
    }));
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
                {formatFrameworkName(project.language_framework)}
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
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-300" />
                  Analyzing ({analysis?.progress_percent ?? 0}%)
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
              {formatFrameworkName(analysis?.detected_framework)}
            </span>
          </div>
        </div>
      </div>

      {/* Real-time Analysis Progress Banner Card - Always Visible */}
      <div className={`glass-card rounded-2xl p-6 border transition-all duration-300 relative overflow-hidden shadow-2xl ${
        analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED' || analyzing
          ? 'border-indigo-500/40 bg-gradient-to-br from-indigo-950/40 via-slate-900/80 to-purple-950/30 shadow-indigo-950/50'
          : analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
          ? 'border-emerald-500/30 bg-gradient-to-br from-emerald-950/20 via-slate-900/80 to-slate-900 shadow-emerald-950/20'
          : analysis?.status === 'FAILED'
          ? 'border-rose-500/30 bg-gradient-to-br from-rose-950/20 via-slate-900/80 to-slate-900 shadow-rose-950/20'
          : 'border-slate-800 bg-slate-900/60'
      }`}>
        {/* Subtle Ambient Background Glow */}
        <div className="absolute -right-20 -top-20 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -left-20 -bottom-20 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 relative z-10">
          <div className="flex items-center gap-3">
            {analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED' || analyzing ? (
              <span className="relative flex h-3.5 w-3.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-indigo-500 shadow-[0_0_8px_#6366f1]"></span>
              </span>
            ) : analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS' ? (
              <div className="w-5 h-5 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
                <Check className="w-3 h-3 stroke-[3]" />
              </div>
            ) : analysis?.status === 'FAILED' ? (
              <div className="w-5 h-5 rounded-full bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400">
                <AlertTriangle className="w-3 h-3" />
              </div>
            ) : (
              <div className="w-5 h-5 rounded-full bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
                <Play className="w-2.5 h-2.5 fill-current ml-0.5" />
              </div>
            )}
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white tracking-wide">
                  Repository Static Analysis Pipeline
                </h3>
                <span className={`text-[10px] uppercase font-bold font-mono px-2 py-0.5 rounded-full border ${
                  analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED' || analyzing
                    ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30 animate-pulse'
                    : analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                    : analysis?.status === 'FAILED'
                    ? 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}>
                  {analyzing ? 'RUNNING' : analysis?.status || 'IDLE • READY'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5 font-medium">
                {getStageInfo(analysis?.current_stage, analysis?.status).desc}
              </p>
            </div>
          </div>

          {/* Percentage & Quick Action */}
          <div className="flex items-center gap-4 self-start sm:self-auto">
            <div className="flex items-baseline gap-1.5">
              <span className="text-[11px] uppercase font-mono text-slate-500">Progress</span>
              <span className={`text-2xl font-black font-mono text-transparent bg-clip-text ${
                analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
                  ? 'bg-gradient-to-r from-emerald-400 to-cyan-400'
                  : 'bg-gradient-to-r from-indigo-300 via-purple-300 to-cyan-300'
              }`}>
                {analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
                  ? 100
                  : analysis?.progress_percent || (analyzing ? 15 : 0)}%
              </span>
            </div>

            <button
              onClick={triggerAnalysis}
              disabled={analyzing || (analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED')}
              className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:opacity-50 text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/20 flex items-center gap-1.5 disabled:cursor-not-allowed"
            >
              {analyzing || analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED' ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-300" />
                  Analyzing...
                </>
              ) : analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS' ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5" />
                  Re-run Analysis
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  Start Analysis
                </>
              )}
            </button>
          </div>
        </div>

        {/* Animated Gradient Progress Bar */}
        <div className="relative z-10 space-y-1.5 mt-4">
          <div className="w-full bg-slate-900/90 rounded-full h-3 p-0.5 overflow-hidden border border-slate-800 shadow-inner">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out relative ${
                analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
                  ? 'bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-400 shadow-[0_0_16px_rgba(16,185,129,0.5)]'
                  : 'bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400 shadow-[0_0_16px_rgba(99,102,241,0.6)]'
              }`}
              style={{
                width: `${
                  analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
                    ? 100
                    : Math.max(analysis?.progress_percent || 0, analyzing ? 15 : 0)}%`
              }}
            >
              {(analyzing || analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED') && (
                <div className="absolute inset-0 bg-white/20 rounded-full animate-pulse" />
              )}
            </div>
          </div>
        </div>

        {/* 5-Stage Stepper Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-3 relative z-10">
          {PIPELINE_STAGES.map((stg, idx) => {
            const stageStatus = getStageStatus(stg.key, analysis?.current_stage, analysis?.status);
            const isCompleted = stageStatus === 'completed';
            const isActive = stageStatus === 'active';

            return (
              <div
                key={stg.key}
                className={`rounded-xl p-3 border transition-all ${
                  isActive
                    ? 'bg-indigo-900/30 border-indigo-500/50 shadow-lg shadow-indigo-500/10 ring-1 ring-indigo-500/30'
                    : isCompleted
                    ? 'bg-emerald-950/20 border-emerald-500/30'
                    : 'bg-slate-900/40 border-slate-800/80 opacity-60'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  {isCompleted ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : isActive ? (
                    <RefreshCw className="w-4 h-4 text-indigo-400 animate-spin shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-slate-600 flex items-center justify-center text-[9px] font-mono text-slate-500 shrink-0">
                      {idx + 1}
                    </div>
                  )}
                  <span
                    className={`text-xs font-bold truncate ${
                      isActive ? 'text-indigo-200' : isCompleted ? 'text-emerald-300' : 'text-slate-400'
                    }`}
                  >
                    {stg.label}
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 leading-tight truncate">
                  {stg.desc}
                </p>
              </div>
            );
          })}
        </div>

        {/* Live Discovered Telemetry Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-800/80 relative z-10 text-xs font-mono">
          <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-slate-500 block text-[10px] uppercase">Scanned Files</span>
            <span className="text-slate-200 font-bold text-sm mt-0.5 flex items-center gap-1.5">
              <FileCode className="w-3.5 h-3.5 text-indigo-400" />
              {analysis?.scanned_files_count || 0}
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-slate-500 block text-[10px] uppercase">Parsed Modules</span>
            <span className="text-slate-200 font-bold text-sm mt-0.5 flex items-center gap-1.5">
              <Code2 className="w-3.5 h-3.5 text-indigo-400" />
              {analysis?.parsed_files_count || 0}
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-slate-500 block text-[10px] uppercase">Discovered Endpoints</span>
            <span className="text-emerald-400 font-bold text-sm mt-0.5 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-emerald-400" />
              {analysis?.endpoint_count || 0}
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-slate-500 block text-[10px] uppercase">Knowledge Graph Nodes</span>
            <span className="text-cyan-400 font-bold text-sm mt-0.5 flex items-center gap-1.5">
              <Network className="w-3.5 h-3.5 text-cyan-400" />
              {analysis?.graph_node_count || 0}
            </span>
          </div>
        </div>

        {/* Failure message if FAILED */}
        {analysis?.status === 'FAILED' && analysis?.error_message && (
          <div className="mt-3 p-3 rounded-xl bg-rose-950/40 border border-rose-900/60 text-xs font-mono text-rose-300">
            <span className="font-bold text-rose-200 block mb-1">Execution Failure:</span>
            <pre className="whitespace-pre-wrap">{analysis.error_message}</pre>
          </div>
        )}
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
        <div className="space-y-6">
          {analysis && (analysis.status === 'COMPLETED' || analysis.status === 'COMPLETED_WITH_WARNINGS') && (
            <div className="glass-card rounded-2xl p-6 border border-emerald-500/20 bg-emerald-950/10 backdrop-blur-xl space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      Static Analysis Complete
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        100% Index
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400">
                      Target repository analyzed and indexed into the Astra semantic knowledge graph.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs font-mono">
                  <span className="text-slate-500">Language:</span>
                  <span className="text-slate-200 font-bold">{analysis.detected_language || 'Python'}</span>
                  <span className="text-slate-600">•</span>
                  <span className="text-slate-500">Framework:</span>
                  <span className="text-indigo-400 font-bold">{formatFrameworkName(analysis.detected_framework)}</span>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs font-mono">
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase">Scanned Files</span>
                  <span className="text-slate-200 font-bold text-base mt-1 flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-indigo-400" />
                    {analysis.scanned_files_count}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase">Parsed Modules</span>
                  <span className="text-slate-200 font-bold text-base mt-1 flex items-center gap-2">
                    <Code2 className="w-4 h-4 text-indigo-400" />
                    {analysis.parsed_files_count}
                  </span>
                </div>
                <button
                  onClick={() => setActiveTab('endpoints')}
                  className="p-3 rounded-xl bg-indigo-950/20 border border-indigo-500/30 hover:border-indigo-500/50 text-left transition-all group"
                >
                  <span className="text-indigo-400 block text-[10px] uppercase flex items-center justify-between">
                    <span>Discovered Routes</span>
                    <ChevronRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                  </span>
                  <span className="text-emerald-400 font-bold text-base mt-1 flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-emerald-400" />
                    {analysis.endpoint_count}
                  </span>
                </button>
                <button
                  onClick={() => setActiveTab('graph')}
                  className="p-3 rounded-xl bg-indigo-950/20 border border-indigo-500/30 hover:border-indigo-500/50 text-left transition-all group"
                >
                  <span className="text-indigo-400 block text-[10px] uppercase flex items-center justify-between">
                    <span>Knowledge Nodes</span>
                    <ChevronRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                  </span>
                  <span className="text-cyan-400 font-bold text-base mt-1 flex items-center gap-2">
                    <Network className="w-4 h-4 text-cyan-400" />
                    {analysis.graph_node_count}
                  </span>
                </button>
              </div>
            </div>
          )}

          {!analysis && (
            <div className="glass-card rounded-2xl p-8 border border-slate-800 text-center space-y-4">
              <Sparkles className="w-10 h-10 text-indigo-400 mx-auto" />
              <div className="space-y-1">
                <h3 className="text-base font-bold text-white">Repository Not Yet Analyzed</h3>
                <p className="text-xs text-slate-400 max-w-md mx-auto">
                  Click the "Analyze Repository" button above to initiate static analysis, discover HTTP routes, and construct the semantic knowledge graph.
                </p>
              </div>
              <button
                onClick={triggerAnalysis}
                disabled={analyzing}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white transition-all shadow-lg shadow-indigo-600/20"
              >
                <Play className="w-3.5 h-3.5 fill-current" /> Analyze Repository Now
              </button>
            </div>
          )}

          <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
            <h3 className="text-base font-bold text-white">Project Infrastructure & Execution Platform</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Astra executes synthetic HTTP test cases deterministically against target applications with full SSRF protection and secret redaction.
            </p>
          </div>
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
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Trigger repository analysis to construct the code dependency graph and index modules, functions, and endpoints.
              </p>
            </div>
          ) : (
            <KnowledgeGraphVisualizer
              graph={graph}
              projectName={project?.name}
            />
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
                      <td className="px-4 py-3 text-slate-400">{Number(run.duration_ms ?? 0).toFixed(0)} ms</td>
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
