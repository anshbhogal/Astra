import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  StopCircle,
  Info,
  Layers,
  ChevronRight,
  ChevronDown,
  Loader2,
  Activity,
} from 'lucide-react';
import { api } from '../services/api';
import { Button } from '../components/common/Button';
import { TestStatusBadge, type TestStatus } from '../components/common/TestStatusBadge';

interface CurrentTestMeta {
  index: number;
  total: number;
  name: string;
  method: string;
  path: string;
}

interface TestRun {
  id: string;
  project_id: string;
  suite_id: string;
  status: 'PENDING' | 'STARTING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'TIMED_OUT' | 'CANCELLED' | 'ENVIRONMENT_ERROR' | 'ERROR';
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  error_tests: number;
  duration_ms: number;
  target_environment: {
    base_url?: string;
    environment_type?: string;
    current_test?: CurrentTestMeta;
  };
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

interface TestResult {
  id: string;
  test_run_id: string;
  test_case_id: string;
  endpoint: string;
  method: string;
  test_type: string;
  outcome: 'PASS' | 'FAIL' | 'ERROR' | 'TIMEOUT' | 'SKIP';
  status_code: number | null;
  request_data: any;
  response_data: any;
  response_body_truncated: boolean;
  execution_time_ms: number;
  assertion_failures: Array<{ type: string; message: string; expected?: any; actual?: any }>;
  error_message: string | null;
  created_at: string;
}

const mapOutcomeToStatus = (outcome: string): TestStatus => {
  switch (outcome.toUpperCase()) {
    case 'PASS':
      return 'passed';
    case 'FAIL':
      return 'failed';
    case 'ERROR':
      return 'error';
    case 'TIMEOUT':
      return 'flaky';
    case 'SKIP':
    default:
      return 'skipped';
  }
};

const mapRunStatusToBadge = (status: string): TestStatus => {
  switch (status.toUpperCase()) {
    case 'COMPLETED':
      return 'passed';
    case 'FAILED':
      return 'failed';
    case 'RUNNING':
    case 'STARTING':
      return 'running';
    case 'TIMED_OUT':
    case 'ENVIRONMENT_ERROR':
      return 'error';
    case 'CANCELLED':
    case 'PENDING':
    default:
      return 'skipped';
  }
};

export const TestRunDetail: React.FC = () => {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>();
  const [testRun, setTestRun] = useState<TestRun | null>(null);
  const [results, setResults] = useState<TestResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [filter, setFilter] = useState<'ALL' | 'PASS' | 'FAIL' | 'ERROR'>('ALL');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    fetchTestRun();
    fetchResults();
  }, [runId]);

  useEffect(() => {
    let timer: any = null;
    if (testRun && (testRun.status === 'PENDING' || testRun.status === 'STARTING' || testRun.status === 'RUNNING')) {
      timer = setInterval(() => {
        fetchTestRun();
        fetchResults();
      }, 750);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [testRun?.status, runId]);

  const fetchTestRun = async () => {
    try {
      const res = await api.get(`/test-runs/${runId}`);
      setTestRun(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Test run telemetry not found.');
    } finally {
      setLoading(false);
    }
  };

  const fetchResults = async () => {
    try {
      const res = await api.get(`/test-runs/${runId}/results?page_size=200`);
      setResults(res.data.items || []);
    } catch (err) {}
  };

  const handleCancelRun = async () => {
    setCancelling(true);
    try {
      const res = await api.post(`/test-runs/${runId}/cancel`);
      setTestRun(res.data);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to cancel test run.');
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-20 text-muted text-sm flex flex-col items-center gap-3">
        <div className="w-6 h-6 border-2 border-brand border-t-transparent rounded-full animate-spin" />
        <span>Loading execution telemetry...</span>
      </div>
    );
  }

  if (error || !testRun) {
    return (
      <div className="bg-card rounded-2xl p-8 text-center space-y-4 border border-border-card shadow-card max-w-md mx-auto">
        <Info className="w-10 h-10 text-status-failed mx-auto" />
        <h3 className="text-lg font-bold text-primary">Test Run Not Found</h3>
        <p className="text-xs text-secondary">{error}</p>
        <Link to={`/projects/${projectId}`} className="inline-block text-xs font-semibold text-brand hover:underline">
          &larr; Return to Project Cockpit
        </Link>
      </div>
    );
  }

  const filteredResults = results.filter((r) => {
    if (filter === 'ALL') return true;
    return r.outcome === filter;
  });

  const failedCount = testRun.failed_tests || 0;
  const passedCount = testRun.passed_tests || 0;
  const errorCount = testRun.error_tests || 0;
  const isRunning = testRun.status === 'RUNNING' || testRun.status === 'STARTING' || testRun.status === 'PENDING';

  const currentTest = testRun.target_environment?.current_test;
  const totalTests = testRun.total_tests || currentTest?.total || (results.length > 0 ? results.length : 1);
  const completedCount = passedCount + failedCount + errorCount;
  const progressPercent = totalTests > 0 ? Math.min(100, Math.round((completedCount / totalTests) * 100)) : 0;

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb Navigation */}
      <div className="flex items-center gap-2 text-xs text-muted">
        <Link to="/projects" className="hover:text-primary transition-colors font-medium flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> Projects
        </Link>
        <span>/</span>
        <Link to={`/projects/${projectId}`} className="hover:text-primary transition-colors font-medium">
          Project Cockpit
        </Link>
        <span>/</span>
        <span className="text-primary font-semibold font-mono">Run #{testRun.id.substring(0, 8)}</span>
      </div>

      {/* Plain Language Status Banner (Status First principle) */}
      <div className="bg-card rounded-2xl p-5 border border-border-card shadow-card flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          {isRunning ? (
            <div className="w-10 h-10 rounded-xl bg-brand/10 border border-brand/30 text-brand flex items-center justify-center shrink-0">
              <Loader2 className="w-6 h-6 animate-spin text-brand" />
            </div>
          ) : testRun.status === 'ENVIRONMENT_ERROR' || testRun.status === 'ERROR' ? (
            <div className="w-10 h-10 rounded-xl bg-status-error-bg border border-status-error/30 text-status-error flex items-center justify-center shrink-0">
              <AlertTriangle className="w-6 h-6" />
            </div>
          ) : testRun.status === 'CANCELLED' ? (
            <div className="w-10 h-10 rounded-xl bg-field border border-border-card text-muted flex items-center justify-center shrink-0">
              <StopCircle className="w-6 h-6" />
            </div>
          ) : failedCount === 0 ? (
            <div className="w-10 h-10 rounded-xl bg-status-passed-bg border border-status-passed/30 text-status-passed flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-6 h-6" />
            </div>
          ) : (
            <div className="w-10 h-10 rounded-xl bg-status-failed-bg border border-status-failed/30 text-status-failed flex items-center justify-center shrink-0">
              <XCircle className="w-6 h-6" />
            </div>
          )}
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-primary">
                {isRunning
                  ? currentTest
                    ? `Running Test Suite: Step ${currentTest.index} of ${currentTest.total}`
                    : `Starting Test Suite Execution (${completedCount} of ${totalTests} completed)`
                  : testRun.status === 'ENVIRONMENT_ERROR'
                  ? 'Pre-flight Health Check Failed'
                  : testRun.status === 'ERROR'
                  ? 'Runtime Test Execution Error'
                  : testRun.status === 'CANCELLED'
                  ? 'Test Execution Aborted by User'
                  : failedCount === 0
                  ? `All ${passedCount} tests passed smoothly after your last execution`
                  : `${failedCount} ${failedCount === 1 ? 'test' : 'tests'} failed after your last change`}
              </h2>
              {isRunning && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-brand text-on-brand animate-pulse tracking-wider">
                  LIVE
                </span>
              )}
            </div>
            <div className="text-xs text-secondary mt-1 flex flex-wrap items-center gap-2">
              {isRunning && currentTest ? (
                <>
                  <span className="text-muted font-medium">Currently testing:</span>
                  <span className="px-1.5 py-0.5 rounded font-mono text-[10px] font-bold bg-brand/10 text-brand border border-brand/20">
                    {currentTest.method}
                  </span>
                  <span className="font-mono text-primary font-semibold">{currentTest.path}</span>
                  <span className="text-muted font-sans font-normal">({currentTest.name})</span>
                </>
              ) : testRun.error_message ? (
                <span className="text-status-error font-mono font-medium">
                  {testRun.error_message}
                </span>
              ) : (
                <span>
                  Target sandbox:{' '}
                  <span className="font-mono text-primary font-semibold">
                    {testRun.target_environment.base_url || 'http://localhost:8000'}
                  </span>
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <TestStatusBadge
            status={mapRunStatusToBadge(testRun.status)}
            label={testRun.status}
          />
          {isRunning && (
            <Button
              variant="danger"
              size="sm"
              onClick={handleCancelRun}
              disabled={cancelling}
              leftIcon={<StopCircle className="w-3.5 h-3.5" />}
            >
              Abort Run
            </Button>
          )}
        </div>
      </div>

      {/* Real-time Execution Telemetry & Progress Card */}
      <div className="bg-card rounded-2xl p-5 border border-border-card shadow-card space-y-3">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-brand" />
            <span className="font-bold text-primary">Execution Telemetry</span>
            {isRunning && (
              <span className="text-[11px] text-muted flex items-center gap-1.5 font-medium ml-1">
                <span className="w-2 h-2 rounded-full bg-status-passed animate-ping" />
                Live sandbox runner
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted font-mono">{completedCount} / {totalTests} steps</span>
            <span className="font-mono font-bold text-brand text-sm px-2.5 py-0.5 bg-brand/10 rounded-lg">
              {progressPercent}%
            </span>
          </div>
        </div>

        {/* Visual Progress Bar Track */}
        <div className="w-full h-3 bg-field rounded-full overflow-hidden border border-border-field relative">
          <div
            className={`h-full transition-all duration-300 ease-out rounded-full ${
              isRunning
                ? 'bg-gradient-to-r from-brand via-brand-hover to-secondaryAccent animate-pulse'
                : failedCount > 0
                ? 'bg-gradient-to-r from-status-passed via-status-passed to-status-failed'
                : 'bg-status-passed'
            }`}
            style={{ width: `${Math.max(isRunning ? 5 : 0, progressPercent)}%` }}
          />
        </div>

        {/* Micro statistics */}
        <div className="flex items-center justify-between text-[11px] text-muted pt-1">
          <span>
            {isRunning && currentTest
              ? `Step ${currentTest.index} of ${totalTests} in progress`
              : `${completedCount} of ${totalTests} tests completed`}
          </span>
          <div className="flex items-center gap-3">
            <span className="text-status-passed font-semibold">{passedCount} Passed</span>
            <span className="text-status-failed font-semibold">{failedCount} Failed</span>
            {errorCount > 0 && <span className="text-status-error font-semibold">{errorCount} Errors</span>}
          </div>
        </div>
      </div>

      {/* KPI Stat Cards with 32px Icon Chips */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <div className="bg-card rounded-xl p-4 border border-border-card shadow-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-muted text-[10px] uppercase font-semibold tracking-wider">Total Tests</span>
            <div className="w-8 h-8 rounded-lg bg-brand/10 border border-brand/20 flex items-center justify-center text-brand">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div>
            <span className="text-2xl font-bold text-primary block">
              {results.length} <span className="text-xs font-normal text-muted">/ {testRun.total_tests}</span>
            </span>
            <span className="text-[11px] text-muted">Executed steps</span>
          </div>
        </div>

        <div className="bg-card rounded-xl p-4 border border-border-card shadow-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-muted text-[10px] uppercase font-semibold tracking-wider">Passed</span>
            <div className="w-8 h-8 rounded-lg bg-status-passed-bg border border-status-passed/30 flex items-center justify-center text-status-passed">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div>
            <span className="text-2xl font-bold text-status-passed block">
              {testRun.passed_tests}
            </span>
            <span className="text-[11px] text-muted">Assertions verified</span>
          </div>
        </div>

        <div className="bg-card rounded-xl p-4 border border-border-card shadow-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-muted text-[10px] uppercase font-semibold tracking-wider">Failed</span>
            <div className="w-8 h-8 rounded-lg bg-status-failed-bg border border-status-failed/30 flex items-center justify-center text-status-failed">
              <XCircle className="w-4 h-4" />
            </div>
          </div>
          <div>
            <span className="text-2xl font-bold text-status-failed block">
              {testRun.failed_tests}
            </span>
            <span className="text-[11px] text-muted">Defects surfaced</span>
          </div>
        </div>

        <div className="bg-card rounded-xl p-4 border border-border-card shadow-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-muted text-[10px] uppercase font-semibold tracking-wider">Errors</span>
            <div className="w-8 h-8 rounded-lg bg-status-error-bg border border-status-error/30 flex items-center justify-center text-status-error">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div>
            <span className="text-2xl font-bold text-status-error block">
              {testRun.error_tests}
            </span>
            <span className="text-[11px] text-muted">Runtime exceptions</span>
          </div>
        </div>

        <div className="bg-card rounded-xl p-4 border border-border-card shadow-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-muted text-[10px] uppercase font-semibold tracking-wider">Latency</span>
            <div className="w-8 h-8 rounded-lg bg-secondaryAccent/10 border border-secondaryAccent/20 flex items-center justify-center text-secondaryAccent">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div>
            <span className="text-2xl font-bold text-primary font-mono block">
              {Number(testRun.duration_ms ?? 0).toFixed(0)} <span className="text-xs font-normal font-sans text-muted">ms</span>
            </span>
            <span className="text-[11px] text-muted">Execution SLA</span>
          </div>
        </div>
      </div>

      {/* Results Filter Bar */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          {(
            [
              { key: 'ALL', label: 'All Steps' },
              { key: 'PASS', label: 'Passed' },
              { key: 'FAIL', label: 'Failed' },
              { key: 'ERROR', label: 'Errors' },
            ] as const
          ).map((item) => {
            const isActive = filter === item.key;
            return (
              <button
                key={item.key}
                onClick={() => setFilter(item.key)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-brand text-on-brand shadow-sm'
                    : 'bg-card text-secondary hover:text-primary border border-border-card hover:bg-hover'
                }`}
              >
                {item.label}
              </button>
            );
          })}
        </div>
        <span className="text-xs text-muted">
          Showing {filteredResults.length} test steps (click row to drill down)
        </span>
      </div>

      {/* Step Results Table */}
      <div className="bg-card rounded-2xl border border-border-card shadow-card overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-field text-secondary border-b border-border-card uppercase text-[10px] font-semibold tracking-wider">
            <tr>
              <th className="px-5 py-3">Outcome</th>
              <th className="px-5 py-3">Method</th>
              <th className="px-5 py-3">Endpoint Path</th>
              <th className="px-5 py-3">Test Type</th>
              <th className="px-5 py-3">Status Code</th>
              <th className="px-5 py-3">Latency</th>
              <th className="px-5 py-3">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-card text-secondary">
            {isRunning && currentTest && (
              <tr className="bg-brand/5 border-l-4 border-l-brand hover:bg-brand/10 transition-colors">
                <td className="px-5 py-3">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-brand/10 text-brand border border-brand/30 animate-pulse">
                    <Loader2 className="w-3 h-3 animate-spin" /> RUNNING
                  </span>
                </td>
                <td className="px-5 py-3 font-mono font-bold text-brand">{currentTest.method}</td>
                <td className="px-5 py-3 font-mono text-primary font-bold">
                  <span>{currentTest.path}</span>
                  <span className="text-[10px] text-muted font-sans font-normal ml-2">({currentTest.name})</span>
                </td>
                <td className="px-5 py-3 text-secondary font-medium">Step {currentTest.index} / {currentTest.total}</td>
                <td className="px-5 py-3 font-mono text-brand font-semibold animate-pulse">in-flight...</td>
                <td className="px-5 py-3 font-mono text-muted">--</td>
                <td className="px-5 py-3 text-brand text-[11px] font-semibold">Executing in sandbox</td>
              </tr>
            )}
            {filteredResults.map((res) => {
              const isExpanded = expandedId === res.id;
              return (
                <React.Fragment key={res.id}>
                  <tr
                    onClick={() => setExpandedId(isExpanded ? null : res.id)}
                    className={`hover:bg-hover transition-colors cursor-pointer group ${
                      isExpanded ? 'bg-hover/60 border-l-4 border-l-brand' : ''
                    }`}
                  >
                    <td className="px-5 py-3">
                      <TestStatusBadge
                        status={mapOutcomeToStatus(res.outcome)}
                        label={res.outcome}
                      />
                    </td>
                    <td className="px-5 py-3 font-mono font-bold text-primary">{res.method}</td>
                    <td className="px-5 py-3 font-mono text-brand font-semibold">{res.endpoint}</td>
                    <td className="px-5 py-3 text-secondary">{res.test_type}</td>
                    <td className="px-5 py-3 font-mono font-semibold text-primary">{res.status_code || '—'}</td>
                    <td className="px-5 py-3 font-mono text-muted">{res.execution_time_ms} ms</td>
                    <td className="px-5 py-3 text-muted group-hover:text-primary transition-colors">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-brand" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </td>
                  </tr>

                  {/* Drill Down Expandable Row */}
                  {isExpanded && (
                    <tr className="bg-field border-b border-border-card">
                      <td colSpan={7} className="p-5 space-y-4">
                        {/* Assertion Failures Alert */}
                        {res.assertion_failures && res.assertion_failures.length > 0 && (
                          <div className="p-3.5 rounded-xl bg-status-failed-bg border border-status-failed/30 text-xs space-y-1">
                            <span className="text-status-failed font-bold flex items-center gap-1.5">
                              <AlertTriangle className="w-4 h-4" /> Assertion Violations ({res.assertion_failures.length})
                            </span>
                            {res.assertion_failures.map((f, idx) => (
                              <p key={idx} className="text-status-failed pl-5 leading-relaxed font-mono">
                                {f.message}
                              </p>
                            ))}
                          </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                          {/* Request Payload */}
                          <div className="p-4 rounded-xl bg-card border border-border-card shadow-sm space-y-2">
                            <span className="text-brand font-bold uppercase text-[10px] tracking-wider block">
                              Request Payload (SSRF Guarded & Secret Redacted)
                            </span>
                            <pre className="overflow-x-auto text-[11px] text-primary bg-field p-3 rounded-lg border border-border-field font-mono">
                              {JSON.stringify(res.request_data, null, 2)}
                            </pre>
                          </div>

                          {/* Response Payload */}
                          <div className="p-4 rounded-xl bg-card border border-border-card shadow-sm space-y-2">
                            <span className="text-status-passed font-bold uppercase text-[10px] tracking-wider block">
                              Sandbox HTTP Response Data
                            </span>
                            <pre className="overflow-x-auto text-[11px] text-primary bg-field p-3 rounded-lg border border-border-field font-mono">
                              {JSON.stringify(res.response_data, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
