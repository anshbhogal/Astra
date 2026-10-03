import React, { useEffect, useState } from 'react';
import { Database, Server, RefreshCw } from 'lucide-react';
import { api } from '../../services/api';

export const Navbar: React.FC = () => {
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
    <header className="h-16 glass-panel border-b border-slate-800 px-6 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-semibold text-slate-300">Phase 1 — Core Foundation & Infrastructure</h2>
      </div>

      {/* Dependency Health Status Indicators */}
      <div className="flex items-center gap-4 text-xs font-mono">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">
          <Database className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">PostgreSQL:</span>
          <span className={dbReady ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
            {dbReady === null ? '...' : dbReady ? 'ONLINE' : 'OFFLINE'}
          </span>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">
          <Server className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">Redis:</span>
          <span className={redisReady ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
            {redisReady === null ? '...' : redisReady ? 'ONLINE' : 'OFFLINE'}
          </span>
        </div>

        <button
          onClick={checkHealth}
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          title="Refresh readiness check"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
        </button>
      </div>
    </header>
  );
};
