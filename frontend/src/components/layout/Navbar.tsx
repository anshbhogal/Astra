import React, { useEffect, useState } from 'react';
import {
  Database,
  Server,
  RefreshCw,
  Search,
  Command,
  Sun,
  Moon,
  Activity,
  CheckCircle2,
  XCircle,
  Radio
} from 'lucide-react';
import { api } from '../../services/api';
import { useThemeStore } from '../../store/themeStore';

interface NavbarProps {
  onOpenCommandPalette?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenCommandPalette }) => {
  const [dbReady, setDbReady] = useState<boolean | null>(null);
  const [redisReady, setRedisReady] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(false);
  const { theme, toggleTheme } = useThemeStore();

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
    <header className="h-16 bg-surface border-b border-border px-6 flex items-center justify-between shrink-0 select-none z-10">
      {/* Left: Mission Console Title & Command Search Bar */}
      <div className="flex items-center gap-4 min-w-0">
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-raised border border-border text-xs text-muted hover:text-primary hover:border-brand/40 transition-all shadow-sm group"
          title="Open Command Palette (Ctrl+K or ⌘K)"
        >
          <Search className="w-3.5 h-3.5 text-muted group-hover:text-brand transition-colors" />
          <span className="hidden sm:inline font-medium">Quick search or command...</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-surface border border-border text-[10px] font-mono text-muted group-hover:border-brand/30">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right: Mission Control Telemetry Strip & Theme Toggle */}
      <div className="flex items-center gap-3 text-xs font-mono">
        {/* System Health Indicators */}
        <div className="hidden md:flex items-center gap-2">
          {/* PostgreSQL Status */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-raised border border-border">
            <Database className="w-3.5 h-3.5 text-secondary" />
            <span className="text-muted text-[11px]">DB</span>
            {dbReady ? (
              <span className="flex items-center gap-1 text-[11px] font-bold text-status-passed">
                <CheckCircle2 className="w-3 h-3 text-status-passed" /> ONLINE
              </span>
            ) : dbReady === false ? (
              <span className="flex items-center gap-1 text-[11px] font-bold text-status-failed">
                <XCircle className="w-3 h-3 text-status-failed" /> OFFLINE
              </span>
            ) : (
              <span className="text-[11px] text-muted">...</span>
            )}
          </div>

          {/* Redis Status */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-raised border border-border">
            <Server className="w-3.5 h-3.5 text-secondary" />
            <span className="text-muted text-[11px]">REDIS</span>
            {redisReady ? (
              <span className="flex items-center gap-1 text-[11px] font-bold text-status-passed">
                <CheckCircle2 className="w-3 h-3 text-status-passed" /> READY
              </span>
            ) : redisReady === false ? (
              <span className="flex items-center gap-1 text-[11px] font-bold text-status-failed">
                <XCircle className="w-3 h-3 text-status-failed" /> OFFLINE
              </span>
            ) : (
              <span className="text-[11px] text-muted">...</span>
            )}
          </div>

          {/* Refresh Ping */}
          <button
            onClick={checkHealth}
            disabled={checking}
            className="p-1.5 text-muted hover:text-primary hover:bg-raised rounded-lg transition-colors border border-transparent hover:border-border"
            title="Refresh system telemetry"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Theme Toggle Button (Voltage Dark <-> Polished Light) */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-xl bg-raised border border-border text-secondary hover:text-primary transition-all hover:border-brand/40 shadow-sm"
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} mode`}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-brand" />
          )}
        </button>
      </div>
    </header>
  );
};
