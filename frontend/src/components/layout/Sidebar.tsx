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
  Zap,
  LogOut,
  Shield,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuthStore();

  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/projects', label: 'Repositories', icon: FolderGit2 },
    { to: '/analytics', label: 'Quality Analytics', icon: BarChart3 },
    { to: '/benchmarks', label: 'Research Benchmarks', icon: FlaskConical },
  ];

  const engineModules = [
    { label: 'Synthetic Suite Gen', icon: Cpu, badge: 'Active' },
    { label: 'Fault Localization', icon: ShieldCheck, badge: 'Active' },
    { label: 'Selective Regression', icon: Activity, badge: 'Active' },
  ];

  return (
    <aside className="w-64 bg-[#171344] dark:bg-[#090A1A] text-white border-r border-black/30 dark:border-white/10 flex flex-col h-screen shrink-0 select-none z-20 transition-colors duration-150">
      {/* Brand Header */}
      <div className="p-5 flex items-center gap-3 border-b border-white/10">
        <div className="w-9 h-9 rounded-xl bg-brand flex items-center justify-center text-white shadow-sm shrink-0">
          <Zap className="w-5 h-5 fill-current" />
        </div>
        <div className="min-w-0">
          <h1 className="font-bold text-base text-white tracking-tight leading-tight flex items-center gap-1.5">
            ASTRA
            <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-brand/35 text-white border border-brand/50">
              v2.0
            </span>
          </h1>
          <p className="text-xs text-indigo-200/90 truncate font-medium">Automated Quality Platform</p>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 px-3 py-5 space-y-6 overflow-y-auto">
        <div className="space-y-1">
          <p className="px-3 text-[11px] font-bold uppercase tracking-wider text-indigo-300/80 mb-2">
            Navigation
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 group ${
                    isActive
                      ? 'bg-gradient-to-r from-brand/45 to-brand/15 text-white font-semibold shadow-sm border-l-4 border-l-brand pl-2.5'
                      : 'text-indigo-200/90 hover:text-white hover:bg-white/10 border-l-4 border-l-transparent pl-2.5'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon className={`w-4 h-4 shrink-0 transition-colors ${isActive ? 'text-white' : 'text-indigo-300 group-hover:text-white'}`} />
                    <span>{item.label}</span>
                  </>
                )}
              </NavLink>
            );
          })}
        </div>

        {/* Engine Pipeline Features */}
        <div className="space-y-1">
          <p className="px-3 text-[11px] font-bold uppercase tracking-wider text-indigo-300/80 mb-2">
            Engines
          </p>
          {engineModules.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.label}
                className="flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium text-indigo-200/90 hover:text-white hover:bg-white/10 transition-colors cursor-default group"
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4 text-indigo-300 group-hover:text-white transition-colors" />
                  <span>{item.label}</span>
                </div>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/15 text-indigo-100 font-semibold border border-white/10">
                  {item.badge}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* User Session Footer */}
      {user && (
        <div className="p-4 border-t border-white/10 bg-black/25">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-lg bg-brand/40 border border-brand/50 flex items-center justify-center text-white font-bold text-xs shrink-0">
                {user.full_name ? user.full_name.charAt(0).toUpperCase() : 'A'}
              </div>
              <div className="truncate min-w-0">
                <p className="text-xs font-semibold text-white truncate leading-tight">{user.full_name || 'Admin User'}</p>
                <span className="inline-flex items-center gap-1 text-[11px] text-indigo-200 capitalize font-medium">
                  <Shield className="w-3 h-3 text-brand" /> {user.role?.toLowerCase() || 'admin'}
                </span>
              </div>
            </div>

            <button
              onClick={logout}
              className="p-1.5 rounded-lg text-indigo-300 hover:text-white hover:bg-white/15 transition-colors"
              title="Sign out"
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
