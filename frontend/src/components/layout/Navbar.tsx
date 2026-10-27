import React, { useEffect, useState } from 'react';
import {
  Database,
  Server,
  RefreshCw,
  Search,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { api } from '../../services/api';
import { ThemeToggle } from '../common/ThemeToggle';

interface NavbarProps {
  onOpenCommandPalette?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenCommandPalette }) => {
  const [dbReady, setDbReady] = useState<boolean | null>(null);
  const [redisReady, setRedisReady] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(false);

  const checkHealth = async () => {
    setChecking(true);
    try {
      const res = await api.get('/health/ready');
      setDbReady(res.data.dependencies.database === 'online');
      setRedisReady(res.data.dependencies.redis === 'online');
    } catch (e) {
      setDbReady(false);
      setRedisReady(false);
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 glass-restrained border-b border-border-card/70 dark:border-white/10 px-6 flex items-center justify-between shrink-0 select-none z-10 shadow-tactile-sm transition-colors duration-150 relative before:absolute before:inset-x-0 before:bottom-0 before:h-px before:bg-white/10">
      {/* Left: Quick Search / Command Launcher */}
      <div className="flex items-center gap-4 min-w-0">
        <button
          onClick={onOpenCommandPalette}
          className="tactile-well flex items-center gap-2.5 px-3.5 py-1.5 rounded-lg border border-border-card/80 dark:border-white/10 text-xs text-secondary hover:text-primary dark:text-zinc-300 dark:hover:text-white transition-all shadow-tactile-sm hover:border-zinc-400/50 dark:hover:border-white/20 active:translate-y-px group"
          title="Open Command Palette (Ctrl+K, ⌘K, or click)"
        >
          <Search className="w-3.5 h-3.5 text-muted group-hover:text-primary dark:text-zinc-400 dark:group-hover:text-white transition-colors" />
          <span className="hidden sm:inline font-medium tracking-tight">Quick search or command...</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-surface dark:bg-white/10 border border-border-card dark:border-white/15 text-[10px] font-mono text-muted dark:text-zinc-300 shadow-tactile-sm">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right: Telemetry & Theme Switcher */}
      <div className="flex items-center gap-3">
        {/* System Health Indicators */}
        <div className="hidden md:flex items-center gap-2 text-xs font-sans">
          {/* PostgreSQL Status */}
          <div className="tactile-card flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-border-card/70 dark:border-white/10 text-secondary dark:text-zinc-300 shadow-tactile-sm relative before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/15">
            <Database className="w-3.5 h-3.5 text-muted dark:text-zinc-400" />
            <span className="text-secondary dark:text-zinc-400 text-xs font-medium">Postgres:</span>
            {dbReady ? (
              <span className="flex items-center gap-1 font-semibold text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="w-3.5 h-3.5" /> Healthy
              </span>
            ) : dbReady === false ? (
              <span className="flex items-center gap-1 font-semibold text-rose-600 dark:text-rose-400">
                <XCircle className="w-3.5 h-3.5" /> Offline
              </span>
            ) : (
              <span className="text-muted dark:text-zinc-500">Checking...</span>
            )}
          </div>

          {/* Redis Status */}
          <div className="tactile-card flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-border-card/70 dark:border-white/10 text-secondary dark:text-zinc-300 shadow-tactile-sm relative before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/15">
            <Server className="w-3.5 h-3.5 text-muted dark:text-zinc-400" />
            <span className="text-secondary dark:text-zinc-400 text-xs font-medium">Redis:</span>
            {redisReady ? (
              <span className="flex items-center gap-1 font-semibold text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="w-3.5 h-3.5" /> Healthy
              </span>
            ) : redisReady === false ? (
              <span className="flex items-center gap-1 font-semibold text-rose-600 dark:text-rose-400">
                <XCircle className="w-3.5 h-3.5" /> Offline
              </span>
            ) : (
              <span className="text-muted dark:text-zinc-500">Checking...</span>
            )}
          </div>

          {/* Refresh Ping */}
          <button
            onClick={checkHealth}
            disabled={checking}
            className="p-1.5 text-secondary hover:text-primary hover:bg-surface-elevated dark:text-zinc-400 dark:hover:text-white dark:hover:bg-white/10 rounded-lg border border-transparent hover:border-border-card/50 dark:hover:border-white/10 shadow-tactile-sm active:translate-y-px transition-all"
            title="Refresh health status"
            aria-label="Refresh status"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Theme Toggle Button */}
        <ThemeToggle />
      </div>
    </header>
  );
};
