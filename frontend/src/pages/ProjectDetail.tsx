import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  Info,
  Code2,
  Sparkles,
  Network,
  Activity,
  CheckCircle2,
  FileCode,
  Cpu,
  ChevronRight,
  Play,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { TestGenerationDrawer } from '../components/TestGenerationDrawer';
import { TestSuiteViewerDrawer } from '../components/TestSuiteViewerDrawer';
import { KnowledgeGraphVisualizer } from '../components/KnowledgeGraphVisualizer';
import { TestStatusBadge } from '../components/common/TestStatusBadge';
import { Button } from '../components/common/Button';

import {
  Project,
  Analysis,
  DiscoveredEndpoint,
  TestSuite,
  TestRun,
  KnowledgeGraph,
  DiscoveredFunction,
  UnitTestRunResult,
  ProjectMember,
  formatFrameworkName,
} from '../components/project/types';

import { ProjectHeaderBanner } from '../components/project/ProjectHeaderBanner';
import { AnalysisStageCard } from '../components/project/AnalysisStageCard';
import { DiscoveredEndpointsTable } from '../components/project/DiscoveredEndpointsTable';
import { DiscoveredFunctionsTable } from '../components/project/DiscoveredFunctionsTable';
import { TestSuitesRunsPanel } from '../components/project/TestSuitesRunsPanel';

export const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [project, setProject] = useState<Project | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [endpoints, setEndpoints] = useState<DiscoveredEndpoint[]>([]);
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [testRuns, setTestRuns] = useState<TestRun[]>([]);
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [functions, setFunctions] = useState<DiscoveredFunction[]>([]);
  const [members, setMembers] = useState<ProjectMember[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [generatingSuite, setGeneratingSuite] = useState(false);
  const [runningUnitTests, setRunningUnitTests] = useState(false);
  const [unitTestResult, setUnitTestResult] = useState<UnitTestRunResult | null>(null);

  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [viewingSuite, setViewingSuite] = useState<TestSuite | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'endpoints' | 'functions' | 'graph' | 'testruns'>('overview');

  // Execution dispatch states
  const [selectedSuiteForRun, setSelectedSuiteForRun] = useState<TestSuite | null>(null);
  const [targetBaseUrl, setTargetBaseUrl] = useState('http://localhost:5000');
  const [healthCheckPath, setHealthCheckPath] = useState('/health');
  const [dispatchingRun, setDispatchingRun] = useState(false);

  // Target sandbox server port tracker
  const [serverIsRunning, setServerIsRunning] = useState(false);
  const [serverPort, setServerPort] = useState<number | null>(null);
  const [serverWarningModalOpen, setServerWarningModalOpen] = useState(false);
  const [pendingRunSuite, setPendingRunSuite] = useState<TestSuite | null>(null);

  const isOwner = user && project && (user.id === project.owner_id || user.role === 'ADMIN');
  const isAdmin = user?.role === 'ADMIN';
  const isTester = user?.role === 'TESTER';
  const canRunTests = isOwner || isAdmin || isTester;

  const fetchProjectDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get(`/projects/${id}`);
      setProject(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch project details.');
    } finally {
      setLoading(false);
    }
  };

  const fetchMembers = async () => {
    try {
      const res = await api.get(`/projects/${id}/members`);
      setMembers(res.data || []);
    } catch {
      // Non-blocking
    }
  };

  const fetchAnalysis = async () => {
    try {
      const res = await api.get(`/projects/${id}/analysis`);
      setAnalysis(res.data);
      if (res.data?.status === 'RUNNING' || res.data?.status === 'QUEUED') {
        setAnalyzing(true);
      } else {
        setAnalyzing(false);
      }
    } catch {
      setAnalysis(null);
      setAnalyzing(false);
    }
  };

  const fetchEndpoints = async () => {
    try {
      const res = await api.get(`/projects/${id}/endpoints`);
      setEndpoints(res.data || []);
    } catch {
      setEndpoints([]);
    }
  };

  const fetchTestSuites = async () => {
    try {
      const res = await api.get(`/projects/${id}/test-suites`);
      setSuites(res.data || []);
    } catch {
      setSuites([]);
    }
  };

  const fetchTestRuns = async () => {
    try {
      const res = await api.get(`/projects/${id}/test-runs`);
      setTestRuns(res.data || []);
    } catch {
      setTestRuns([]);
    }
  };

  const fetchKnowledgeGraph = async () => {
    try {
      const res = await api.get(`/projects/${id}/graph`);
      setGraph(res.data);
    } catch {
      setGraph(null);
    }
  };

  const fetchFunctions = async () => {
    try {
      const res = await api.get(`/projects/${id}/functions`);
      setFunctions(res.data?.functions || []);
    } catch {
      setFunctions([]);
    }
  };

  useEffect(() => {
    if (id) {
      fetchProjectDetails();
      fetchAnalysis();
      fetchEndpoints();
      fetchTestSuites();
      fetchTestRuns();
      fetchKnowledgeGraph();
      fetchFunctions();
      fetchMembers();
    }
  }, [id]);

  // Polling mechanism during analysis pipeline run
  useEffect(() => {
    let interval: any = null;
    if (analyzing || analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED') {
      interval = setInterval(() => {
        fetchAnalysis();
        fetchEndpoints();
        fetchKnowledgeGraph();
        fetchFunctions();
      }, 2500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [analyzing, analysis?.status]);

  const triggerAnalysis = async () => {
    setAnalyzing(true);
    try {
      await api.post(`/projects/${id}/analyze`);
      fetchAnalysis();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to trigger static analysis.');
      setAnalyzing(false);
    }
  };

  const runUnitTests = async () => {
    setRunningUnitTests(true);
    try {
      const res = await api.post(`/projects/${id}/code/run-tests`, {
        generate_if_missing: true,
      });
      setUnitTestResult(res.data);
      setActiveTab('testruns');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to execute unit test suite.');
    } finally {
      setRunningUnitTests(false);
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

  return (
    <div className="space-y-6">
      {/* 1. Project Banner, Actions & Team Governance */}
      <ProjectHeaderBanner
        project={project}
        analysis={analysis}
        endpoints={endpoints}
        members={members}
        canRunTests={canRunTests}
        analyzing={analyzing}
        isAdmin={isAdmin}
        onTriggerAnalysis={triggerAnalysis}
        onOpenAdvancedDrawer={() => setIsDrawerOpen(true)}
      />

      {/* 2. Repository Static Analysis Pipeline */}
      <AnalysisStageCard
        analysis={analysis}
        analyzing={analyzing}
        functionsCount={functions.length}
        graphNodesCount={analysis?.graph_node_count || 0}
        onTriggerAnalysis={triggerAnalysis}
        onSelectFunctionsTab={() => setActiveTab('functions')}
      />

      {/* 3. Segmented Navigation Tabs */}
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
          onClick={() => setActiveTab('functions')}
          className={`px-4 py-2 rounded-xl transition-all flex items-center gap-1.5 ${
            activeTab === 'functions'
              ? 'bg-card text-brand font-bold shadow-sm border border-border-card'
              : 'text-secondary hover:text-primary hover:bg-hover'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-brand" /> Functions Discovered ({functions.length})
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

      {/* 4. Tab Content */}
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

      {activeTab === 'endpoints' && <DiscoveredEndpointsTable endpoints={endpoints} />}

      {activeTab === 'functions' && (
        <DiscoveredFunctionsTable
          functions={functions}
          canRunTests={canRunTests}
          runningUnitTests={runningUnitTests}
          onRunUnitTests={runUnitTests}
        />
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
            <KnowledgeGraphVisualizer graph={graph} projectName={project?.name} />
          )}
        </div>
      )}

      {activeTab === 'testruns' && (
        <TestSuitesRunsPanel
          projectId={id!}
          project={project}
          suites={suites}
          testRuns={testRuns}
          functionsCount={functions.length}
          endpointsCount={endpoints.length}
          unitTestResult={unitTestResult}
          runningUnitTests={runningUnitTests}
          generatingSuite={generatingSuite}
          dispatchingRun={dispatchingRun}
          serverIsRunning={serverIsRunning}
          serverPort={serverPort}
          onRunUnitTests={runUnitTests}
          onGenerateSuite={generateTestSuite}
          onServerStateChange={handleServerStateChange}
          onViewSuite={(s) => setViewingSuite(s)}
          onInitiateRun={handleInitiateRun}
          onDispatchRun={dispatchRun}
          targetBaseUrl={targetBaseUrl}
          setTargetBaseUrl={setTargetBaseUrl}
          healthCheckPath={healthCheckPath}
          setHealthCheckPath={setHealthCheckPath}
          selectedSuiteForRun={selectedSuiteForRun}
          setSelectedSuiteForRun={setSelectedSuiteForRun}
          serverWarningModalOpen={serverWarningModalOpen}
          setServerWarningModalOpen={setServerWarningModalOpen}
          pendingRunSuite={pendingRunSuite}
          setPendingRunSuite={setPendingRunSuite}
        />
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

      {/* Test Suite Case Inspector Drawer */}
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
    </div>
  );
};
