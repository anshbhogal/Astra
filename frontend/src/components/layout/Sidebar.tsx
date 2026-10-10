import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderGit2,
  BarChart3,
  FlaskConical,
  Activity,
  Cpu,
  ShieldCheck,
  Terminal,
  LogOut,
  ChevronRight,
  Shield
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuthStore();

  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/projects', label: 'Repositories', icon: FolderGit2 },
    { to: '/analytics', label: 'Executive Analytics', icon: BarChart3 },
    { to: '/benchmarks', label: 'Research Benchmarks', icon: FlaskConical },
  ];

  const engineModules = [
    { label: 'Synthetic Suite Gen', icon: Cpu, badge: 'Phase 5' },
    { label: 'Fault Localization', icon: ShieldCheck, badge: 'Phase 6' },
    { label: 'Selective Regression', icon: Activity, badge: 'Phase 7' },
  ];

  return (
    <aside className="w-64 bg-surface border-r border-border flex flex-col h-screen shrink-0 select-none z-20">
      {/* Console Brand Header */}
      <div className="p-5 flex items-center gap-3 border-b border-border">
        <div className="w-10 h-10 rounded-xl bg-brand flex items-center justify-center shadow-lg shadow-brand/25 text-white">
          <Terminal className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-extrabold text-base text-primary tracking-wider flex items-center gap-1.5 font-mono">
            ASTRA <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-brand/20 text-brand border border-brand/30">v1.0</span>
          </h1>
          <p className="text-[11px] text-muted font-medium">Mission Control Console</p>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">
        <div className="space-y-1">
          <p className="px-3 text-[10px] font-bold text-muted uppercase tracking-widest mb-2 font-mono">
            Command Center
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all duration-150 ${
                    isActive
                      ? 'bg-brand/15 text-brand border border-brand/40 shadow-sm'
                      : 'text-secondary hover:text-primary hover:bg-raised/70 border border-transparent'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </div>

        {/* Engine Pipeline Features */}
        <div className="space-y-1">
          <p className="px-3 text-[10px] font-bold text-muted uppercase tracking-widest mb-2 font-mono">
            Active Engines
          </p>
          {engineModules.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.label}
                className="flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium text-muted/70 opacity-60 cursor-not-allowed"
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </div>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-raised text-muted border border-border">
                  {item.badge}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* User Session Footer */}
      {user && (
        <div className="p-4 border-t border-border bg-raised/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-xl bg-brand/20 border border-brand/30 flex items-center justify-center text-brand font-bold text-xs shrink-0">
                {user.full_name ? user.full_name.charAt(0).toUpperCase() : 'A'}
              </div>
              <div className="truncate min-w-0">
                <p className="text-xs font-bold text-primary truncate leading-tight">{user.full_name || 'Admin User'}</p>
                <span className="inline-flex items-center gap-1 text-[10px] font-mono text-muted uppercase">
                  <Shield className="w-2.5 h-2.5 text-brand" /> {user.role || 'ADMIN'}
                </span>
              </div>
            </div>

            <button
              onClick={logout}
              className="p-1.5 rounded-lg text-muted hover:text-status-failed hover:bg-raised transition-colors"
              title="Sign out of console"
              aria-label="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </aside>
  );
};
