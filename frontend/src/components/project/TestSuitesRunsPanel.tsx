import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  Zap,
  Eye,
  Play,
  ChevronRight,
  AlertTriangle,
  Server,
} from 'lucide-react';
import { Button } from '../common/Button';
import { Modal } from '../common/Modal';
import { Input } from '../common/Input';
import { TestStatusBadge } from '../common/TestStatusBadge';
import { SandboxServerControl } from '../SandboxServerControl';
import { SpatialTestExecutionVisualizer } from '../SpatialTestExecutionVisualizer';
import {
  Project,
  TestSuite,
  TestRun,
  UnitTestRunResult,
  mapRunStatusToBadge,
} from './types';

interface TestSuitesRunsPanelProps {
  projectId: string;
  project: Project;
  suites: TestSuite[];
  testRuns: TestRun[];
  functionsCount: number;
  endpointsCount: number;
  unitTestResult: UnitTestRunResult | null;
  runningUnitTests: boolean;
  generatingSuite: boolean;
  dispatchingRun: boolean;
  serverIsRunning: boolean;
  serverPort: number | null;
  onRunUnitTests: () => void;
  onGenerateSuite: () => void;
  onServerStateChange: (isRunning: boolean, port: number | null) => void;
  onViewSuite: (suite: TestSuite) => void;
  onInitiateRun: (suite: TestSuite) => void;
  onDispatchRun: (suiteId: string, customUrl?: string, customHealthPath?: string) => Promise<void>;
  targetBaseUrl: string;
  setTargetBaseUrl: (url: string) => void;
  healthCheckPath: string;
  setHealthCheckPath: (path: string) => void;
  selectedSuiteForRun: TestSuite | null;
  setSelectedSuiteForRun: (suite: TestSuite | null) => void;
  serverWarningModalOpen: boolean;
  setServerWarningModalOpen: (open: boolean) => void;
  pendingRunSuite: TestSuite | null;
  setPendingRunSuite: (suite: TestSuite | null) => void;
}

export const TestSuitesRunsPanel: React.FC<TestSuitesRunsPanelProps> = ({
  projectId,
  project,
  suites,
  testRuns,
  functionsCount,
  endpointsCount,
  unitTestResult,
  runningUnitTests,
  generatingSuite,
  dispatchingRun,
  serverIsRunning,
  serverPort,
  onRunUnitTests,
  onGenerateSuite,
  onServerStateChange,
  onViewSuite,
  onInitiateRun,
  onDispatchRun,
  targetBaseUrl,
  setTargetBaseUrl,
  healthCheckPath,
  setHealthCheckPath,
  selectedSuiteForRun,
  setSelectedSuiteForRun,
  serverWarningModalOpen,
  setServerWarningModalOpen,
  pendingRunSuite,
  setPendingRunSuite,
}) => {
  const [showStdout, setShowStdout] = useState(false);
  const safeSuites: TestSuite[] = Array.isArray(suites) ? suites : (suites as any)?.items || [];
  const safeTestRuns: TestRun[] = Array.isArray(testRuns) ? testRuns : (testRuns as any)?.items || [];

  return (
    <div className="space-y-6">
      {/* Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-primary">Test Suites & Execution Telemetry</h3>
          <p className="text-xs text-secondary">Synthesize unit test suites or execute async HTTP API test runs.</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="primary"
            onClick={onRunUnitTests}
            disabled={runningUnitTests || functionsCount === 0}
            isLoading={runningUnitTests}
            leftIcon={<Sparkles className="w-4 h-4 fill-current" />}
          >
            Generate & Run Unit Suite ({functionsCount} funcs)
          </Button>

          <Button
            variant="outline"
            onClick={onGenerateSuite}
            disabled={generatingSuite || endpointsCount === 0}
            isLoading={generatingSuite}
            leftIcon={<Zap className="w-4 h-4 fill-current" />}
          >
            Generate Synthetic API Suite
          </Button>
        </div>
      </div>

      {/* Unit Test Execution Telemetry Card */}
      {unitTestResult && (
        <div className="glass-restrained rounded-2xl p-5 border border-border-card shadow-tactile space-y-4 relative overflow-hidden before:absolute before:inset-x-6 before:top-0 before:h-px before:bg-white/20">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border-card">
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-bold text-primary flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-brand" />
                  Multi-Layer Unit Suite Execution
                </h4>
                <span
                  className={`px-2 py-0.5 rounded text-[11px] font-bold shadow-tactile-sm ${
                    unitTestResult.exit_code === 0
                      ? 'bg-status-passed-bg text-status-passed border border-status-passed/30'
                      : 'bg-status-failed-bg text-status-failed border border-status-failed/30'
                  }`}
                >
                  {unitTestResult.exit_code === 0 ? 'PASSED (Exit 0)' : `FAILED (Exit ${unitTestResult.exit_code})`}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-field text-secondary border border-border-card shadow-tactile-sm">
                  100% Offline • $0 Cost • AI Mocks Active
                </span>
              </div>
              <p className="text-xs text-muted mt-0.5">
                Spec-grounded invariant and boundary tests executed in isolated runner sandbox.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => setShowStdout(!showStdout)}>
                {showStdout ? 'Hide Logs' : 'View Pytest Stdout'}
              </Button>
            </div>
          </div>

          {/* Stat Counters */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="p-3 rounded-xl bg-field border border-border-card text-center">
              <span className="text-[10px] font-semibold uppercase text-muted block">Total Tests</span>
              <span className="text-lg font-bold text-primary font-mono block mt-0.5">
                {unitTestResult.total_tests}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-status-passed-bg/30 border border-status-passed/20 text-center">
              <span className="text-[10px] font-semibold uppercase text-status-passed block">Passed</span>
              <span className="text-lg font-bold text-status-passed font-mono block mt-0.5">
                {unitTestResult.passed_tests}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-status-failed-bg/30 border border-status-failed/20 text-center">
              <span className="text-[10px] font-semibold uppercase text-status-failed block">Failed</span>
              <span className="text-lg font-bold text-status-failed font-mono block mt-0.5">
                {unitTestResult.failed_tests}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-field border border-border-card text-center">
              <span className="text-[10px] font-semibold uppercase text-muted block">Execution Time</span>
              <span className="text-lg font-bold text-brand font-mono block mt-0.5">
                {unitTestResult.duration_ms} ms
              </span>
            </div>
            <div className="p-3 rounded-xl bg-field border border-border-card text-center">
              <span className="text-[10px] font-semibold uppercase text-muted block">Pass Rate</span>
              <span className="text-lg font-bold text-primary font-mono block mt-0.5">
                {unitTestResult.total_tests > 0
                  ? Math.round((unitTestResult.passed_tests / unitTestResult.total_tests) * 100)
                  : 0}
                %
              </span>
            </div>
          </div>

          {/* Individual Test Cases List */}
          {unitTestResult.test_outcomes && unitTestResult.test_outcomes.length > 0 && (
            <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
              {unitTestResult.test_outcomes.map((t, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-lg bg-field border border-border-card flex items-center justify-between text-xs font-mono"
                >
                  <div className="flex items-center gap-2 truncate pr-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        t.outcome === 'passed' ? 'bg-status-passed' : 'bg-status-failed'
                      }`}
                    />
                    <span className="text-primary truncate">{t.nodeid.split('::').pop()}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-muted text-[11px]">{(t.duration * 1000).toFixed(1)} ms</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        t.outcome === 'passed' ? 'text-status-passed bg-status-passed-bg' : 'text-status-failed bg-status-failed-bg'
                      }`}
                    >
                      {t.outcome}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Stdout Console */}
          {showStdout && (
            <div className="mt-3 p-3 rounded-xl bg-black/80 border border-border-card text-[11px] font-mono text-zinc-300 max-h-60 overflow-y-auto whitespace-pre-wrap">
              {unitTestResult.raw_stdout}
            </div>
          )}
        </div>
      )}

      {/* Target Sandbox Server Lifecycle Controller */}
      {projectId && project && (
        <SandboxServerControl
          projectId={projectId}
          projectName={project.name}
          onServerStateChange={onServerStateChange}
        />
      )}

      {/* Generated Test Suites */}
      <div className="glass-restrained rounded-2xl p-5 border border-border-card shadow-tactile space-y-3 relative before:absolute before:inset-x-6 before:top-0 before:h-px before:bg-white/15">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-bold text-primary tracking-tight">Generated Test Suites ({safeSuites.length})</h4>
            <p className="text-xs text-muted">Inspect specifications, endpoints & assertions before executing</p>
          </div>
        </div>
        {safeSuites.length === 0 ? (
          <p className="text-xs text-muted">No test suites generated yet. Click "Generate Synthetic Suite" above.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {safeSuites.map((s) => (
              <div
                key={s.id}
                className="p-4 rounded-xl tactile-well border border-border-card/60 flex items-center justify-between text-xs"
              >
                <div className="space-y-1">
                  <span className="text-primary font-bold block">{s.name}</span>
                  <span className="text-muted text-[11px] block">
                    {s.total_cases} test cases • v{s.version}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" onClick={() => onViewSuite(s)} leftIcon={<Eye className="w-3.5 h-3.5" />}>
                    View Tests ({s.total_cases})
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => onInitiateRun(s)}
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

      {/* Spatial Test Execution Visualizer */}
      <SpatialTestExecutionVisualizer
        testRun={
          safeTestRuns.length > 0
            ? {
                id: safeTestRuns[0].id,
                status: safeTestRuns[0].status,
                total_tests: safeTestRuns[0].total_tests,
                passed_tests: safeTestRuns[0].passed_tests,
                failed_tests: safeTestRuns[0].failed_tests,
                error_tests: safeTestRuns[0].error_tests,
                duration_ms: safeTestRuns[0].duration_ms,
                target_environment: safeTestRuns[0].target_environment,
              }
            : {
                id: 'pipeline-preview',
                status: 'COMPLETED',
                total_tests: 12,
                passed_tests: 10,
                failed_tests: 1,
                error_tests: 0,
                duration_ms: 245,
                target_environment: {
                  base_url: targetBaseUrl || 'http://localhost:5000',
                },
              }
        }
        results={
          safeTestRuns.length > 0
            ? []
            : [
                { id: 't-1', endpoint: '/api/v1/auth/login', method: 'POST', test_type: 'contract', outcome: 'PASS', status_code: 200, execution_time_ms: 42 },
                { id: 't-2', endpoint: '/api/v1/auth/me', method: 'GET', test_type: 'security', outcome: 'PASS', status_code: 200, execution_time_ms: 18 },
                { id: 't-3', endpoint: '/api/v1/projects', method: 'GET', test_type: 'invariant', outcome: 'PASS', status_code: 200, execution_time_ms: 36 },
                { id: 't-4', endpoint: '/api/v1/projects', method: 'POST', test_type: 'schema', outcome: 'PASS', status_code: 201, execution_time_ms: 55 },
                { id: 't-5', endpoint: '/api/v1/projects/{id}', method: 'DELETE', test_type: 'destructive', outcome: 'FAIL', status_code: 403, execution_time_ms: 22, assertion_failures: [{ type: 'authorization', message: 'Expected status 204 but received 403 Forbidden' }] },
                { id: 't-6', endpoint: '/api/v1/health', method: 'GET', test_type: 'liveness', outcome: 'PASS', status_code: 200, execution_time_ms: 8 },
              ]
        }
      />

      {/* Past Execution Runs Table */}
      <div className="glass-restrained rounded-2xl border border-border-card shadow-tactile overflow-hidden space-y-3 p-5 relative before:absolute before:inset-x-6 before:top-0 before:h-px before:bg-white/20">
        <h4 className="text-sm font-bold text-primary tracking-tight">Execution History ({safeTestRuns.length})</h4>
        {safeTestRuns.length === 0 ? (
          <p className="text-xs text-muted">No test runs executed yet.</p>
        ) : (
          <table className="w-full text-left text-xs">
            <thead className="bg-field/90 text-secondary border-b border-border-card uppercase text-[10px] font-semibold tracking-wider">
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
              {safeTestRuns.map((run) => (
                <tr key={run.id} className="hover:bg-hover transition-colors">
                  <td className="px-4 py-3 font-bold text-primary font-mono">#{run.id.substring(0, 8)}</td>
                  <td className="px-4 py-3">
                    <TestStatusBadge status={mapRunStatusToBadge(run.status)} label={run.status} />
                  </td>
                  <td className="px-4 py-3 text-primary font-bold">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span>
                          <span className="text-status-passed">{run.passed_tests}</span> / {run.total_tests}
                        </span>
                        {run.total_tests > 0 && (
                          <span className="text-[10px] text-muted font-mono">
                            (
                            {Math.round(
                              ((run.passed_tests + run.failed_tests + run.error_tests) / run.total_tests) * 100
                            )}
                            %)
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
                              width: `${Math.min(
                                100,
                                Math.round(
                                  ((run.passed_tests + run.failed_tests + run.error_tests) / run.total_tests) * 100
                                )
                              )}%`,
                            }}
                          />
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-secondary font-mono">
                    {Number(run.duration_ms ?? 0).toFixed(0)} ms
                  </td>
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
                You are about to execute test suite{' '}
                <strong className="text-primary font-semibold">{pendingRunSuite.name}</strong>, but the target
                sandbox server is currently <strong>NOT RUNNING</strong>. Running tests without an active server will
                result in connection failures.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-field border border-border-card space-y-2">
              <span className="font-bold text-primary block">Step 1: Start Target Server</span>
              <p className="text-secondary text-[11px]">
                Please start the target server using the <strong>"Start Target Server"</strong> button above. The
                system will auto-allocate a free port (e.g. 5000) and emulate your scanned endpoints.
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
                {selectedSuiteForRun.total_cases} test cases will be executed asynchronously against your target
                environment.
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
                  ...(serverPort
                    ? [{ label: `Active Sandbox (:${serverPort})`, url: `http://localhost:${serverPort}` }]
                    : []),
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
                Provide the address where your scanned application server is listening. Astra will send all HTTP test
                specifications directly to this target.
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
              <Button variant="ghost" size="sm" onClick={() => setSelectedSuiteForRun(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => onDispatchRun(selectedSuiteForRun.id)}
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
