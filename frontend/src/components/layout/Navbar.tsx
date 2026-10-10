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
    <header className="h-16 bg-sidebar border-b border-black/20 px-6 flex items-center justify-between shrink-0 select-none z-10 transition-colors duration-150">
      {/* Left: Quick Search / Command Launcher */}
      <div className="flex items-center gap-4 min-w-0">
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-2.5 px-3.5 py-2 rounded-lg bg-white/10 hover:bg-white/15 border border-white/15 text-xs text-white/90 hover:text-white transition-all shadow-sm group"
          title="Open Command Palette (Ctrl+K, ⌘K, or click)"
        >
          <Search className="w-4 h-4 text-white/70 group-hover:text-white transition-colors" />
          <span className="hidden sm:inline font-medium">Quick search or command...</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-white/15 border border-white/20 text-[10px] font-mono text-white/80">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right: Telemetry & Theme Switcher */}
      <div className="flex items-center gap-3">
        {/* System Health Indicators */}
        <div className="hidden md:flex items-center gap-2 text-xs font-sans">
          {/* PostgreSQL Status */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/10 border border-white/15">
            <Database className="w-3.5 h-3.5 text-white/80" />
            <span className="text-white/70 text-xs font-medium">Postgres:</span>
            {dbReady ? (
              <span className="flex items-center gap-1 font-semibold text-emerald-300">
                <CheckCircle2 className="w-3.5 h-3.5" /> Healthy
              </span>
            ) : dbReady === false ? (
              <span className="flex items-center gap-1 font-semibold text-rose-300">
                <XCircle className="w-3.5 h-3.5" /> Offline
              </span>
            ) : (
              <span className="text-white/60">Checking...</span>
            )}
          </div>

          {/* Redis Status */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/10 border border-white/15">
            <Server className="w-3.5 h-3.5 text-white/80" />
            <span className="text-white/70 text-xs font-medium">Redis:</span>
            {redisReady ? (
              <span className="flex items-center gap-1 font-semibold text-emerald-300">
                <CheckCircle2 className="w-3.5 h-3.5" /> Healthy
              </span>
            ) : redisReady === false ? (
              <span className="flex items-center gap-1 font-semibold text-rose-300">
                <XCircle className="w-3.5 h-3.5" /> Offline
              </span>
            ) : (
              <span className="text-white/60">Checking...</span>
            )}
          </div>

          {/* Refresh Ping */}
          <button
            onClick={checkHealth}
            disabled={checking}
            className="p-1.5 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
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
