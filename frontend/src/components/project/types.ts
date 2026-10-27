import { TestStatus } from '../common/TestStatusBadge';

export const mapRunStatusToBadge = (status?: string): TestStatus => {
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

export interface Project {
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

export interface Analysis {
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

export interface DiscoveredEndpoint {
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

export interface TestSuite {
  id: string;
  name: string;
  total_cases: number;
  version: string;
  created_at: string;
}

export interface TestRun {
  id: string;
  status: string;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  error_tests: number;
  duration_ms: number;
  created_at: string;
  target_environment?: {
    base_url?: string;
    environment_type?: string;
    current_test?: any;
  };
}

export interface KnowledgeGraph {
  nodes: Array<{ id: string; label: string; type: string; properties: any }>;
  edges: Array<{ source: string; target: string; type: string; properties: any }>;
}

export interface DiscoveredFunction {
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

export interface UnitTestOutcome {
  nodeid: string;
  outcome: string;
  duration: number;
  message?: string;
}

export interface UnitTestRunResult {
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

export interface ProjectMember {
  id: string;
  project_id: string;
  user_id: string;
  role: string;
  created_at: string;
  user: {
    id: string;
    email: string;
    full_name: string;
    role: string;
  };
}

export const PIPELINE_STAGES = [
  { key: 'CLONING', label: '1. Git Clone', desc: 'Fetch source tree & branch' },
  { key: 'SCANNING', label: '2. File Scan', desc: 'Scan files & detect language' },
  { key: 'AST_PARSING', label: '3. AST Parsing', desc: 'Parse AST & extract endpoints' },
  { key: 'GRAPH_BUILDING', label: '4. Knowledge Graph', desc: 'Build code dependency graph' },
  { key: 'PERSISTING', label: '5. Database Index', desc: 'Persist endpoints & graph nodes' },
];

export const getStageInfo = (stage?: string, status?: string) => {
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

export const getStageStatus = (stageKey: string, currentStage?: string, overallStatus?: string) => {
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

export const formatFrameworkName = (raw?: string | null): string => {
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
    CPP_GENERIC: 'C++ Native',
    JS_EXPRESS: 'Express.js',
    JS_FASTIFY: 'Fastify',
    JS_NESTJS: 'NestJS',
    JS_KOA: 'Koa.js',
    JS_NEXTJS: 'Next.js API',
    JS_GENERIC: 'JavaScript / Node',
    TS_GENERIC: 'TypeScript / Node',
    GO_GIN: 'Gin (Go)',
    GO_ECHO: 'Echo (Go)',
    GO_FIBER: 'Fiber (Go)',
    GO_CHI: 'Chi (Go)',
    GO_GENERIC: 'Go Native',
  };
  return MAP[raw] || raw;
};
