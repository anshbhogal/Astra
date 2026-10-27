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
  Code2,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuthStore();

  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/projects', label: 'Repositories', icon: FolderGit2 },
    { to: '/ide', label: 'Code Studio (IDE)', icon: Code2 },
    { to: '/analytics', label: 'Quality Analytics', icon: BarChart3 },
    { to: '/benchmarks', label: 'Research Benchmarks', icon: FlaskConical },
    ...(user?.role === 'ADMIN' ? [{ to: '/admin', label: 'Admin Console', icon: Shield }] : []),
  ];

  const engineModules = [
    { label: 'Synthetic Suite Gen', icon: Cpu, badge: 'Active' },
    { label: 'Fault Localization', icon: ShieldCheck, badge: 'Active' },
    { label: 'Selective Regression', icon: Activity, badge: 'Active' },
  ];

  return (
    <aside className="w-64 bg-[#0B0C14] text-zinc-300 border-r border-white/10 flex flex-col h-screen shrink-0 select-none z-20 transition-colors duration-150 relative">
      {/* Brand Header */}
      <div className="p-4 px-5 flex items-center justify-between border-b border-white/10 relative before:absolute before:inset-x-0 before:bottom-0 before:h-px before:bg-white/5">
        <NavLink to="/" className="flex items-center gap-2 group">
          <img
            src="/astra-logo-dark.svg"
            alt="ASTRA"
            className="h-8 w-auto object-contain transition-transform group-hover:scale-[1.02]"
          />
          <span className="tactile-well text-[10px] font-mono font-medium px-2 py-0.5 rounded text-zinc-300 border border-white/10 shadow-tactile-sm shrink-0">
            v2.0
          </span>
        </NavLink>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 px-3 py-5 space-y-6 overflow-y-auto">
        <div className="space-y-1">
          <p className="px-3 text-[10px] font-mono uppercase tracking-wider text-zinc-500 mb-2">
            Platform Navigation
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 group relative ${
                    isActive
                      ? 'bg-white/10 text-white font-semibold shadow-tactile-sm border border-white/15 before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/20'
                      : 'text-zinc-400 hover:text-white hover:bg-white/[0.04] border border-transparent'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon className={`w-4 h-4 shrink-0 transition-colors ${isActive ? 'text-white' : 'text-zinc-400 group-hover:text-white'}`} />
                    <span className="tracking-tight">{item.label}</span>
                    {isActive && (
                      <span className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-sm" />
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </div>

        {/* Engine Pipeline Features */}
        <div className="space-y-1">
          <p className="px-3 text-[10px] font-mono uppercase tracking-wider text-zinc-500 mb-2">
            Intelligence Engines
          </p>
          {engineModules.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.label}
                className="flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03] transition-colors cursor-default group"
              >
                <div className="flex items-center gap-2.5">
                  <Icon className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-300 transition-colors" />
                  <span className="tracking-tight text-[11px]">{item.label}</span>
                </div>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-white/[0.05] text-zinc-400 border border-white/10 shadow-tactile-sm">
                  {item.badge}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* User Session Footer */}
      {user && (
        <div className="p-3 border-t border-white/10 bg-[#08090F]">
          <div className="tactile-well rounded-xl p-2.5 flex items-center justify-between border border-white/10 shadow-tactile-sm">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-7 h-7 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center text-white font-semibold text-xs shrink-0 shadow-tactile-sm relative before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/25">
                {user.full_name ? user.full_name.charAt(0).toUpperCase() : 'A'}
              </div>
              <div className="truncate min-w-0">
                <p className="text-xs font-semibold text-white truncate leading-tight tracking-tight">{user.full_name || 'Admin User'}</p>
                <span className="inline-flex items-center gap-1 text-[10px] text-zinc-400 capitalize font-mono">
                  <Shield className="w-3 h-3 text-zinc-400" /> {user.role?.toLowerCase() || 'admin'}
                </span>
              </div>
            </div>

            <button
              onClick={logout}
              className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-colors border border-transparent hover:border-white/10 active:translate-y-px"
              title="Sign out"
              aria-label="Logout"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </aside>
  );
};
