import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ExternalLink,
  GitBranch,
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
  Sparkles,
  Eye,
  Server,
} from 'lucide-react';
import { api } from '../services/api';
import { TestGenerationDrawer } from '../components/TestGenerationDrawer';
import { TestSuiteViewerDrawer } from '../components/TestSuiteViewerDrawer';
import { SandboxServerControl } from '../components/SandboxServerControl';
import { KnowledgeGraphVisualizer } from '../components/KnowledgeGraphVisualizer';
import { TestStatusBadge, type TestStatus } from '../components/common/TestStatusBadge';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { Input } from '../components/common/Input';

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

interface DiscoveredFunction {
  function_id: string;
  qualified_name: string;
  file_path: string;
  line_number: number;
  parameters: Array<{ name: string; type_annotation?: string; has_default?: boolean }>;
  return_schema: string;
  docstring: string | null;
  side_effects: string[];
  called_functions: string[];
  purity_estimate: number;
  cyclomatic_complexity: number;
  is_async: boolean;
}

interface UnitTestOutcome {
  nodeid: string;
  outcome: string;
  duration: number;
  message?: string;
}

interface UnitTestRunResult {
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  skipped_tests: number;
  duration_ms: number;
  coverage_percent: number;
  test_outcomes: UnitTestOutcome[];
  raw_stdout: string;
  exit_code: number;
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
  const navigate = useNavigate();
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
  const [selectedSuiteForRun, setSelectedSuiteForRun] = useState<TestSuite | null>(null);
  const [viewingSuite, setViewingSuite] = useState<TestSuite | null>(null);
  const [serverIsRunning, setServerIsRunning] = useState(false);
  const [serverPort, setServerPort] = useState<number | null>(null);
  const [serverWarningModalOpen, setServerWarningModalOpen] = useState(false);
  const [pendingRunSuite, setPendingRunSuite] = useState<TestSuite | null>(null);
  const [targetBaseUrl, setTargetBaseUrl] = useState('http://localhost:5000');
  const [healthCheckPath, setHealthCheckPath] = useState('/health');

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

  useEffect(() => {
    const hasRunningTests = testRuns.some(
      (r) => r.status === 'RUNNING' || r.status === 'STARTING' || r.status === 'PENDING'
    );
    if (!hasRunningTests) return;

    const timer = setInterval(() => {
      fetchTestRuns();
    }, 1200);

    return () => clearInterval(timer);
  }, [testRuns, id]);

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
        name: `Synthetic Suite v${suites.length + 1}`,
      });
      fetchTestSuites();
      alert(`Successfully generated synthetic test suite '${res.data.name}' with ${res.data.total_cases} test cases!`);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to generate test suite. Ensure repository is analyzed first.');
    } finally {
      setGeneratingSuite(false);
    }
  };

  const handleServerStateChange = (isRunning: boolean, port: number | null) => {
    setServerIsRunning(isRunning);
    setServerPort(port);
    if (isRunning && port) {
      setTargetBaseUrl(`http://localhost:${port}`);
    }
  };

  const handleInitiateRun = (suite: TestSuite) => {
    if (!serverIsRunning) {
      setPendingRunSuite(suite);
      setServerWarningModalOpen(true);
      return;
    }
    if (serverPort) {
      setTargetBaseUrl(`http://localhost:${serverPort}`);
    }
    setSelectedSuiteForRun(suite);
  };

  const dispatchRun = async (suiteId: string, customUrl?: string, customHealthPath?: string) => {
    setDispatchingRun(true);
    const resolvedUrl = (customUrl || targetBaseUrl || 'http://localhost:5000').trim();
    const resolvedHealth = (customHealthPath || healthCheckPath || '/health').trim();
    try {
      const res = await api.post(`/projects/${id}/test-runs`, {
        suite_id: suiteId,
        target_base_url: resolvedUrl,
        environment_type: 'LOCAL_SANDBOX',
        health_check_path: resolvedHealth,
      });
      fetchTestRuns();
      setSelectedSuiteForRun(null);
      if (res.data?.id) {
        navigate(`/projects/${id}/test-runs/${res.data.id}`);
      } else {
        setActiveTab('testruns');
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to dispatch test run.');
    } finally {
      setDispatchingRun(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-20 text-muted text-sm flex flex-col items-center gap-3">
        <div className="w-6 h-6 border-2 border-brand border-t-transparent rounded-full animate-spin" />
        <span>Loading project details...</span>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="bg-card rounded-2xl p-8 text-center space-y-4 border border-border-card shadow-card max-w-md mx-auto">
        <Info className="w-10 h-10 text-status-failed mx-auto" />
        <h3 className="text-lg font-bold text-primary">Project Not Found</h3>
        <p className="text-xs text-secondary">{error}</p>
        <Link to="/projects" className="inline-block text-xs font-semibold text-brand hover:underline">
          &larr; Return to Projects List
        </Link>
      </div>
    );
  }

  const getMethodBadgeClass = (method: string) => {
    switch (method.toUpperCase()) {
      case 'GET':
        return 'bg-status-passed-bg text-status-passed border border-status-passed/30';
      case 'POST':
        return 'bg-brand/10 text-brand border border-brand/30';
      case 'PUT':
        return 'bg-status-flaky-bg text-status-flaky border border-status-flaky/30';
      case 'DELETE':
        return 'bg-status-failed-bg text-status-failed border border-status-failed/30';
      default:
        return 'bg-status-skipped-bg text-status-skipped border border-status-skipped/30';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb Header */}
      <div className="flex items-center gap-2 text-xs text-muted">
        <Link to="/projects" className="hover:text-primary transition-colors flex items-center gap-1 font-medium">
          <ArrowLeft className="w-3.5 h-3.5" /> Projects
        </Link>
        <span>/</span>
        <span className="text-primary font-semibold">{project.name}</span>
      </div>

      {/* Project Banner Card */}
      <div className="glass-card border-t-4 border-t-brand rounded-2xl p-6 shadow-glass space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-2xl font-bold text-primary tracking-tight">{project.name}</h1>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-brand/10 text-brand border border-brand/20">
                {formatFrameworkName(project.language_framework)}
              </span>
            </div>
            <p className="text-xs text-secondary">{project.description || 'No description provided.'}</p>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <Button
              variant="primary"
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
              className="inline-flex items-center gap-1.5 px-3.5 h-10 rounded-lg bg-card border border-border-field hover:bg-hover text-xs font-semibold text-primary transition-colors shrink-0"
            >
              <ExternalLink className="w-3.5 h-3.5 text-brand" /> View Repository
            </a>
          </div>
        </div>

        {/* Metadata Strip with 32px Icon Chips */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-border-card text-xs">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand/10 border border-brand/20 flex items-center justify-center text-brand shrink-0">
              <GitBranch className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-muted block text-[10px] uppercase font-semibold">Default Branch</span>
              <span className="text-primary font-semibold truncate block mt-0.5">{project.default_branch}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-secondaryAccent/10 border border-secondaryAccent/20 flex items-center justify-center text-secondaryAccent shrink-0">
              <Shield className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-muted block text-[10px] uppercase font-semibold">Project Owner</span>
              <span className="text-primary font-semibold truncate block mt-0.5">
                {project.owner?.full_name || 'System Admin'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand/10 border border-brand/20 flex items-center justify-center text-brand shrink-0">
              <FileCode className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-muted block text-[10px] uppercase font-semibold">Latest Analysis SHA</span>
              <span className="text-primary font-mono text-[11px] font-semibold truncate block mt-0.5">
                {analysis?.commit_sha ? analysis.commit_sha.substring(0, 8) : 'Not Analyzed'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-secondaryAccent/10 border border-secondaryAccent/20 flex items-center justify-center text-secondaryAccent shrink-0">
              <Layers className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-muted block text-[10px] uppercase font-semibold">Detected Stack</span>
              <span className="text-primary font-semibold truncate block mt-0.5">
                {formatFrameworkName(analysis?.detected_framework)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Real-time Analysis Progress Banner Card - Clean & Minimalist */}
      <div className={`glass-card rounded-2xl p-6 shadow-card transition-all duration-200 relative overflow-hidden border ${
        analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED' || analyzing
          ? 'border-brand/40 ring-1 ring-brand/20'
          : analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
          ? 'border-emerald-500/25'
          : analysis?.status === 'FAILED'
          ? 'border-rose-500/30'
          : 'border-border-card'
      }`}>
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 relative z-10">
          <div className="flex items-center gap-3">
            {analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED' || analyzing ? (
              <div className="w-9 h-9 rounded-xl bg-brand/10 text-brand border border-brand/25 flex items-center justify-center shrink-0">
                <RefreshCw className="w-4 h-4 animate-spin" />
              </div>
            ) : analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS' ? (
              <div className="w-9 h-9 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 border border-emerald-200/80 dark:border-emerald-800/50 flex items-center justify-center shrink-0">
                <Check className="w-4 h-4 stroke-[2.5]" />
              </div>
            ) : analysis?.status === 'FAILED' ? (
              <div className="w-9 h-9 rounded-xl bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 border border-rose-200/80 dark:border-rose-800/50 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-4 h-4" />
              </div>
            ) : (
              <div className="w-9 h-9 rounded-xl bg-brand/10 text-brand border border-brand/25 flex items-center justify-center shrink-0">
                <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
              </div>
            )}
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h3 className="text-base font-semibold text-primary tracking-tight">
                  Repository Static Analysis Pipeline
                </h3>
                {analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS' ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/40">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    COMPLETED
                  </span>
                ) : analysis?.status === 'RUNNING' || analyzing ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand/10 text-brand border border-brand/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-brand animate-ping" />
                    RUNNING
                  </span>
                ) : analysis?.status === 'FAILED' ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800/40">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                    FAILED
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-field text-secondary border border-border-card">
                    IDLE • READY
                  </span>
                )}
              </div>
              <p className="text-xs text-secondary mt-0.5">
                {getStageInfo(analysis?.current_stage, analysis?.status).desc}
              </p>
            </div>
          </div>

          {/* Percentage & Action Button */}
          <div className="flex items-center gap-4 self-start sm:self-auto">
            <div className="flex items-baseline gap-1.5">
              <span className="text-[11px] uppercase font-semibold text-muted tracking-wider">Progress</span>
              <span className="text-2xl font-bold font-mono text-primary">
                {analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
                  ? 100
                  : analysis?.progress_percent || (analyzing ? 15 : 0)}%
              </span>
            </div>

            <Button
              variant="secondary"
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

        {/* Clean Sleek Progress Bar */}
        <div className="relative z-10 space-y-1 mt-4">
          <div className="w-full bg-field rounded-full h-2 overflow-hidden border border-border-card">
            <div
              className={`h-full rounded-full transition-all duration-500 ease-out ${
                analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
                  ? 'bg-emerald-500'
                  : 'bg-brand'
              }`}
              style={{
                width: `${
                  analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS'
                    ? 100
                    : Math.max(analysis?.progress_percent || 0, analyzing ? 15 : 0)}%`,
              }}
            />
          </div>
        </div>

        {/* 5-Stage Stepper Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 pt-4 relative z-10">
          {PIPELINE_STAGES.map((stg, idx) => {
            const stageStatus = getStageStatus(stg.key, analysis?.current_stage, analysis?.status);
            const isCompleted = stageStatus === 'completed';
            const isActive = stageStatus === 'active';

            return (
              <div
                key={stg.key}
                className={`rounded-xl p-3 border transition-colors ${
                  isActive
                    ? 'bg-brand/5 border-brand/40 shadow-sm ring-1 ring-brand/20'
                    : isCompleted
                    ? 'bg-card border-emerald-500/25 dark:border-emerald-500/20 shadow-sm'
                    : 'bg-field/50 border-border-card opacity-60'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  {isCompleted ? (
                    <div className="w-4 h-4 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                      <Check className="w-2.5 h-2.5 stroke-[3]" />
                    </div>
                  ) : isActive ? (
                    <RefreshCw className="w-3.5 h-3.5 text-brand animate-spin shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-border-field bg-card flex items-center justify-center text-[9px] font-semibold text-muted shrink-0">
                      {idx + 1}
                    </div>
                  )}
                  <span
                    className={`text-xs font-medium truncate ${
                      isActive ? 'text-brand font-semibold' : isCompleted ? 'text-primary' : 'text-secondary'
                    }`}
                  >
                    {stg.label}
                  </span>
                </div>
                <p className="text-[10px] text-muted leading-tight truncate">
                  {stg.desc}
                </p>
              </div>
            );
          })}
        </div>

        {/* Live Discovered Telemetry Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-border-card relative z-10 text-xs">
          {/* Scanned Files */}
          <div className="p-3 rounded-xl bg-field/60 border border-border-card flex items-center gap-3 hover:bg-field transition-colors">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
              <FileCode className="w-4 h-4" />
            </div>
            <div>
              <span className="text-muted block text-[10px] uppercase font-semibold">Scanned Files</span>
              <span className="text-primary font-bold text-base mt-0.5 block font-mono">
                {analysis?.scanned_files_count || 0}
              </span>
            </div>
          </div>

          {/* Parsed Modules */}
          <div className="p-3 rounded-xl bg-field/60 border border-border-card flex items-center gap-3 hover:bg-field transition-colors">
            <div className="w-8 h-8 rounded-lg bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0">
              <Code2 className="w-4 h-4" />
            </div>
            <div>
              <span className="text-muted block text-[10px] uppercase font-semibold">Parsed Modules</span>
              <span className="text-primary font-bold text-base mt-0.5 block font-mono">
                {analysis?.parsed_files_count || 0}
              </span>
            </div>
          </div>

          {/* Discovered Endpoints */}
          <div className="p-3 rounded-xl bg-field/60 border border-border-card flex items-center gap-3 hover:bg-field transition-colors">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <span className="text-muted block text-[10px] uppercase font-semibold">Discovered Endpoints</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-bold text-base mt-0.5 block font-mono">
                {analysis?.endpoint_count || 0}
              </span>
            </div>
          </div>

          {/* Knowledge Graph Nodes */}
          <div className="p-3 rounded-xl bg-field/60 border border-border-card flex items-center gap-3 hover:bg-field transition-colors">
            <div className="w-8 h-8 rounded-lg bg-cyan-50 dark:bg-cyan-950/40 text-cyan-600 dark:text-cyan-400 flex items-center justify-center shrink-0">
              <Network className="w-4 h-4" />
            </div>
            <div>
              <span className="text-muted block text-[10px] uppercase font-semibold">Knowledge Graph Nodes</span>
              <span className="text-primary font-bold text-base mt-0.5 block font-mono">
                {analysis?.graph_node_count || 0}
              </span>
            </div>
          </div>
        </div>

        {/* Failure message if FAILED */}
        {analysis?.status === 'FAILED' && analysis?.error_message && (
          <div className="mt-4 p-3.5 rounded-xl bg-status-failed-bg border border-status-failed/30 text-xs text-status-failed">
            <span className="font-bold block mb-1">Execution Failure:</span>
            <pre className="font-mono whitespace-pre-wrap">{analysis.error_message}</pre>
          </div>
        )}
      </div>

      {/* Segmented Solid Tabs Navigation */}
      <div className="p-1.5 rounded-2xl bg-field border border-border-card flex flex-wrap gap-1 text-xs font-semibold shadow-inner">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 rounded-xl transition-all ${
            activeTab === 'overview'
              ? 'bg-card text-brand font-bold shadow-sm border border-border-card'
              : 'text-secondary hover:text-primary hover:bg-hover'
          }`}
        >
          Workspace Overview
        </button>
        <button
          onClick={() => setActiveTab('endpoints')}
          className={`px-4 py-2 rounded-xl transition-all flex items-center gap-1.5 ${
            activeTab === 'endpoints'
              ? 'bg-card text-brand font-bold shadow-sm border border-border-card'
              : 'text-secondary hover:text-primary hover:bg-hover'
          }`}
        >
          <Code2 className="w-3.5 h-3.5" /> Discovered Endpoints ({endpoints.length})
        </button>
        <button
          onClick={() => setActiveTab('graph')}
          className={`px-4 py-2 rounded-xl transition-all flex items-center gap-1.5 ${
            activeTab === 'graph'
              ? 'bg-card text-brand font-bold shadow-sm border border-border-card'
              : 'text-secondary hover:text-primary hover:bg-hover'
          }`}
        >
          <Network className="w-3.5 h-3.5" /> Knowledge Graph ({graph?.nodes.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('testruns')}
          className={`px-4 py-2 rounded-xl transition-all flex items-center gap-1.5 ${
            activeTab === 'testruns'
              ? 'bg-card text-brand font-bold shadow-sm border border-border-card'
              : 'text-secondary hover:text-primary hover:bg-hover'
          }`}
        >
          <Activity className="w-3.5 h-3.5" /> Test Executions ({testRuns.length})
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {analysis && (analysis.status === 'COMPLETED' || analysis.status === 'COMPLETED_WITH_WARNINGS') && (
            <div className="bg-card rounded-2xl p-6 border border-border-card shadow-card space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-status-passed-bg border border-status-passed/30 flex items-center justify-center text-status-passed">
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

                <div className="flex items-center gap-2 text-xs">
                  <span className="text-muted font-medium">Language:</span>
                  <span className="text-primary font-bold">{analysis.detected_language || 'Python'}</span>
                  <span className="text-muted">•</span>
                  <span className="text-muted font-medium">Framework:</span>
                  <span className="text-brand font-bold">{formatFrameworkName(analysis.detected_framework)}</span>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
                <div className="p-3.5 rounded-xl bg-field border border-border-card">
                  <span className="text-muted block text-[10px] uppercase font-semibold">Scanned Files</span>
                  <span className="text-primary font-bold text-base mt-1 flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-brand" />
                    {analysis.scanned_files_count}
                  </span>
                </div>
                <div className="p-3.5 rounded-xl bg-field border border-border-card">
                  <span className="text-muted block text-[10px] uppercase font-semibold">Parsed Modules</span>
                  <span className="text-primary font-bold text-base mt-1 flex items-center gap-2">
                    <Code2 className="w-4 h-4 text-brand" />
                    {analysis.parsed_files_count}
                  </span>
                </div>
                <button
                  onClick={() => setActiveTab('endpoints')}
                  className="p-3.5 rounded-xl bg-field border border-border-card hover:border-brand text-left transition-colors group"
                >
                  <span className="text-muted block text-[10px] uppercase font-semibold flex items-center justify-between">
                    <span>Discovered Routes</span>
                    <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform text-brand" />
                  </span>
                  <span className="text-status-passed font-bold text-base mt-1 flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-status-passed" />
                    {analysis.endpoint_count}
                  </span>
                </button>
                <button
                  onClick={() => setActiveTab('graph')}
                  className="p-3.5 rounded-xl bg-field border border-border-card hover:border-brand text-left transition-colors group"
                >
                  <span className="text-muted block text-[10px] uppercase font-semibold flex items-center justify-between">
                    <span>Knowledge Nodes</span>
                    <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform text-brand" />
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
            <div className="bg-card rounded-2xl p-8 border border-border-card shadow-card text-center space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-brand/10 border border-brand/20 flex items-center justify-center text-brand mx-auto">
                <Sparkles className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-primary">Repository Not Yet Analyzed</h3>
                <p className="text-xs text-secondary max-w-md mx-auto">
                  Click the "Analyze Repository" button to initiate static analysis, discover HTTP routes, and construct the semantic knowledge graph.
                </p>
              </div>
              <Button
                variant="primary"
                onClick={triggerAnalysis}
                isLoading={analyzing}
                leftIcon={<Play className="w-3.5 h-3.5 fill-current" />}
              >
                Analyze Repository Now
              </Button>
            </div>
          )}

          <div className="bg-card rounded-2xl p-6 border border-border-card shadow-card space-y-2">
            <h3 className="text-base font-bold text-primary">Project Infrastructure & Execution Platform</h3>
            <p className="text-xs text-secondary leading-relaxed">
              Astra executes synthetic HTTP test cases deterministically against target applications with full SSRF protection, secret redaction, and deep knowledge graph trace analysis.
            </p>
          </div>
        </div>
      )}

      {activeTab === 'endpoints' && (
        <div className="space-y-4">
          {endpoints.length === 0 ? (
            <div className="bg-card rounded-2xl p-8 text-center space-y-3 border border-border-card shadow-card">
              <Cpu className="w-10 h-10 text-muted mx-auto" />
              <h3 className="text-base font-bold text-primary">No Endpoints Discovered Yet</h3>
              <p className="text-xs text-secondary">Run analysis on this repository to extract route endpoints.</p>
            </div>
          ) : (
            <div className="bg-card rounded-2xl border border-border-card shadow-card overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-field text-secondary border-b border-border-card uppercase text-[10px] font-semibold tracking-wider">
                  <tr>
                    <th className="px-5 py-3">Method</th>
                    <th className="px-5 py-3">Path</th>
                    <th className="px-5 py-3">Handler Function</th>
                    <th className="px-5 py-3">Source Location</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-card text-secondary">
                  {endpoints.map((ep) => (
                    <tr key={ep.id} className="hover:bg-hover transition-colors">
                      <td className="px-5 py-3 font-mono">
                        <span className={`px-2.5 py-0.5 rounded text-[11px] font-bold ${getMethodBadgeClass(ep.method)}`}>
                          {ep.method}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-primary font-mono font-semibold">{ep.path}</td>
                      <td className="px-5 py-3 text-brand font-mono">{ep.function_name}()</td>
                      <td className="px-5 py-3 text-muted font-mono flex items-center gap-1.5">
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
            <div className="bg-card rounded-2xl p-8 text-center space-y-3 border border-border-card shadow-card">
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
              variant="primary"
              onClick={generateTestSuite}
              disabled={generatingSuite || endpoints.length === 0}
              isLoading={generatingSuite}
              leftIcon={<Zap className="w-4 h-4 fill-current" />}
            >
              Generate Synthetic Suite
            </Button>
          </div>

          {/* Step 1: Target Sandbox Server Lifecycle Controller */}
          {id && project && (
            <SandboxServerControl
              projectId={id}
              projectName={project.name}
              onServerStateChange={handleServerStateChange}
            />
          )}

          {/* Generated Test Suites */}
          <div className="bg-card rounded-2xl p-5 border border-border-card shadow-card space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-primary">Generated Test Suites ({suites.length})</h4>
                <p className="text-xs text-muted">Inspect specifications, endpoints & assertions before executing</p>
              </div>
            </div>
            {suites.length === 0 ? (
              <p className="text-xs text-muted">No test suites generated yet. Click "Generate Synthetic Suite" above.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {suites.map((s) => (
                  <div key={s.id} className="p-4 rounded-xl bg-field border border-border-card flex items-center justify-between text-xs">
                    <div className="space-y-1">
                      <span className="text-primary font-bold block">{s.name}</span>
                      <span className="text-muted text-[11px] block">{s.total_cases} test cases • v{s.version}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setViewingSuite(s)}
                        leftIcon={<Eye className="w-3.5 h-3.5" />}
                      >
                        View Tests ({s.total_cases})
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleInitiateRun(s)}
                        disabled={dispatchingRun}
                        leftIcon={<Play className="w-3 h-3 fill-current" />}
                      >
                        Run Suite
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Past Execution Runs Table */}
          <div className="bg-card rounded-2xl border border-border-card shadow-card overflow-hidden space-y-3 p-5">
            <h4 className="text-sm font-bold text-primary">Execution History ({testRuns.length})</h4>
            {testRuns.length === 0 ? (
              <p className="text-xs text-muted">No test runs executed yet.</p>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-field text-secondary border-b border-border-card uppercase text-[10px] font-semibold tracking-wider">
                  <tr>
                    <th className="px-4 py-3">Run ID</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Tests Passed / Total</th>
                    <th className="px-4 py-3">Duration</th>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-card text-secondary">
                  {testRuns.map((run) => (
                    <tr key={run.id} className="hover:bg-hover transition-colors">
                      <td className="px-4 py-3 font-bold text-primary font-mono">#{run.id.substring(0, 8)}</td>
                      <td className="px-4 py-3">
                        <TestStatusBadge
                          status={mapRunStatusToBadge(run.status)}
                          label={run.status}
                        />
                      </td>
                      <td className="px-4 py-3 text-primary font-bold">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span><span className="text-status-passed">{run.passed_tests}</span> / {run.total_tests}</span>
                            {run.total_tests > 0 && (
                              <span className="text-[10px] text-muted font-mono">
                                ({Math.round(((run.passed_tests + run.failed_tests + run.error_tests) / run.total_tests) * 100)}%)
                              </span>
                            )}
                          </div>
                          {run.total_tests > 0 && (
                            <div className="w-24 h-1.5 bg-field rounded-full overflow-hidden border border-border-field">
                              <div
                                className={`h-full ${
                                  run.status === 'RUNNING' || run.status === 'STARTING' || run.status === 'PENDING'
                                    ? 'bg-brand animate-pulse'
                                    : run.failed_tests > 0
                                    ? 'bg-status-failed'
                                    : 'bg-status-passed'
                                }`}
                                style={{
                                  width: `${Math.min(100, Math.round(((run.passed_tests + run.failed_tests + run.error_tests) / run.total_tests) * 100))}%`
                                }}
                              />
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-secondary font-mono">{Number(run.duration_ms ?? 0).toFixed(0)} ms</td>
                      <td className="px-4 py-3 text-muted">{new Date(run.created_at).toLocaleTimeString()}</td>
                      <td className="px-4 py-3">
                        <Link
                          to={`/projects/${project.id}/test-runs/${run.id}`}
                          className="inline-flex items-center gap-1.5 text-brand hover:text-brand-hover font-semibold transition-colors"
                        >
                          {run.status === 'RUNNING' || run.status === 'STARTING' || run.status === 'PENDING' ? (
                            <>
                              <span className="w-2 h-2 rounded-full bg-brand animate-ping" />
                              View Live <ChevronRight className="w-3.5 h-3.5" />
                            </>
                          ) : (
                            <>
                              View Results <ChevronRight className="w-3.5 h-3.5" />
                            </>
                          )}
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

      {/* Step 2: Test Suite Case Inspector Drawer */}
      <TestSuiteViewerDrawer
        isOpen={!!viewingSuite}
        onClose={() => setViewingSuite(null)}
        suiteId={viewingSuite?.id || null}
        suiteName={viewingSuite?.name || ''}
        totalCasesCount={viewingSuite?.total_cases || 0}
        isServerRunning={serverIsRunning}
        serverPort={serverPort}
        onRunSuite={(suiteId) => {
          const st = suites.find((x) => x.id === suiteId) || viewingSuite;
          setViewingSuite(null);
          if (st) {
            handleInitiateRun(st);
          }
        }}
        onRequestStartServer={() => {
          setViewingSuite(null);
          window.scrollTo({ top: 300, behavior: 'smooth' });
        }}
      />

      {/* Target Server Warning Modal */}
      {serverWarningModalOpen && pendingRunSuite && (
        <Modal
          isOpen={serverWarningModalOpen}
          onClose={() => {
            setServerWarningModalOpen(false);
            setPendingRunSuite(null);
          }}
          title="Target Server Not Running"
        >
          <div className="space-y-4 text-xs">
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-500 space-y-2">
              <div className="flex items-center gap-2 font-bold">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>Target Server Offline</span>
              </div>
              <p className="text-[11px] text-secondary leading-relaxed">
                You are about to execute test suite <strong className="text-primary font-semibold">{pendingRunSuite.name}</strong>, but the target sandbox server is currently <strong>NOT RUNNING</strong>.
                Running tests without an active server will result in connection failures.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-field border border-border-card space-y-2">
              <span className="font-bold text-primary block">Step 1: Start Target Server</span>
              <p className="text-secondary text-[11px]">
                Please start the target server above using the <strong>"Start Target Server"</strong> button. The system will auto-allocate a free port (e.g. 5000) and emulate your scanned endpoints.
              </p>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-border-card">
              <button
                type="button"
                onClick={() => {
                  setServerWarningModalOpen(false);
                  const st = pendingRunSuite;
                  setPendingRunSuite(null);
                  if (st) setSelectedSuiteForRun(st);
                }}
                className="text-[11px] text-muted hover:text-primary underline"
              >
                Continue Anyway with External URL &rarr;
              </button>

              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setServerWarningModalOpen(false);
                    setPendingRunSuite(null);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    setServerWarningModalOpen(false);
                    setPendingRunSuite(null);
                    window.scrollTo({ top: 300, behavior: 'smooth' });
                  }}
                  leftIcon={<Server className="w-3.5 h-3.5" />}
                >
                  Go to Start Server
                </Button>
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* Target Sandbox Configuration Modal */}
      {selectedSuiteForRun && (
        <Modal
          isOpen={!!selectedSuiteForRun}
          onClose={() => setSelectedSuiteForRun(null)}
          title="Dispatch Test Suite Execution"
        >
          <div className="space-y-4 text-xs">
            <div className="p-3.5 rounded-xl bg-field border border-border-card space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-bold text-primary block text-sm">{selectedSuiteForRun.name}</span>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                    serverIsRunning
                      ? 'bg-status-passed-bg text-status-passed border-status-passed/30'
                      : 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      serverIsRunning ? 'bg-status-passed animate-ping' : 'bg-amber-500'
                    }`}
                  />
                  {serverIsRunning ? `Server Running (Port ${serverPort})` : 'Server Not Running'}
                </span>
              </div>
              <p className="text-secondary text-[11px]">
                {selectedSuiteForRun.total_cases} test cases will be executed asynchronously against your target environment.
              </p>
            </div>

            <div className="space-y-2">
              <label className="font-semibold text-primary block">Target Application Base URL</label>
              <Input
                value={targetBaseUrl}
                onChange={(e) => setTargetBaseUrl(e.target.value)}
                placeholder="http://localhost:5000"
              />
              <div className="flex items-center gap-1.5 flex-wrap pt-1">
                <span className="text-[10px] text-muted">Presets:</span>
                {[
                  ...(serverPort ? [{ label: `Active Sandbox (:${serverPort})`, url: `http://localhost:${serverPort}` }] : []),
                  { label: 'Flask (:5000)', url: 'http://localhost:5000' },
                  { label: 'Node (:3000)', url: 'http://localhost:3000' },
                  { label: 'Spring (:8080)', url: 'http://localhost:8080' },
                  { label: 'Astra API (:8000)', url: 'http://localhost:8000' },
                ].map((preset) => (
                  <button
                    key={`${preset.label}-${preset.url}`}
                    type="button"
                    onClick={() => setTargetBaseUrl(preset.url)}
                    className="px-2 py-0.5 rounded text-[10px] bg-card border border-border-card text-secondary hover:text-primary hover:border-brand transition-colors"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-muted leading-relaxed">
                Provide the address where your scanned application server is listening. Astra will send all HTTP test specifications directly to this target.
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="font-semibold text-primary block">Pre-flight Liveness Health Path</label>
              <Input
                value={healthCheckPath}
                onChange={(e) => setHealthCheckPath(e.target.value)}
                placeholder="/health or /"
              />
              <p className="text-[11px] text-muted">
                Initial ping to verify that the application sandbox is reachable before initiating execution.
              </p>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-border-card">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedSuiteForRun(null)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => dispatchRun(selectedSuiteForRun.id)}
                disabled={dispatchingRun || !targetBaseUrl.trim()}
                isLoading={dispatchingRun}
                leftIcon={<Play className="w-3 h-3 fill-current" />}
              >
                Start Execution
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
