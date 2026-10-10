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
import { TestStatusBadge, type TestStatus } from '../components/common/TestStatusBadge';
import { Button } from '../components/common/Button';

const mapRunStatusToBadge = (status?: string): TestStatus => {
  switch ((status || '').toUpperCase()) {
    case 'COMPLETED':
    case 'PASSED':
    case 'PASS':
      return 'passed';
    case 'FAILED':
    case 'FAIL':
      return 'failed';
    case 'RUNNING':
    case 'STARTING':
    case 'QUEUED':
      return 'running';
    case 'ERROR':
    case 'ENVIRONMENT_ERROR':
      return 'error';
    case 'FLAKY':
      return 'flaky';
    default:
      return 'skipped';
  }
};

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
      <div className="flex items-center gap-3 text-xs text-muted">
        <Link to="/projects" className="hover:text-primary transition-colors flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> Projects
        </Link>
        <span>/</span>
        <span className="text-primary font-semibold">{project.name}</span>
      </div>

      {/* Project Banner Card */}
      <div className="glass-card rounded-2xl p-6 border border-border space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-extrabold text-primary">{project.name}</h1>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-brand/10 text-brand border border-brand/20">
                {formatFrameworkName(project.language_framework)}
              </span>
            </div>
            <p className="text-xs text-secondary">{project.description || 'No description provided.'}</p>
          </div>

          <div className="flex items-center gap-3">
            {/* The single Volt Lime highlight action button on this screen */}
            <Button
              variant="accent"
              size="md"
              onClick={triggerAnalysis}
              disabled={analyzing || (analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED')}
              isLoading={analyzing || analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED'}
              leftIcon={<Play className="w-3.5 h-3.5 fill-current" />}
            >
              {analyzing || analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED'
                ? `Analyzing (${analysis?.progress_percent ?? 0}%)`
                : analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
                ? 'Re-run Analysis'
                : 'Analyze Repository'}
            </Button>

            <Button
              variant="secondary"
              size="md"
              onClick={() => setIsDrawerOpen(true)}
              disabled={!analysis || endpoints.length === 0}
              leftIcon={<Sliders className="w-3.5 h-3.5 text-brand" />}
            >
              Advanced Suite Generator
            </Button>

            <a
              href={project.repository_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-surface border border-border hover:bg-raised text-xs font-medium text-secondary hover:text-primary transition-colors shrink-0"
            >
              <ExternalLink className="w-3.5 h-3.5 text-brand" /> View Repository
            </a>
          </div>
        </div>

        {/* Metadata Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-border text-xs font-mono text-secondary">
          <div>
            <span className="text-muted block text-[10px] uppercase">Default Branch</span>
            <span className="text-primary flex items-center gap-1 font-semibold mt-0.5">
              <GitBranch className="w-3.5 h-3.5 text-muted" /> {project.default_branch}
            </span>
          </div>
          <div>
            <span className="text-muted block text-[10px] uppercase">Project Owner</span>
            <span className="text-primary font-semibold mt-0.5 block truncate">
              {project.owner?.full_name || 'System'}
            </span>
          </div>
          <div>
            <span className="text-muted block text-[10px] uppercase">Latest Analysis SHA</span>
            <span className="text-primary font-semibold mt-0.5 block font-mono text-[11px] truncate">
              {analysis?.commit_sha ? analysis.commit_sha.substring(0, 8) : 'Not Analyzed'}
            </span>
          </div>
          <div>
            <span className="text-muted block text-[10px] uppercase">Detected Framework</span>
            <span className="text-brand font-semibold mt-0.5 block">
              {formatFrameworkName(analysis?.detected_framework)}
            </span>
          </div>
        </div>
      </div>

      {/* Real-time Analysis Progress Banner Card - Always Visible */}
      <div className={`glass-card rounded-2xl p-6 border transition-all duration-300 relative overflow-hidden ${
        analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED' || analyzing
          ? 'border-brand/40 bg-surface shadow-brand-glow'
          : analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
          ? 'border-border bg-surface'
          : analysis?.status === 'FAILED'
          ? 'border-status-failed-border bg-surface'
          : 'border-border bg-surface'
      }`}>
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 relative z-10">
          <div className="flex items-center gap-3">
            {analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED' || analyzing ? (
              <span className="relative flex h-3.5 w-3.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-brand shadow-[0_0_8px_var(--brand)]"></span>
              </span>
            ) : analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS' ? (
              <div className="w-5 h-5 rounded-full bg-status-passed-bg border border-status-passed-border flex items-center justify-center text-status-passed">
                <Check className="w-3 h-3 stroke-[3]" />
              </div>
            ) : analysis?.status === 'FAILED' ? (
              <div className="w-5 h-5 rounded-full bg-status-failed-bg border border-status-failed-border flex items-center justify-center text-status-failed">
                <AlertTriangle className="w-3 h-3" />
              </div>
            ) : (
              <div className="w-5 h-5 rounded-full bg-brand/10 border border-brand/20 flex items-center justify-center text-brand">
                <Play className="w-2.5 h-2.5 fill-current ml-0.5" />
              </div>
            )}
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-primary tracking-wide">
                  Repository Static Analysis Pipeline
                </h3>
                <TestStatusBadge
                  status={
                    analyzing || analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED'
                      ? 'running'
                      : analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
                      ? 'passed'
                      : analysis?.status === 'FAILED'
                      ? 'failed'
                      : 'skipped'
                  }
                  label={analyzing ? 'RUNNING' : analysis?.status || 'IDLE • READY'}
                />
              </div>
              <p className="text-xs text-secondary mt-0.5 font-medium">
                {getStageInfo(analysis?.current_stage, analysis?.status).desc}
              </p>
            </div>
          </div>

          {/* Percentage & Quick Action */}
          <div className="flex items-center gap-4 self-start sm:self-auto">
            <div className="flex items-baseline gap-1.5">
              <span className="text-[11px] uppercase font-mono text-muted">Progress</span>
              <span className="text-2xl font-black font-mono text-accent">
                {analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
                  ? 100
                  : analysis?.progress_percent || (analyzing ? 15 : 0)}%
              </span>
            </div>

            <Button
              variant={analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS' ? 'secondary' : 'accent'}
              size="sm"
              onClick={triggerAnalysis}
              disabled={analyzing || (analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED')}
              isLoading={analyzing || analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED'}
              leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${analyzing ? 'animate-spin' : ''}`} />}
            >
              {analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
                ? 'Re-run Analysis'
                : 'Start Analysis'}
            </Button>
          </div>
        </div>

        {/* Animated Gradient Progress Bar */}
        <div className="relative z-10 space-y-1.5 mt-4">
          <div className="w-full bg-raised rounded-full h-2.5 p-0.5 overflow-hidden border border-border">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out relative ${
                analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
                  ? 'bg-status-passed shadow-[0_0_12px_var(--status-passed)]'
                  : 'bg-brand shadow-brand-glow'
              }`}
              style={{
                width: `${
                  analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
                    ? 100
                    : Math.max(analysis?.progress_percent || 0, analyzing ? 15 : 0)}%`
              }}
            >
              {(analyzing || analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED') && (
                <div className="absolute inset-0 bg-white/30 rounded-full animate-pulse" />
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
                    ? 'bg-brand/10 border-brand/50 shadow-brand-glow ring-1 ring-brand/30'
                    : isCompleted
                    ? 'bg-status-passed-bg border-status-passed-border'
                    : 'bg-raised border-border opacity-70'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  {isCompleted ? (
                    <CheckCircle2 className="w-4 h-4 text-status-passed shrink-0" />
                  ) : isActive ? (
                    <RefreshCw className="w-4 h-4 text-brand animate-spin shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-[9px] font-mono text-muted shrink-0">
                      {idx + 1}
                    </div>
                  )}
                  <span
                    className={`text-xs font-bold truncate ${
                      isActive ? 'text-primary' : isCompleted ? 'text-status-passed' : 'text-muted'
                    }`}
                  >
                    {stg.label}
                  </span>
                </div>
                <p className="text-[10px] text-secondary leading-tight truncate">
                  {stg.desc}
                </p>
              </div>
            );
          })}
        </div>

        {/* Live Discovered Telemetry Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-border relative z-10 text-xs font-mono">
          <div className="p-2.5 rounded-xl bg-raised border border-border">
            <span className="text-muted block text-[10px] uppercase">Scanned Files</span>
            <span className="text-primary font-bold text-sm mt-0.5 flex items-center gap-1.5">
              <FileCode className="w-3.5 h-3.5 text-brand" />
              {analysis?.scanned_files_count || 0}
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-raised border border-border">
            <span className="text-muted block text-[10px] uppercase">Parsed Modules</span>
            <span className="text-primary font-bold text-sm mt-0.5 flex items-center gap-1.5">
              <Code2 className="w-3.5 h-3.5 text-brand" />
              {analysis?.parsed_files_count || 0}
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-raised border border-border">
            <span className="text-muted block text-[10px] uppercase">Discovered Endpoints</span>
            <span className="text-status-passed font-bold text-sm mt-0.5 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-status-passed" />
              {analysis?.endpoint_count || 0}
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-raised border border-border">
            <span className="text-muted block text-[10px] uppercase">Knowledge Graph Nodes</span>
            <span className="text-brand font-bold text-sm mt-0.5 flex items-center gap-1.5">
              <Network className="w-3.5 h-3.5 text-brand" />
              {analysis?.graph_node_count || 0}
            </span>
          </div>
        </div>

        {/* Failure message if FAILED */}
        {analysis?.status === 'FAILED' && analysis?.error_message && (
          <div className="mt-3 p-3 rounded-xl bg-status-failed-bg border border-status-failed-border text-xs font-mono text-status-failed">
            <span className="font-bold block mb-1">Execution Failure:</span>
            <pre className="whitespace-pre-wrap">{analysis.error_message}</pre>
          </div>
        )}
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-border gap-6 text-sm font-medium text-secondary">
        <button
          onClick={() => setActiveTab('overview')}
          className={`pb-3 transition-all relative ${
            activeTab === 'overview' ? 'text-brand font-bold border-b-2 border-brand' : 'hover:text-primary'
          }`}
        >
          Workspace Overview
        </button>
        <button
          onClick={() => setActiveTab('endpoints')}
          className={`pb-3 transition-all relative flex items-center gap-1.5 ${
            activeTab === 'endpoints' ? 'text-brand font-bold border-b-2 border-brand' : 'hover:text-primary'
          }`}
        >
          <Code2 className="w-4 h-4" /> Discovered Endpoints ({endpoints.length})
        </button>
        <button
          onClick={() => setActiveTab('graph')}
          className={`pb-3 transition-all relative flex items-center gap-1.5 ${
            activeTab === 'graph' ? 'text-brand font-bold border-b-2 border-brand' : 'hover:text-primary'
          }`}
        >
          <Network className="w-4 h-4" /> Knowledge Graph ({graph?.nodes.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('testruns')}
          className={`pb-3 transition-all relative flex items-center gap-1.5 ${
            activeTab === 'testruns' ? 'text-brand font-bold border-b-2 border-brand' : 'hover:text-primary'
          }`}
        >
          <Activity className="w-4 h-4" /> Test Executions ({testRuns.length})
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {analysis && (analysis.status === 'COMPLETED' || analysis.status === 'COMPLETED_WITH_WARNINGS') && (
            <div className="glass-card rounded-2xl p-6 border border-border bg-surface space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-status-passed-bg border border-status-passed-border flex items-center justify-center text-status-passed">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-primary flex items-center gap-2">
                      Static Analysis Complete
                      <TestStatusBadge status="passed" label="100% Index" />
                    </h3>
                    <p className="text-xs text-secondary">
                      Target repository analyzed and indexed into the Astra semantic knowledge graph.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs font-mono">
                  <span className="text-muted">Language:</span>
                  <span className="text-primary font-bold">{analysis.detected_language || 'Python'}</span>
                  <span className="text-border">•</span>
                  <span className="text-muted">Framework:</span>
                  <span className="text-brand font-bold">{formatFrameworkName(analysis.detected_framework)}</span>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs font-mono">
                <div className="p-3 rounded-xl bg-raised border border-border">
                  <span className="text-muted block text-[10px] uppercase">Scanned Files</span>
                  <span className="text-primary font-bold text-base mt-1 flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-brand" />
                    {analysis.scanned_files_count}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-raised border border-border">
                  <span className="text-muted block text-[10px] uppercase">Parsed Modules</span>
                  <span className="text-primary font-bold text-base mt-1 flex items-center gap-2">
                    <Code2 className="w-4 h-4 text-brand" />
                    {analysis.parsed_files_count}
                  </span>
                </div>
                <button
                  onClick={() => setActiveTab('endpoints')}
                  className="p-3 rounded-xl bg-raised border border-border hover:border-brand/40 text-left transition-all group"
                >
                  <span className="text-muted block text-[10px] uppercase flex items-center justify-between">
                    <span>Discovered Routes</span>
                    <ChevronRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform text-brand" />
                  </span>
                  <span className="text-status-passed font-bold text-base mt-1 flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-status-passed" />
                    {analysis.endpoint_count}
                  </span>
                </button>
                <button
                  onClick={() => setActiveTab('graph')}
                  className="p-3 rounded-xl bg-raised border border-border hover:border-brand/40 text-left transition-all group"
                >
                  <span className="text-muted block text-[10px] uppercase flex items-center justify-between">
                    <span>Knowledge Nodes</span>
                    <ChevronRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform text-brand" />
                  </span>
                  <span className="text-brand font-bold text-base mt-1 flex items-center gap-2">
                    <Network className="w-4 h-4 text-brand" />
                    {analysis.graph_node_count}
                  </span>
                </button>
              </div>
            </div>
          )}

          {!analysis && (
            <div className="glass-card rounded-2xl p-8 border border-border text-center space-y-4">
              <Sparkles className="w-10 h-10 text-brand mx-auto" />
              <div className="space-y-1">
                <h3 className="text-base font-bold text-primary">Repository Not Yet Analyzed</h3>
                <p className="text-xs text-secondary max-w-md mx-auto">
                  Click the "Analyze Repository" button to initiate static analysis, discover HTTP routes, and construct the semantic knowledge graph.
                </p>
              </div>
              <Button
                variant="accent"
                onClick={triggerAnalysis}
                isLoading={analyzing}
                leftIcon={<Play className="w-3.5 h-3.5 fill-current" />}
              >
                Analyze Repository Now
              </Button>
            </div>
          )}

          <div className="glass-card rounded-2xl p-6 border border-border space-y-4">
            <h3 className="text-base font-bold text-primary">Project Infrastructure & Execution Platform</h3>
            <p className="text-xs text-secondary leading-relaxed">
              Astra executes synthetic HTTP test cases deterministically against target applications with full SSRF protection and secret redaction.
            </p>
          </div>
        </div>
      )}

      {activeTab === 'endpoints' && (
        <div className="space-y-4">
          {endpoints.length === 0 ? (
            <div className="glass-card rounded-2xl p-8 text-center space-y-3 border border-border">
              <Cpu className="w-10 h-10 text-muted mx-auto" />
              <h3 className="text-base font-bold text-primary">No Endpoints Discovered Yet</h3>
            </div>
          ) : (
            <div className="glass-card rounded-2xl border border-border overflow-hidden">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-raised text-muted border-b border-border uppercase text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Method</th>
                    <th className="px-4 py-3">Path</th>
                    <th className="px-4 py-3">Handler Function</th>
                    <th className="px-4 py-3">Source Location</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border text-secondary">
                  {endpoints.map((ep) => (
                    <tr key={ep.id} className="hover:bg-raised/60 transition-colors">
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded font-bold border ${getMethodBadgeClass(ep.method)}`}>
                          {ep.method}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-primary font-semibold">{ep.path}</td>
                      <td className="px-4 py-3 text-brand">{ep.function_name}()</td>
                      <td className="px-4 py-3 text-muted flex items-center gap-1">
                        <FileCode className="w-3.5 h-3.5 text-muted" />
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
            <div className="glass-card rounded-2xl p-8 text-center space-y-3 border border-border">
              <Network className="w-10 h-10 text-muted mx-auto" />
              <h3 className="text-base font-bold text-primary">Knowledge Graph Not Available</h3>
              <p className="text-xs text-secondary max-w-md mx-auto">
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
              <h3 className="text-base font-bold text-primary">Test Suites & Execution Telemetry</h3>
              <p className="text-xs text-secondary">Generate synthetic test specifications and execute async HTTP test runs.</p>
            </div>

            <Button
              variant="secondary"
              onClick={generateTestSuite}
              disabled={generatingSuite || endpoints.length === 0}
              isLoading={generatingSuite}
              leftIcon={<Zap className="w-4 h-4 text-accent" />}
            >
              Generate Synthetic Suite
            </Button>
          </div>

          {/* Generated Test Suites */}
          <div className="glass-card rounded-2xl p-5 border border-border space-y-3">
            <h4 className="text-sm font-bold text-primary">Generated Test Suites ({suites.length})</h4>
            {suites.length === 0 ? (
              <p className="text-xs text-muted">No test suites generated yet. Click "Generate Synthetic Suite" above.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {suites.map(s => (
                  <div key={s.id} className="p-4 rounded-xl bg-raised border border-border flex items-center justify-between text-xs font-mono">
                    <div className="space-y-1">
                      <span className="text-primary font-bold block">{s.name}</span>
                      <span className="text-muted text-[10px] block">{s.total_cases} test cases • v{s.version}</span>
                    </div>
                    <Button
                      variant="accent"
                      size="sm"
                      onClick={() => dispatchRun(s.id)}
                      disabled={dispatchingRun}
                      leftIcon={<Play className="w-3 h-3 fill-current" />}
                    >
                      Run Suite
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Past Execution Runs Table */}
          <div className="glass-card rounded-2xl border border-border overflow-hidden space-y-3 p-5">
            <h4 className="text-sm font-bold text-primary">Execution History ({testRuns.length})</h4>
            {testRuns.length === 0 ? (
              <p className="text-xs text-muted">No test runs executed yet.</p>
            ) : (
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-raised text-muted border-b border-border uppercase text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Run ID</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Tests Passed / Total</th>
                    <th className="px-4 py-3">Duration</th>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border text-secondary">
                  {testRuns.map(run => (
                    <tr key={run.id} className="hover:bg-raised/60 transition-colors">
                      <td className="px-4 py-3 font-bold text-primary font-mono">#{run.id.substring(0, 8)}</td>
                      <td className="px-4 py-3">
                        <TestStatusBadge
                          status={mapRunStatusToBadge(run.status)}
                          label={run.status}
                        />
                      </td>
                      <td className="px-4 py-3 text-primary font-bold">
                        <span className="text-status-passed">{run.passed_tests}</span> / {run.total_tests}
                      </td>
                      <td className="px-4 py-3 text-secondary">{Number(run.duration_ms ?? 0).toFixed(0)} ms</td>
                      <td className="px-4 py-3 text-muted">{new Date(run.created_at).toLocaleTimeString()}</td>
                      <td className="px-4 py-3">
                        <Link
                          to={`/projects/${project.id}/test-runs/${run.id}`}
                          className="inline-flex items-center gap-1 text-brand hover:text-brand-hover font-bold transition-colors"
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
