import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Play,
  StopCircle,
  RefreshCw,
  Info,
  Shield,
  Layers,
  FileText,
  ChevronRight,
  ChevronDown,
  Terminal,
} from 'lucide-react';
import { api } from '../services/api';
import { Button } from '../components/common/Button';
import { TestStatusBadge, type TestStatus } from '../components/common/TestStatusBadge';

interface TestRun {
  id: string;
  project_id: string;
  suite_id: string;
  status: 'PENDING' | 'STARTING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'TIMED_OUT' | 'CANCELLED' | 'ENVIRONMENT_ERROR';
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  error_tests: number;
  duration_ms: number;
  target_environment: { base_url?: string; environment_type?: string };
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
    if (testRun && (testRun.status === 'PENDING' || testRun.status === 'STARTING' || testRun.status === 'RUNNING')) {
      const timer = setInterval(() => {
        fetchTestRun();
        fetchResults();
      }, 2000);
      return () => clearInterval(timer);
    }
  }, [testRun]);

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
      <div className="text-center py-20 text-muted text-sm font-mono flex flex-col items-center gap-3">
        <div className="w-6 h-6 border-2 border-brand border-t-transparent rounded-full animate-spin" />
        <span>Loading execution telemetry...</span>
      </div>
    );
  }

  if (error || !testRun) {
    return (
      <div className="glass-card rounded-2xl p-8 text-center space-y-4 border border-border max-w-md mx-auto">
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
  const isRunning = testRun.status === 'RUNNING' || testRun.status === 'STARTING' || testRun.status === 'PENDING';

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb Navigation */}
      <div className="flex items-center gap-3 text-xs text-muted">
        <Link to="/projects" className="hover:text-primary transition-colors">
          Projects
        </Link>
        <span>/</span>
        <Link to={`/projects/${projectId}`} className="hover:text-primary transition-colors">
          Project Cockpit
        </Link>
        <span>/</span>
        <span className="text-primary font-semibold font-mono">Run #{testRun.id.substring(0, 8)}</span>
      </div>

      {/* Plain Language Status Banner (Status First principle) */}
      <div className="glass-panel rounded-xl p-4 border border-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {failedCount === 0 ? (
            <div className="p-2 rounded-lg bg-status-passed-bg border border-status-passed-border text-status-passed">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          ) : (
            <div className="p-2 rounded-lg bg-status-failed-bg border border-status-failed-border text-status-failed">
              <XCircle className="w-5 h-5" />
            </div>
          )}
          <div>
            <p className="text-sm font-bold text-primary">
              {failedCount === 0
                ? `All ${passedCount} tests passed smoothly after your last execution`
                : `${failedCount} ${failedCount === 1 ? 'test' : 'tests'} failed after your last change`}
            </p>
            <p className="text-xs text-muted">
              Target environment sandbox: <span className="font-mono text-secondary">{testRun.target_environment.base_url || 'http://localhost:8000'}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
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

      {/* KPI Key Numbers Grid - Features Volt Lime on Key Metric Numbers */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 font-mono">
        <div className="glass-card rounded-xl p-4 border border-border">
          <span className="text-muted text-[10px] uppercase block tracking-wider">Total Tests</span>
          {/* Volt Lime highlight for the key number on this screen */}
          <span className="text-2xl font-black text-accent mt-1 block">
            {results.length} / {testRun.total_tests}
          </span>
          <span className="text-[11px] text-muted">Executed steps</span>
        </div>

        <div className="glass-card rounded-xl p-4 border border-border">
          <span className="text-muted text-[10px] uppercase block tracking-wider">Passed</span>
          <span className="text-2xl font-bold text-status-passed mt-1 block">
            {testRun.passed_tests}
          </span>
          <span className="text-[11px] text-muted">Assertions verified</span>
        </div>

        <div className="glass-card rounded-xl p-4 border border-border">
          <span className="text-muted text-[10px] uppercase block tracking-wider">Failed</span>
          <span className="text-2xl font-bold text-status-failed mt-1 block">
            {testRun.failed_tests}
          </span>
          <span className="text-[11px] text-muted">Defects surfaced</span>
        </div>

        <div className="glass-card rounded-xl p-4 border border-border">
          <span className="text-muted text-[10px] uppercase block tracking-wider">Errors</span>
          <span className="text-2xl font-bold text-status-error mt-1 block">
            {testRun.error_tests}
          </span>
          <span className="text-[11px] text-muted">Runtime exceptions</span>
        </div>

        <div className="glass-card rounded-xl p-4 border border-border">
          <span className="text-muted text-[10px] uppercase block tracking-wider">Latency</span>
          <span className="text-2xl font-bold text-primary mt-1 block">
            {Number(testRun.duration_ms ?? 0).toFixed(0)} ms
          </span>
          <span className="text-[11px] text-muted">Total execution SLA</span>
        </div>
      </div>

      {/* Results Filter Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {(['ALL', 'PASS', 'FAIL', 'ERROR'] as const).map((tab) => {
            const isActive = filter === tab;
            return (
              <button
                key={tab}
                onClick={() => setFilter(tab)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all ${
                  isActive
                    ? 'bg-brand text-white shadow-brand-glow'
                    : 'bg-surface text-secondary hover:text-primary border border-border'
                }`}
              >
                {tab === 'ALL' ? 'All Steps' : tab}
              </button>
            );
          })}
        </div>
        <span className="text-xs font-mono text-muted">
          Showing {filteredResults.length} test steps (click row to drill down)
        </span>
      </div>

      {/* Step Results Table */}
      <div className="glass-card rounded-2xl border border-border overflow-hidden">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-raised text-muted border-b border-border uppercase text-[10px]">
            <tr>
              <th className="px-4 py-3">Outcome</th>
              <th className="px-4 py-3">Method</th>
              <th className="px-4 py-3">Endpoint Path</th>
              <th className="px-4 py-3">Test Type</th>
              <th className="px-4 py-3">Status Code</th>
              <th className="px-4 py-3">Latency</th>
              <th className="px-4 py-3">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border text-secondary">
            {filteredResults.map((res) => (
              <React.Fragment key={res.id}>
                <tr
                  onClick={() => setExpandedId(expandedId === res.id ? null : res.id)}
                  className="hover:bg-raised/60 transition-colors cursor-pointer group"
                >
                  <td className="px-4 py-3">
                    <TestStatusBadge
                      status={mapOutcomeToStatus(res.outcome)}
                      label={res.outcome}
                    />
                  </td>
                  <td className="px-4 py-3 font-bold text-primary">{res.method}</td>
                  <td className="px-4 py-3 text-brand font-semibold">{res.endpoint}</td>
                  <td className="px-4 py-3 text-muted">{res.test_type}</td>
                  <td className="px-4 py-3 font-semibold text-primary">{res.status_code || '—'}</td>
                  <td className="px-4 py-3 text-muted">{res.execution_time_ms} ms</td>
                  <td className="px-4 py-3 text-muted group-hover:text-primary transition-colors">
                    {expandedId === res.id ? (
                      <ChevronDown className="w-4 h-4 text-brand" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </td>
                </tr>

                {/* Drill Down Expandable Row */}
                {expandedId === res.id && (
                  <tr className="bg-raised/40 border-b border-border">
                    <td colSpan={7} className="p-4 space-y-4">
                      {/* Assertion Failures Alert */}
                      {res.assertion_failures && res.assertion_failures.length > 0 && (
                        <div className="p-3 rounded-xl bg-status-failed-bg border border-status-failed-border text-xs font-mono space-y-1">
                          <span className="text-status-failed font-bold flex items-center gap-1.5">
                            <AlertTriangle className="w-4 h-4" /> Assertion Violations ({res.assertion_failures.length})
                          </span>
                          {res.assertion_failures.map((f, idx) => (
                            <p key={idx} className="text-status-failed pl-5 leading-relaxed">
                              {f.message}
                            </p>
                          ))}
                        </div>
                      )}

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
                        {/* Request Payload */}
                        <div className="p-3.5 rounded-xl bg-surface border border-border space-y-2">
                          <span className="text-brand font-bold uppercase text-[10px] block">
                            // Request Payload (SSRF Guarded & Secret Redacted)
                          </span>
                          <pre className="overflow-x-auto text-[11px] text-secondary bg-base p-2.5 rounded border border-border">
                            {JSON.stringify(res.request_data, null, 2)}
                          </pre>
                        </div>

                        {/* Response Payload */}
                        <div className="p-3.5 rounded-xl bg-surface border border-border space-y-2">
                          <span className="text-status-passed font-bold uppercase text-[10px] block">
                            // Sandbox HTTP Response Data
                          </span>
                          <pre className="overflow-x-auto text-[11px] text-secondary bg-base p-2.5 rounded border border-border">
                            {JSON.stringify(res.response_data, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
