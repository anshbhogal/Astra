import React, { useState } from 'react';
import {
  Bug,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  ChevronRight,
  GitCommit,
  Layers,
  Search,
  Filter,
  X,
  Cpu,
} from 'lucide-react';

export interface GroundTruthBugItem {
  bug_id: string;
  service: string;
  endpoint: string;
  http_method: string;
  category: string;
  description: string;
  expected_status: number;
  buggy_status: number;
  trigger_condition: string;
  introduced_in_commit?: string;
  expected_behavior?: string;
  actual_buggy_behavior?: string;
  is_control?: boolean;
}

interface BenchmarkBugGridProps {
  bugs: GroundTruthBugItem[];
  detectedBugIds?: string[];
}

export const BenchmarkBugGrid: React.FC<BenchmarkBugGridProps> = ({
  bugs,
  detectedBugIds = [],
}) => {
  const [selectedService, setSelectedService] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeBug, setActiveBug] = useState<GroundTruthBugItem | null>(null);

  const services = ['ALL', 'auth_service', 'ecommerce_service', 'student_service', 'banking_service', 'CONTROLS'];

  const filteredBugs = bugs.filter((b) => {
    if (selectedService === 'CONTROLS' && !b.is_control) return false;
    if (selectedService !== 'ALL' && selectedService !== 'CONTROLS' && b.service !== selectedService) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        b.bug_id.toLowerCase().includes(q) ||
        b.endpoint.toLowerCase().includes(q) ||
        b.category.toLowerCase().includes(q) ||
        b.description.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case 'BROKEN_AUTHENTICATION':
      case 'AUTHORIZATION_BYPASS':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
      case 'RACE_CONDITION':
      case 'CONCURRENCY_DOUBLE_SPEND':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'DATA_LEAK':
      case 'SENSITIVE_DATA_EXPOSURE':
        return 'text-purple-400 bg-purple-500/10 border-purple-500/20';
      case 'BUSINESS_LOGIC':
      case 'STATE_DESYNC':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
      default:
        return 'text-slate-400 bg-slate-800 border-slate-700';
    }
  };

  return (
    <div className="glass-card rounded-2xl border border-slate-800 p-6 space-y-6 shadow-xl">
      {/* Header & Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Bug className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Benchmark Bug Catalog & Ground Truth Traceability</h3>
            <p className="text-xs text-slate-400">
              50 real injected architectural defects & 100 verified clean negative controls
            </p>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search bug ID, endpoint..."
            className="bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-56"
          />
        </div>
      </div>

      {/* Service Tab Pills */}
      <div className="flex flex-wrap gap-2 text-xs">
        {services.map((svc) => (
          <button
            key={svc}
            onClick={() => setSelectedService(svc)}
            className={`px-3 py-1.5 rounded-xl font-semibold transition-all ${
              selectedService === svc
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/25'
                : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            {svc === 'ALL' ? 'All Items (150)' : svc === 'CONTROLS' ? 'Negative Controls (100)' : svc.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Bugs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 max-h-[500px] overflow-y-auto pr-2">
        {filteredBugs.length === 0 ? (
          <div className="col-span-full text-center py-12 text-slate-500 text-xs">
            No bugs match the current query or filter.
          </div>
        ) : (
          filteredBugs.map((b) => {
            const isDetected = detectedBugIds.includes(b.bug_id);
            const isControl = b.is_control;
            return (
              <div
                key={b.bug_id}
                onClick={() => setActiveBug(b)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer hover:border-indigo-500/60 ${
                  isControl
                    ? 'bg-slate-950/60 border-slate-800/80 hover:bg-slate-900/60'
                    : isDetected
                    ? 'bg-emerald-950/10 border-emerald-500/30 hover:bg-emerald-950/20'
                    : 'bg-slate-900/70 border-slate-800 hover:bg-slate-900'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-xs font-bold text-white flex items-center gap-1.5">
                    {isControl ? (
                      <ShieldCheck className="w-3.5 h-3.5 text-teal-400" />
                    ) : isDetected ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Bug className="w-3.5 h-3.5 text-indigo-400" />
                    )}
                    {b.bug_id}
                  </span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getCategoryColor(b.category)}`}>
                    {b.category.slice(0, 16)}
                  </span>
                </div>

                <p className="text-xs text-slate-300 font-medium line-clamp-2 mb-2.5">
                  {b.description}
                </p>

                <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-2 border-t border-slate-800/60">
                  <span className="truncate max-w-[140px] text-slate-400 font-medium">
                    {b.http_method} {b.endpoint}
                  </span>
                  <span className="text-indigo-400 font-semibold hover:underline flex items-center gap-0.5">
                    Inspect <ChevronRight className="w-3 h-3" />
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* "Why did ASTRA detect this bug?" Traceability Modal */}
      {activeBug && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-6 relative">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  <HelpCircle className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Detection & Attribution Traceability</h3>
                  <p className="text-xs font-mono text-indigo-400">{activeBug.bug_id} • {activeBug.service}</p>
                </div>
              </div>
              <button
                onClick={() => setActiveBug(null)}
                className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-xl transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* 3-State Detection Lifecycle Banner */}
            <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl space-y-3">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">
                ASTRA 3-State Ground-Truth Pipeline
              </span>
              <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                <div className="p-2.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-center">
                  <span className="text-[10px] text-indigo-400 block font-bold">STAGE 1</span>
                  <span className="text-white font-bold">1. TRIGGERED</span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">Payload executed</span>
                </div>
                <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-center">
                  <span className="text-[10px] text-emerald-400 block font-bold">STAGE 2</span>
                  <span className="text-white font-bold">2. DETECTED</span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">Assertion failed</span>
                </div>
                <div className="p-2.5 rounded-lg bg-teal-500/10 border border-teal-500/20 text-center">
                  <span className="text-[10px] text-teal-400 block font-bold">STAGE 3</span>
                  <span className="text-white font-bold">3. ATTRIBUTED</span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">Root cause mapped</span>
                </div>
              </div>
            </div>

            {/* In-depth details */}
            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Target Endpoint</span>
                  <span className="text-white font-mono font-bold">{activeBug.http_method} {activeBug.endpoint}</span>
                </div>
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Status Assertion</span>
                  <span className="text-slate-300 font-mono">
                    Expected <span className="text-emerald-400 font-bold">{activeBug.expected_status}</span> vs Buggy <span className="text-rose-400 font-bold">{activeBug.buggy_status}</span>
                  </span>
                </div>
              </div>

              <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Trigger Payload / Precondition</span>
                <p className="text-slate-300 font-mono text-[11px] leading-relaxed">{activeBug.trigger_condition}</p>
              </div>

              {activeBug.introduced_in_commit && (
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl flex items-center justify-between font-mono">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <GitCommit className="w-3.5 h-3.5 text-indigo-400" /> Git Fixture Commit
                  </span>
                  <span className="text-indigo-300 font-bold">{activeBug.introduced_in_commit}</span>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setActiveBug(null)}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition-colors"
              >
                Close Traceability Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
