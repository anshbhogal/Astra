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
    <header className="h-16 bg-card/90 dark:bg-sidebar border-b border-border-card dark:border-white/10 px-6 flex items-center justify-between shrink-0 select-none z-10 shadow-sm backdrop-blur-md transition-colors duration-150">
      {/* Left: Quick Search / Command Launcher */}
      <div className="flex items-center gap-4 min-w-0">
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-2.5 px-3.5 py-2 rounded-lg bg-field hover:bg-hover border border-border-field/70 dark:bg-white/10 dark:hover:bg-white/15 dark:border-white/15 text-xs text-secondary hover:text-primary dark:text-white/90 dark:hover:text-white transition-all shadow-sm group"
          title="Open Command Palette (Ctrl+K, ⌘K, or click)"
        >
          <Search className="w-4 h-4 text-muted group-hover:text-primary dark:text-white/70 dark:group-hover:text-white transition-colors" />
          <span className="hidden sm:inline font-medium">Quick search or command...</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-card dark:bg-white/15 border border-border-card dark:border-white/20 text-[10px] font-mono text-muted dark:text-white/80">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right: Telemetry & Theme Switcher */}
      <div className="flex items-center gap-3">
        {/* System Health Indicators */}
        <div className="hidden md:flex items-center gap-2 text-xs font-sans">
          {/* PostgreSQL Status */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-field dark:bg-white/10 border border-border-card dark:border-white/15 text-secondary dark:text-white/80">
            <Database className="w-3.5 h-3.5 text-muted dark:text-white/80" />
            <span className="text-secondary dark:text-white/70 text-xs font-medium">Postgres:</span>
            {dbReady ? (
              <span className="flex items-center gap-1 font-semibold text-emerald-700 dark:text-emerald-300">
                <CheckCircle2 className="w-3.5 h-3.5" /> Healthy
              </span>
            ) : dbReady === false ? (
              <span className="flex items-center gap-1 font-semibold text-rose-700 dark:text-rose-300">
                <XCircle className="w-3.5 h-3.5" /> Offline
              </span>
            ) : (
              <span className="text-muted dark:text-white/60">Checking...</span>
            )}
          </div>

          {/* Redis Status */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-field dark:bg-white/10 border border-border-card dark:border-white/15 text-secondary dark:text-white/80">
            <Server className="w-3.5 h-3.5 text-muted dark:text-white/80" />
            <span className="text-secondary dark:text-white/70 text-xs font-medium">Redis:</span>
            {redisReady ? (
              <span className="flex items-center gap-1 font-semibold text-emerald-700 dark:text-emerald-300">
                <CheckCircle2 className="w-3.5 h-3.5" /> Healthy
              </span>
            ) : redisReady === false ? (
              <span className="flex items-center gap-1 font-semibold text-rose-700 dark:text-rose-300">
                <XCircle className="w-3.5 h-3.5" /> Offline
              </span>
            ) : (
              <span className="text-muted dark:text-white/60">Checking...</span>
            )}
          </div>

          {/* Refresh Ping */}
          <button
            onClick={checkHealth}
            disabled={checking}
            className="p-1.5 text-secondary hover:text-primary hover:bg-hover dark:text-white/70 dark:hover:text-white dark:hover:bg-white/10 rounded-lg transition-colors"
            title="Refresh health status"
            aria-label="Refresh status"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Section 6 Theme Toggle Button (36px, Sun in dark mode, Moon in light mode) */}
        <ThemeToggle />
      </div>
    </header>
  );
};
