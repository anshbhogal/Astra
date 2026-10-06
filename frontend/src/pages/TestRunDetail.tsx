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
  ChevronDown
} from 'lucide-react';
import { api } from '../services/api';

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
  response_body_truncated: bool;
  execution_time_ms: number;
  assertion_failures: Array<{ type: string; message: string; expected?: any; actual?: any }>;
  error_message: string | null;
  created_at: string;
}

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
    return <div className="text-center py-16 text-slate-500 text-sm">Loading test run execution telemetry...</div>;
  }

  if (error || !testRun) {
    return (
      <div className="glass-card rounded-2xl p-8 text-center space-y-4 border border-slate-800 max-w-md mx-auto">
        <Info className="w-10 h-10 text-rose-400 mx-auto" />
        <h3 className="text-lg font-bold text-slate-200">Test Run Not Found</h3>
        <p className="text-xs text-slate-400">{error}</p>
        <Link to={`/projects/${projectId}`} className="inline-block text-xs font-semibold text-indigo-400 hover:underline">
          &larr; Return to Project Details
        </Link>
      </div>
    );
  }

  const filteredResults = results.filter(r => {
    if (filter === 'ALL') return true;
    return r.outcome === filter;
  });

  const getOutcomeBadge = (outcome: string) => {
    switch (outcome) {
      case 'PASS': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'FAIL': return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      case 'ERROR': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'TIMEOUT': return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      default: return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Breadcrumbs */}
      <div className="flex items-center gap-3 text-xs text-slate-400">
        <Link to="/projects" className="hover:text-slate-200">Projects</Link>
        <span>/</span>
        <Link to={`/projects/${projectId}`} className="hover:text-slate-200">Project Details</Link>
        <span>/</span>
        <span className="text-slate-200 font-semibold">Test Run #{testRun.id.substring(0, 8)}</span>
      </div>

      {/* Header Banner */}
      <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-extrabold text-white">Execution Run Telemetry</h1>
              <span className={`text-xs font-mono font-bold px-2.5 py-1 rounded border ${
                testRun.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                testRun.status === 'FAILED' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                testRun.status === 'RUNNING' ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' : 'bg-slate-500/10 text-slate-400 border-slate-500/20'
              }`}>
                {testRun.status}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              Target Environment: <code className="text-indigo-400">{testRun.target_environment.base_url || 'http://localhost:8000'}</code>
            </p>
          </div>

          {(testRun.status === 'RUNNING' || testRun.status === 'STARTING' || testRun.status === 'PENDING') && (
            <button
              onClick={handleCancelRun}
              disabled={cancelling}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-xs font-semibold text-rose-400 transition-colors"
            >
              <StopCircle className="w-4 h-4" /> Stop Execution
            </button>
          )}
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 pt-4 border-t border-slate-800/80 font-mono">
          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase block">Total Executed</span>
            <span className="text-lg font-bold text-white mt-0.5 block">{results.length} / {testRun.total_tests}</span>
          </div>
          <div className="p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/10">
            <span className="text-emerald-500/80 text-[10px] uppercase block">Passed</span>
            <span className="text-lg font-bold text-emerald-400 mt-0.5 block">{testRun.passed_tests}</span>
          </div>
          <div className="p-3 rounded-xl bg-rose-500/5 border border-rose-500/10">
            <span className="text-rose-500/80 text-[10px] uppercase block">Failed</span>
            <span className="text-lg font-bold text-rose-400 mt-0.5 block">{testRun.failed_tests}</span>
          </div>
          <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/10">
            <span className="text-amber-500/80 text-[10px] uppercase block">Errors</span>
            <span className="text-lg font-bold text-amber-400 mt-0.5 block">{testRun.error_tests}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase block">Duration</span>
            <span className="text-lg font-bold text-indigo-400 mt-0.5 block">{testRun.duration_ms.toFixed(0)} ms</span>
          </div>
        </div>
      </div>

      {/* Results Filter Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {(['ALL', 'PASS', 'FAIL', 'ERROR'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all ${
                filter === tab ? 'bg-indigo-600 text-white' : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
        <span className="text-xs font-mono text-slate-400">Showing {filteredResults.length} test steps</span>
      </div>

      {/* Step Results Table */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
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
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {filteredResults.map(res => (
              <React.Fragment key={res.id}>
                <tr
                  onClick={() => setExpandedId(expandedId === res.id ? null : res.id)}
                  className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded font-bold border ${getOutcomeBadge(res.outcome)}`}>
                      {res.outcome}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-bold text-white">{res.method}</td>
                  <td className="px-4 py-3 text-indigo-400">{res.endpoint}</td>
                  <td className="px-4 py-3 text-slate-400">{res.test_type}</td>
                  <td className="px-4 py-3">{res.status_code || '—'}</td>
                  <td className="px-4 py-3 text-slate-400">{res.execution_time_ms} ms</td>
                  <td className="px-4 py-3 text-slate-500">
                    {expandedId === res.id ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </td>
                </tr>

                {/* Expanded Detail Drawer */}
                {expandedId === res.id && (
                  <tr className="bg-slate-950/80 border-b border-slate-800">
                    <td colSpan={7} className="p-4 space-y-4">
                      {/* Assertion Failures Alert */}
                      {res.assertion_failures && res.assertion_failures.length > 0 && (
                        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs font-mono space-y-1">
                          <span className="text-rose-400 font-bold flex items-center gap-1">
                            <AlertTriangle className="w-4 h-4" /> Assertion Failures ({res.assertion_failures.length})
                          </span>
                          {res.assertion_failures.map((f, idx) => (
                            <p key={idx} className="text-rose-300 pl-5">{f.message}</p>
                          ))}
                        </div>
                      )}

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
                        {/* Request Payload */}
                        <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                          <span className="text-indigo-400 font-bold uppercase text-[10px] block">// Request Data (Redacted)</span>
                          <pre className="overflow-x-auto text-[11px] text-slate-300">{JSON.stringify(res.request_data, null, 2)}</pre>
                        </div>

                        {/* Response Payload */}
                        <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                          <span className="text-emerald-400 font-bold uppercase text-[10px] block">// Response Data</span>
                          <pre className="overflow-x-auto text-[11px] text-slate-300">{JSON.stringify(res.response_data, null, 2)}</pre>
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
