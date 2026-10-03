import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FolderGit2, Activity, Server, ArrowUpRight, Play, CheckCircle2, Shield, Layers } from 'lucide-react';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { Button } from '../components/common/Button';

export const DashboardOverview: React.FC = () => {
  const { user } = useAuthStore();
  const [projectCount, setProjectCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  // Celery test task state
  const [taskLoading, setTaskLoading] = useState(false);
  const [taskResponse, setTaskResponse] = useState<any>(null);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await api.get('/projects/');
      setProjectCount(res.data.total);
    } catch (e) {
      setProjectCount(0);
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

  return (
    <div className="space-y-6">
      {/* Welcome Hero Banner */}
      <div className="glass-card rounded-2xl p-6 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">
            Welcome back, {user?.full_name}! 👋
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            ASTRA Phase 1 Core Infrastructure is active. All services are containerized and ready.
          </p>
        </div>
        <Link to="/projects">
          <Button variant="primary" rightIcon={<ArrowUpRight className="w-4 h-4" />}>
            Manage Projects
          </Button>
        </Link>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="glass-card rounded-xl p-5 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Projects</span>
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
              <FolderGit2 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white">
            {loading ? '...' : projectCount}
          </p>
          <p className="text-xs text-slate-500">Tracked software repositories</p>
        </div>

        <div className="glass-card rounded-xl p-5 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">User Role</span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <Shield className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-indigo-400">
            {user?.role}
          </p>
          <p className="text-xs text-slate-500">Role-Based Access Control Active</p>
        </div>

        <div className="glass-card rounded-xl p-5 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Celery Task Broker</span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <Server className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-emerald-400">
            Redis 7
          </p>
          <p className="text-xs text-slate-500">Async background worker queue</p>
        </div>
      </div>

      {/* Infrastructure Verification Interactive Card */}
      <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-400" /> Celery Task Queue Dispatch Verification
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Dispatch a test job to verify Redis message broker & background Celery worker execution.
            </p>
          </div>
          <Button
            onClick={handleDispatchTask}
            isLoading={taskLoading}
            variant="secondary"
            leftIcon={<Play className="w-4 h-4 text-emerald-400" />}
          >
            Dispatch Celery Task
          </Button>
        </div>

        {taskResponse && (
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 font-mono text-xs space-y-2 animate-fade-in">
            <div className="flex items-center justify-between text-emerald-400 font-semibold">
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" /> Task Dispatched Successfully
              </span>
              <span className="text-slate-500">Task ID: {taskResponse.task_id}</span>
            </div>
            <pre className="text-slate-300 overflow-x-auto p-2 bg-slate-950 rounded border border-slate-800/60">
              {JSON.stringify(taskResponse, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Phase Roadmap Matrix */}
      <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Layers className="w-5 h-5 text-indigo-400" /> ASTRA Implementation Milestones
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-between">
            <div>
              <p className="font-bold text-indigo-300">Phase 1: Core Foundation & Infrastructure</p>
              <p className="text-slate-400 text-[11px]">Docker, FastAPI, PostgreSQL, Redis, JWT, RBAC, React UI</p>
            </div>
            <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-semibold text-[10px]">ACTIVE</span>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800/80 flex items-center justify-between opacity-70">
            <div>
              <p className="font-semibold text-slate-300">Phase 2: Repository & AST Analyzer</p>
              <p className="text-slate-500 text-[11px]">Git clone, AST static parser, Knowledge Graph</p>
            </div>
            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-500 font-mono text-[10px]">NEXT</span>
          </div>
        </div>
      </div>
    </div>
  );
};
