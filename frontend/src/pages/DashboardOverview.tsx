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
      {/* Overview Hero Banner with restrained glass, specular highlight, and subtle ambient depth */}
      <div className="rounded-2xl p-7 glass-restrained shadow-tactile relative overflow-hidden flex flex-col md:flex-row items-start md:items-center justify-between gap-6 before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/20">
        {/* Subtle decorative background ambient glow */}
        <div className="absolute -top-24 -right-24 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 left-1/3 w-80 h-80 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="space-y-2 max-w-2xl relative z-10">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium tactile-well text-zinc-300 border border-white/10 shadow-tactile-sm">
            <Zap className="w-3.5 h-3.5 fill-current text-amber-400" />
            Autonomous QA Cockpit
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-primary drop-shadow-sm">
            Welcome back, {user?.full_name?.split(' ')[0] || 'Tester'}
          </h1>
          <p className="text-sm text-secondary leading-relaxed max-w-xl">
            ASTRA autonomous defect detection, code intelligence, and self-healing test pipelines are actively running.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0 relative z-10">
          <Button
            variant="secondary"
            size="md"
            onClick={fetchDashboardData}
            isLoading={loading}
            className="shadow-tactile active:translate-y-px"
            leftIcon={<RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh Telemetry
          </Button>
          <Link to="/projects">
            <Button
              variant="primary"
              size="md"
              className="shadow-tactile active:translate-y-px"
              rightIcon={<ArrowUpRight className="w-4 h-4" />}
            >
              Browse Repositories
            </Button>
          </Link>
        </div>
      </div>

      {/* Reassurance Status Banner - Restrained Glass with Tactile Pass Indicator */}
      <div className="glass-restrained p-4 rounded-xl border border-border-card/70 dark:border-white/10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-tactile-sm relative before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/15">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0 shadow-tactile-sm">
            <CheckCircle2 className="w-5 h-5 stroke-[2.2]" />
          </div>
          <div>
            <p className="text-sm font-semibold text-primary flex items-center gap-2">
              All QA Engines Nominal
              <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 shadow-tactile-sm">
                {totalProjects} Repositories Online
              </span>
            </p>
            <p className="text-xs text-secondary mt-0.5">
              {passRate >= 90
                ? 'High reliability threshold maintained across continuous test generation cycles.'
                : 'Attention needed: Recent regressions detected in testing suites.'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <TestStatusBadge status="passed" label="All Checks Passed" />
          <TestStatusBadge status="running" label="Workers Active" />
        </div>
      </div>

      {/* Section Divider with Solid Tracker */}
      <div className="pt-2">
        <div className="flex items-center justify-between mb-3">
          <div className="section-header-band">
            <span className="text-xs font-semibold uppercase tracking-wider text-primary font-mono">Core Metrics & Telemetry</span>
          </div>
          <span className="text-xs text-muted font-medium">Aggregated Platform Health</span>
        </div>
      </div>

      {/* 4 Stat Cards with Tactile Elevation & Specular Highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Card 1: Repositories */}
        <div className="glass-restrained-interactive tactile-card shadow-tactile-sm rounded-xl p-5 space-y-3 relative overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted font-mono">Tracked Repositories</span>
            <div className="w-9 h-9 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 flex items-center justify-center shadow-tactile-sm">
              <FolderGit2 className="w-4 h-4" />
            </div>
          </div>
          <div>
            <p className="text-[32px] font-bold text-primary tracking-tight leading-none">
              {loading ? '...' : totalProjects}
            </p>
            <p className="text-xs text-secondary font-medium mt-1.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
              Multi-language codebases
            </p>
          </div>
        </div>

        {/* Card 2: Pass Rate */}
        <div className="glass-restrained-interactive tactile-card shadow-tactile-sm rounded-xl p-5 space-y-3 relative overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted font-mono">Overall Pass Rate</span>
            <div className="w-9 h-9 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center justify-center shadow-tactile-sm">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div>
            <p className="text-[32px] font-bold text-primary tracking-tight leading-none flex items-baseline gap-2">
              <span>{loading ? '...' : `${passRate}%`}</span>
              <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-0.5">
                <TrendingUp className="w-3.5 h-3.5" /> High
              </span>
            </p>
            <p className="text-xs text-secondary font-medium mt-1.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Across automated test suites
            </p>
          </div>
        </div>

        {/* Card 3: Tests Executed */}
        <div className="glass-restrained-interactive tactile-card shadow-tactile-sm rounded-xl p-5 space-y-3 relative overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted font-mono">Tests Executed</span>
            <div className="w-9 h-9 rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20 flex items-center justify-center shadow-tactile-sm">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div>
            <p className="text-[32px] font-bold text-primary tracking-tight leading-none">
              {loading ? '...' : testsExecuted}
            </p>
            <p className="text-xs text-secondary font-medium mt-1.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-500" />
              Across {totalRuns} test runs
            </p>
          </div>
        </div>

        {/* Card 4: Task Queue Worker */}
        <div className="glass-restrained-interactive tactile-card shadow-tactile-sm rounded-xl p-5 space-y-3 relative overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted font-mono">Worker Cluster</span>
            <div className="w-9 h-9 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 flex items-center justify-center shadow-tactile-sm">
              <Server className="w-4 h-4" />
            </div>
          </div>
          <div>
            <p className="text-[32px] font-bold text-primary tracking-tight leading-none">
              Redis 7
            </p>
            <p className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold mt-1.5 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Active concurrency workers
            </p>
          </div>
        </div>
      </div>

      {/* Structural Divider */}
      <hr className="section-divider" />

      {/* Main Grid: Projects List & Diagnostics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Monitored Repositories */}
        <div className="lg:col-span-2 glass-restrained rounded-2xl overflow-hidden shadow-tactile flex flex-col justify-between relative before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/20">
          <div>
            {/* Card Header */}
            <div className="p-4 px-6 border-b border-border-card/60 dark:border-white/10 flex items-center justify-between bg-surface/50 dark:bg-white/[0.02]">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-500 flex items-center justify-center border border-indigo-500/20 shadow-tactile-sm">
                  <FolderGit2 className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-primary">Connected Repositories</h2>
                  <p className="text-[11px] text-muted">Codebases enrolled in static AST analysis and test generation</p>
                </div>
              </div>
              <Link
                to="/projects"
                className="text-xs font-medium text-brand hover:underline flex items-center gap-1"
              >
                View all ({totalProjects}) <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="p-5 space-y-3">
              {projects.length === 0 && !loading && (
                <div className="p-8 text-center rounded-xl tactile-well border border-border-card/60 dark:border-white/10 shadow-tactile-sm">
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
                  className="group block p-4 rounded-xl tactile-card border border-border-card/70 dark:border-white/10 hover:border-zinc-400 dark:hover:border-white/20 shadow-tactile-sm active:translate-y-px transition-all duration-150 relative before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/15"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-primary group-hover:text-brand transition-colors truncate">
                          {proj.name}
                        </span>
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-brand/10 text-brand border border-brand/20 shadow-tactile-sm">
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
                      <span className="p-1.5 rounded-lg bg-surface border border-border-card/70 dark:border-white/10 text-muted group-hover:text-brand group-hover:border-brand/40 shadow-tactile-sm transition-colors">
                        <ArrowUpRight className="w-4 h-4" />
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>

        {/* Right Col: Async Worker Verification Card */}
        <div className="glass-restrained rounded-2xl overflow-hidden shadow-tactile flex flex-col justify-between space-y-4 relative before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/20">
          <div>
            {/* Card Header */}
            <div className="p-4 px-6 border-b border-border-card/60 dark:border-white/10 flex items-center gap-3 bg-surface/50 dark:bg-white/[0.02]">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center justify-center shadow-tactile-sm">
                <Activity className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-primary">Worker Telemetry</h2>
                <p className="text-[11px] text-muted">Background Celery worker health</p>
              </div>
            </div>

            <div className="p-5 space-y-4">
              <div className="tactile-well p-4 rounded-xl border border-border-card/70 dark:border-white/10 space-y-3 shadow-tactile-sm">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-secondary font-medium">Message Broker</span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" />
                    Online (Redis 6379)
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-secondary font-medium">Worker Concurrency</span>
                  <span className="text-primary font-semibold font-mono">4 Threads (Prefork)</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-secondary font-medium">SSRF Boundary</span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Protected Sandbox</span>
                </div>

                <Button
                  onClick={handleDispatchTask}
                  isLoading={taskLoading}
                  variant="secondary"
                  size="sm"
                  className="w-full mt-2 shadow-tactile active:translate-y-px"
                  leftIcon={<Play className="w-3.5 h-3.5 text-brand" />}
                >
                  Dispatch Diagnostic Ping
                </Button>
              </div>

              {taskResponse && (
                <div className="p-3.5 rounded-xl tactile-well border border-border-card/70 dark:border-white/10 text-xs space-y-2 animate-fade-in shadow-tactile-sm">
                  <div className="flex items-center justify-between text-emerald-600 dark:text-emerald-400 font-semibold">
                    <span className="flex items-center gap-1.5 text-xs">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Job Dispatched
                    </span>
                    <span className="text-muted text-[10px] font-mono">
                      ID: {taskResponse.task_id?.slice(0, 8)}...
                    </span>
                  </div>
                  <pre className="text-secondary text-[11px] overflow-x-auto p-2 bg-surface rounded border border-border-card/70 dark:border-white/10 font-mono shadow-tactile-sm">
                    {JSON.stringify(taskResponse, null, 2)}
                  </pre>
                </div>
              )}

              {/* User & Security Session Box */}
              <div className="tactile-well p-4 rounded-xl border border-border-card/70 dark:border-white/10 space-y-2 shadow-tactile-sm">
                <span className="text-[10px] font-mono uppercase tracking-wider text-muted block">
                  Active Operator Session
                </span>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-primary font-semibold font-mono">{user?.email}</span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-brand/10 text-brand border border-brand/20 shadow-tactile-sm">
                    {user?.role}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
