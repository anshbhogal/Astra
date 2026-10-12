import React, { useState, useEffect } from 'react';
import {
  X,
  Search,
  Filter,
  CheckCircle2,
  Code2,
  ChevronDown,
  ChevronUp,
  Play,
  Layers,
  ShieldAlert,
  Clock,
  Check,
  Copy,
  ExternalLink,
  Info,
} from 'lucide-react';
import { api } from '../services/api';
import { Button } from './common/Button';

export interface TestCaseItem {
  id: string;
  suite_id: string;
  endpoint_id?: string | null;
  name: string;
  test_type: string;
  specification: {
    method?: string;
    path?: string;
    endpoint?: string;
    headers?: Record<string, string>;
    query?: Record<string, any>;
    parameters?: Record<string, any>;
    body?: any;
    expected_status?: number;
    expected_status_code?: number;
    assertions?: any[];
    timeout_ms?: number;
    [key: string]: any;
  };
  execution_order: number;
  created_at: string;
}

interface TestSuiteViewerDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  suiteId: string | null;
  suiteName: string;
  totalCasesCount: number;
  isServerRunning?: boolean;
  serverPort?: number | null;
  onRunSuite: (suiteId: string) => void;
  onRequestStartServer?: () => void;
}

export const TestSuiteViewerDrawer: React.FC<TestSuiteViewerDrawerProps> = ({
  isOpen,
  onClose,
  suiteId,
  suiteName,
  totalCasesCount,
  isServerRunning = false,
  serverPort = null,
  onRunSuite,
  onRequestStartServer,
}) => {
  const [testCases, setTestCases] = useState<TestCaseItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMethod, setSelectedMethod] = useState<string>('ALL');
  const [expandedCaseId, setExpandedCaseId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && suiteId) {
      fetchCases();
    } else {
      setTestCases([]);
      setSearchQuery('');
      setSelectedMethod('ALL');
      setExpandedCaseId(null);
    }
  }, [isOpen, suiteId]);

  const fetchCases = async () => {
    if (!suiteId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/test-suites/${suiteId}/cases`);
      setTestCases(res.data.items || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load test suite cases.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const getMethod = (tc: TestCaseItem) => {
    return (tc.specification.method || 'GET').toUpperCase();
  };

  const getPath = (tc: TestCaseItem) => {
    return tc.specification.path || tc.specification.endpoint || '/';
  };

  const getExpectedStatus = (tc: TestCaseItem) => {
    return tc.specification.expected_status || tc.specification.expected_status_code || 200;
  };

  const methods = ['ALL', 'GET', 'POST', 'PUT', 'DELETE', 'PATCH'];

  const filteredCases = testCases.filter((tc) => {
    const method = getMethod(tc);
    const path = getPath(tc);
    const name = tc.name || '';

    const matchesMethod = selectedMethod === 'ALL' || method === selectedMethod;
    const matchesSearch =
      path.toLowerCase().includes(searchQuery.toLowerCase()) ||
      name.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesMethod && matchesSearch;
  });

  const getMethodBadgeClass = (method: string) => {
    switch (method.toUpperCase()) {
      case 'GET':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
      case 'POST':
        return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
      case 'PUT':
        return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
      case 'DELETE':
        return 'bg-rose-500/10 text-rose-500 border-rose-500/20';
      case 'PATCH':
        return 'bg-purple-500/10 text-purple-500 border-purple-500/20';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  const handleCopySpec = (tc: TestCaseItem) => {
    navigator.clipboard.writeText(JSON.stringify(tc.specification, null, 2));
    setCopiedId(tc.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end">
      <div className="w-full max-w-3xl bg-card border-l border-border-card h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="p-5 border-b border-border-card flex items-center justify-between bg-field/30">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center text-brand">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-primary">{suiteName}</h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-field text-secondary border border-border-card">
                  {testCases.length} Tests
                </span>
              </div>
              <p className="text-xs text-muted">
                Inspect test specifications, payloads, assertions, and target endpoints
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-secondary hover:text-primary hover:bg-hover transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Server Status Notice Bar */}
        <div className="px-5 py-2.5 bg-field/60 border-b border-border-card flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                isServerRunning ? 'bg-status-passed animate-ping' : 'bg-muted'
              }`}
            />
            <span className="text-secondary font-medium">
              Target Server:{' '}
              <strong className={isServerRunning ? 'text-status-passed' : 'text-muted'}>
                {isServerRunning ? `RUNNING on port ${serverPort}` : 'NOT RUNNING'}
              </strong>
            </span>
          </div>

          {!isServerRunning && onRequestStartServer && (
            <button
              onClick={onRequestStartServer}
              className="text-brand hover:underline font-semibold text-[11px]"
            >
              Start Server Now &rarr;
            </button>
          )}
        </div>

        {/* Search & Filter Toolbar */}
        <div className="p-4 border-b border-border-card bg-card space-y-3">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search endpoints (e.g. /signup) or test names..."
                className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-field border border-border-card text-xs text-primary placeholder-muted focus:outline-none focus:border-brand"
              />
            </div>
          </div>

          {/* Method Filters */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            <span className="text-muted text-[11px] mr-1 flex items-center gap-1">
              <Filter className="w-3 h-3" /> Method:
            </span>
            {methods.map((m) => (
              <button
                key={m}
                onClick={() => setSelectedMethod(m)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all border ${
                  selectedMethod === m
                    ? 'bg-brand text-on-brand border-brand shadow-sm'
                    : 'bg-field text-secondary border-border-card hover:bg-hover'
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        {/* Test Cases List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
          {loading ? (
            <div className="text-center py-20 text-muted text-xs flex flex-col items-center gap-3">
              <div className="w-6 h-6 border-2 border-brand border-t-transparent rounded-full animate-spin" />
              <span>Loading test suite specifications...</span>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-status-failed-bg border border-status-failed/30 text-status-failed text-xs">
              {error}
            </div>
          ) : filteredCases.length === 0 ? (
            <div className="text-center py-16 text-muted text-xs">
              No test cases matched your filter criteria.
            </div>
          ) : (
            filteredCases.map((tc, idx) => {
              const method = getMethod(tc);
              const path = getPath(tc);
              const expectedStatus = getExpectedStatus(tc);
              const isExpanded = expandedCaseId === tc.id;
              const assertions = tc.specification.assertions || [];
              const hasBody = tc.specification.body && Object.keys(tc.specification.body).length > 0;
              const hasQuery =
                (tc.specification.query && Object.keys(tc.specification.query).length > 0) ||
                (tc.specification.parameters && Object.keys(tc.specification.parameters).length > 0);

              return (
                <div
                  key={tc.id}
                  className="rounded-xl border border-border-card bg-field/40 hover:border-brand/40 transition-colors overflow-hidden"
                >
                  {/* Summary Bar */}
                  <div
                    onClick={() => setExpandedCaseId(isExpanded ? null : tc.id)}
                    className="p-3 flex items-center justify-between cursor-pointer select-none hover:bg-hover/50"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="text-[10px] font-mono text-muted w-5 shrink-0">
                        #{idx + 1}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] border shrink-0 ${getMethodBadgeClass(
                          method
                        )}`}
                      >
                        {method}
                      </span>
                      <span className="font-mono text-xs font-semibold text-primary truncate">
                        {path}
                      </span>
                      <span className="hidden sm:inline-block text-[11px] text-muted truncate">
                        &mdash; {tc.name}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                          expectedStatus < 300
                            ? 'bg-status-passed-bg text-status-passed border-status-passed/30'
                            : expectedStatus < 500
                            ? 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                            : 'bg-status-failed-bg text-status-failed border-status-failed/30'
                        }`}
                      >
                        HTTP {expectedStatus}
                      </span>
                      <button className="text-muted hover:text-primary">
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Expanded Details Drawer */}
                  {isExpanded && (
                    <div className="p-3.5 border-t border-border-card bg-card space-y-3 text-xs">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-secondary font-medium">{tc.name}</span>
                        <div className="flex items-center gap-2">
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-field text-secondary border border-border-card uppercase">
                            {tc.test_type}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleCopySpec(tc)}
                            className="inline-flex items-center gap-1 text-[10px] text-muted hover:text-primary transition-colors"
                            title="Copy full specification JSON"
                          >
                            {copiedId === tc.id ? (
                              <>
                                <Check className="w-3 h-3 text-status-passed" /> Copied
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3" /> Copy Spec
                              </>
                            )}
                          </button>
                        </div>
                      </div>

                      {/* Assertions */}
                      <div className="space-y-1">
                        <span className="text-[10px] uppercase font-semibold text-muted block">
                          Validation Assertions ({assertions.length > 0 ? assertions.length : 1})
                        </span>
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5 text-xs text-secondary">
                            <CheckCircle2 className="w-3.5 h-3.5 text-status-passed shrink-0" />
                            <span>Response status code equals {expectedStatus}</span>
                          </div>
                          {assertions.map((a: any, i: number) => (
                            <div
                              key={i}
                              className="flex items-center gap-1.5 text-xs text-secondary"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5 text-status-passed shrink-0" />
                              <span>
                                {typeof a === 'string'
                                  ? a
                                  : a.description ||
                                    `${a.type || 'check'} on ${a.target || 'response'}: ${JSON.stringify(
                                      a.expected || a.value || ''
                                    )}`}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Request Payload / Query */}
                      {hasBody && (
                        <div className="space-y-1">
                          <span className="text-[10px] uppercase font-semibold text-muted block">
                            Request Body Payload
                          </span>
                          <pre className="p-2.5 rounded-lg bg-field border border-border-card text-[11px] font-mono text-secondary overflow-x-auto max-h-36">
                            {JSON.stringify(tc.specification.body, null, 2)}
                          </pre>
                        </div>
                      )}

                      {hasQuery && (
                        <div className="space-y-1">
                          <span className="text-[10px] uppercase font-semibold text-muted block">
                            Query / Route Parameters
                          </span>
                          <pre className="p-2.5 rounded-lg bg-field border border-border-card text-[11px] font-mono text-secondary overflow-x-auto max-h-24">
                            {JSON.stringify(
                              tc.specification.query || tc.specification.parameters,
                              null,
                              2
                            )}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border-card bg-field/30 flex items-center justify-between">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              if (suiteId) {
                onRunSuite(suiteId);
              }
            }}
            leftIcon={<Play className="w-3 h-3 fill-current" />}
          >
            Run This Suite ({filteredCases.length} Tests)
          </Button>
        </div>
      </div>
    </div>
  );
};
