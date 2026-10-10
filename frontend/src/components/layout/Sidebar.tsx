import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, FolderGit2, ShieldCheck, Activity, Cpu, LogOut, Terminal, BarChart3, FlaskConical } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { StatusBadge } from '../common/StatusBadge';

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuthStore();

  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/projects', label: 'Projects', icon: FolderGit2 },
    { to: '/analytics', label: 'Executive Analytics', icon: BarChart3 },
    { to: '/benchmarks', label: 'Research Benchmark', icon: FlaskConical },
  ];

  const placeholderNavItems = [
    { label: 'Test Execution', icon: Activity, badge: 'Phase 3' },
    { label: 'AI Requirements', icon: Cpu, badge: 'Phase 5' },
    { label: 'Defect Analysis', icon: ShieldCheck, badge: 'Phase 6' },
  ];

  return (
    <aside className="w-64 glass-panel flex flex-col h-screen border-r border-slate-800 shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-5 flex items-center gap-3 border-b border-slate-800/80">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/25">
          <Terminal className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="font-extrabold text-lg text-white tracking-wider flex items-center gap-1.5">
            ASTRA <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">v1.0</span>
          </h1>
          <p className="text-xs text-slate-400 font-medium">Testing & Quality Platform</p>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">
        <div className="space-y-1">
          <p className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Core Workspace</p>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-gradient-to-r from-indigo-600/20 to-blue-600/10 text-indigo-400 border border-indigo-500/30 shadow-md shadow-indigo-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`
                }
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </div>

        {/* Upcoming Modules Preview */}
        <div className="space-y-1">
          <p className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Engine Modules</p>
          {placeholderNavItems.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.label}
                className="flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium text-slate-600 opacity-60 cursor-not-allowed"
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </div>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-500">
                  {item.badge}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* User Footer */}
      {user && (
        <div className="p-4 border-t border-slate-800/80 bg-slate-900/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-indigo-400 font-bold shrink-0">
                {user.full_name.charAt(0).toUpperCase()}
              </div>
              <div className="truncate">
                <p className="text-xs font-semibold text-slate-200 truncate">{user.full_name}</p>
                <StatusBadge role={user.role} />
              </div>
            </div>
            <button
              onClick={logout}
              title="Logout"
              className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </aside>
  );
};
