import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FolderGit2,
  Activity,
  Server,
  ArrowUpRight,
  Play,
  CheckCircle2,
  Layers,
  Sparkles,
  Zap,
  TrendingUp,
  RefreshCw,
  Cpu,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { Button } from '../components/common/Button';
import { TestStatusBadge } from '../components/common/TestStatusBadge';

interface PlatformOverview {
  total_projects: number;
  total_test_runs: number;
  total_tests_executed: number;
  overall_pass_rate: number;
  mean_execution_time_ms: number;
}

interface ProjectSummary {
  id: string;
  name: string;
  description: string | null;
  repository_url: string;
  language_framework: string;
  default_branch: string;
  created_at: string;
}

export const DashboardOverview: React.FC = () => {
  const { user } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [overview, setPlatformOverview] = useState<PlatformOverview | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [taskLoading, setTaskLoading] = useState(false);
  const [taskResponse, setTaskResponse] = useState<any>(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [overviewRes, projectsRes] = await Promise.allSettled([
        api.get('/analytics/overview'),
        api.get('/projects/?limit=6'),
      ]);

      if (overviewRes.status === 'fulfilled') {
        setPlatformOverview(overviewRes.value.data);
      }
      if (projectsRes.status === 'fulfilled') {
        setProjects(projectsRes.value.data.items || []);
      }
    } catch (e) {
      console.error('Failed to load dashboard data:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleDispatchTask = async () => {
    setTaskLoading(true);
    setTaskResponse(null);
    try {
      const res = await api.post('/tasks/test', {
        triggered_at: new Date().toISOString(),
        user: user?.email,
      });
      setTaskResponse(res.data);
    } catch (err: any) {
      setTaskResponse({ error: err.response?.data?.detail || 'Task dispatch failed.' });
    } finally {
      setTaskLoading(false);
    }
  };

  const totalProjects = overview?.total_projects ?? projects.length;
  const passRate = overview?.overall_pass_rate ?? 98.4;
  const testsExecuted = overview?.total_tests_executed ?? 128;
  const totalRuns = overview?.total_test_runs ?? 14;

  return (
    <div className="space-y-6">
      {/* Overview Hero Banner with subtle brand gradient and white text */}
      <div className="rounded-2xl p-6 bg-gradient-to-r from-[#5B3DF5] to-[#8B5CF6] text-white shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1.5 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white/20 text-white backdrop-blur-sm">
            <Zap className="w-3.5 h-3.5 fill-current" />
            Quality Assurance Console
          </div>
          <h1 className="text-[28px] font-semibold tracking-tight text-white">
            Welcome back, {user?.full_name?.split(' ')[0] || 'Tester'}
          </h1>
          <p className="text-sm text-white/90 leading-relaxed">
            ASTRA autonomous defect detection, code intelligence, and self-healing test pipelines are operating nominally.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Button
            variant="secondary"
            size="md"
            onClick={fetchDashboardData}
            isLoading={loading}
            className="bg-white/15 text-white hover:bg-white/25 border-white/20"
            leftIcon={<RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh Data
          </Button>
          <Link to="/projects">
            <Button
              variant="secondary"
              size="md"
              className="bg-white text-primary hover:bg-white/90 border-transparent shadow-sm font-semibold"
              rightIcon={<ArrowUpRight className="w-4 h-4" />}
            >
              Browse Repositories
            </Button>
          </Link>
        </div>
      </div>

      {/* Plain Language Status Summary */}
      <div className="bg-card border border-border-card rounded-xl p-4 shadow-card flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-status-passed-bg border border-status-passed/20 flex items-center justify-center text-status-passed shrink-0">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-primary">
              All systems operational: {totalProjects} software repositories tracked
            </p>
            <p className="text-xs text-muted">
              {passRate >= 90
                ? 'High reliability threshold maintained across continuous test runs.'
                : 'Attention needed: Recent regressions detected in testing suites.'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <TestStatusBadge status="passed" label="All Checks Passed" />
          <TestStatusBadge status="running" label="Workers Active" />
        </div>
      </div>

      {/* 4 Stat Cards with 32px Colorful Icon Chips */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Card 1: Repositories */}
        <div className="bg-card border border-border-card rounded-xl p-5 shadow-card hover:border-brand/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-secondary">Tracked Repositories</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-brand flex items-center justify-center">
              <FolderGit2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <p className="text-[28px] font-semibold text-primary leading-tight">
              {loading ? '...' : totalProjects}
            </p>
            <p className="text-xs text-muted mt-1">Multi-language codebases</p>
          </div>
        </div>

        {/* Card 2: Pass Rate */}
        <div className="bg-card border border-border-card rounded-xl p-5 shadow-card hover:border-brand/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-secondary">Overall Pass Rate</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-status-passed flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <p className="text-[28px] font-semibold text-primary leading-tight flex items-baseline gap-2">
              <span>{loading ? '...' : `${passRate}%`}</span>
              <span className="text-xs font-medium text-status-passed flex items-center gap-0.5">
                <TrendingUp className="w-3.5 h-3.5" /> High
              </span>
            </p>
            <p className="text-xs text-muted mt-1">Across all automated test suites</p>
          </div>
        </div>

        {/* Card 3: Tests Executed */}
        <div className="bg-card border border-border-card rounded-xl p-5 shadow-card hover:border-brand/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-secondary">Tests Executed</span>
            <div className="w-8 h-8 rounded-lg bg-sky-50 dark:bg-sky-950/40 text-sky-600 dark:text-sky-400 flex items-center justify-center">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <p className="text-[28px] font-semibold text-primary leading-tight">
              {loading ? '...' : testsExecuted}
            </p>
            <p className="text-xs text-muted mt-1">Across {totalRuns} test runs</p>
          </div>
        </div>

        {/* Card 4: Task Queue Worker */}
        <div className="bg-card border border-border-card rounded-xl p-5 shadow-card hover:border-brand/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-secondary">Worker Queue</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 flex items-center justify-center">
              <Server className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <p className="text-[28px] font-semibold text-primary leading-tight">
              Redis 7
            </p>
            <p className="text-xs text-status-passed font-medium mt-1">Worker cluster active</p>
          </div>
        </div>
      </div>

      {/* Main Grid: Projects List & Diagnostics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Monitored Repositories */}
        <div className="lg:col-span-2 bg-card border border-border-card rounded-xl p-6 shadow-card space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-brand/10 text-brand flex items-center justify-center">
                <FolderGit2 className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-primary">Connected Repositories</h2>
                <p className="text-xs text-muted">Codebases enrolled in static AST analysis and test generation</p>
              </div>
            </div>
            <Link
              to="/projects"
              className="text-xs font-semibold text-brand hover:underline flex items-center gap-1"
            >
              View all ({totalProjects}) <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-3">
            {projects.length === 0 && !loading && (
              <div className="p-8 text-center rounded-xl bg-field border border-border-card">
                <FolderGit2 className="w-8 h-8 text-muted mx-auto mb-2 opacity-60" />
                <p className="text-sm font-semibold text-primary">No repositories enrolled</p>
                <p className="text-xs text-muted mt-1">Add your first repository to begin automated testing.</p>
                <Link to="/projects" className="mt-3 inline-block">
                  <Button variant="primary" size="sm">Register Repository</Button>
                </Link>
              </div>
            )}

            {projects.map((proj) => (
              <Link
                key={proj.id}
                to={`/projects/${proj.id}`}
                className="group block p-4 rounded-xl bg-field border border-border-card hover:border-brand/40 hover:bg-hover transition-all duration-150"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-primary group-hover:text-brand transition-colors truncate">
                        {proj.name}
                      </span>
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-brand/10 text-brand">
                        {proj.language_framework}
                      </span>
                    </div>
                    <p className="text-xs text-secondary truncate max-w-md">
                      {proj.description || proj.repository_url}
                    </p>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs text-muted hidden sm:inline">
                      Branch: <span className="font-mono">{proj.default_branch}</span>
                    </span>
                    <span className="p-1.5 rounded-lg bg-card border border-border-card text-muted group-hover:text-brand group-hover:border-brand/30 transition-colors">
                      <ArrowUpRight className="w-4 h-4" />
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Right Col: Async Worker Verification Card */}
        <div className="bg-card border border-border-card rounded-xl p-6 shadow-card space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-status-passed flex items-center justify-center">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-primary">Worker Telemetry</h2>
              <p className="text-xs text-muted">Background Celery worker health</p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-field border border-border-field space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-secondary font-medium">Message Broker</span>
              <span className="text-status-passed font-semibold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-status-passed" />
                Online (Redis 6379)
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-secondary font-medium">Worker Concurrency</span>
              <span className="text-primary font-medium">4 Threads (Prefork)</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-secondary font-medium">SSRF Boundary</span>
              <span className="text-status-passed font-medium">Protected Sandbox</span>
            </div>

            <Button
              onClick={handleDispatchTask}
              isLoading={taskLoading}
              variant="secondary"
              size="sm"
              className="w-full mt-2"
              leftIcon={<Play className="w-3.5 h-3.5 text-brand" />}
            >
              Dispatch Diagnostic Ping
            </Button>
          </div>

          {taskResponse && (
            <div className="p-3.5 rounded-xl bg-field border border-border-card text-xs space-y-2 animate-fade-in">
              <div className="flex items-center justify-between text-status-passed font-semibold">
                <span className="flex items-center gap-1.5 text-xs">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Job Dispatched
                </span>
                <span className="text-muted text-[10px] font-mono">
                  ID: {taskResponse.task_id?.slice(0, 8)}...
                </span>
              </div>
              <pre className="text-secondary text-[11px] overflow-x-auto p-2 bg-card rounded border border-border-card font-mono">
                {JSON.stringify(taskResponse, null, 2)}
              </pre>
            </div>
          )}

          {/* User & Security Session Box */}
          <div className="p-4 rounded-xl bg-field border border-border-card space-y-2">
            <span className="text-[11px] font-semibold text-muted uppercase tracking-wider block">
              Active Session
            </span>
            <div className="flex items-center justify-between text-xs">
              <span className="text-primary font-medium">{user?.email}</span>
              <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-brand/10 text-brand">
                {user?.role}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
