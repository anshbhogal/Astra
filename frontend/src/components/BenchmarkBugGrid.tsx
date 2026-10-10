import React, { useState } from 'react';
import {
  Bug,
  ShieldCheck,
  CheckCircle2,
  HelpCircle,
  ChevronRight,
  GitCommit,
  Search,
  X,
} from 'lucide-react';
import { Button } from './common/Button';

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
        return 'text-status-failed bg-status-failed-bg border-status-failed/30';
      case 'RACE_CONDITION':
      case 'CONCURRENCY_DOUBLE_SPEND':
        return 'text-status-flaky bg-status-flaky-bg border-status-flaky/30';
      case 'DATA_LEAK':
      case 'SENSITIVE_DATA_EXPOSURE':
        return 'text-brand bg-brand/10 border-brand/30';
      case 'BUSINESS_LOGIC':
      case 'STATE_DESYNC':
        return 'text-secondaryAccent bg-secondaryAccent/10 border-secondaryAccent/30';
      default:
        return 'text-secondary bg-field border-border-card';
    }
  };

  return (
    <div className="bg-card rounded-2xl border border-border-card p-6 space-y-6 shadow-card">
      {/* Header & Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-card pb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-brand/10 text-brand border border-brand/20 flex items-center justify-center">
            <Bug className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-primary">Benchmark Bug Catalog & Ground Truth Traceability</h3>
            <p className="text-xs text-secondary">
              50 real injected architectural defects & 100 verified clean negative controls
            </p>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="w-4 h-4 text-muted absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search bug ID, endpoint..."
            className="bg-field border border-border-field rounded-xl pl-9 pr-3 py-1.5 text-xs text-primary placeholder-muted focus:outline-none focus:ring-2 focus:ring-brand w-56"
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
                ? 'bg-brand text-on-brand shadow-sm'
                : 'bg-field border border-border-card text-secondary hover:text-primary hover:border-brand'
            }`}
          >
            {svc === 'ALL' ? 'All Items (150)' : svc === 'CONTROLS' ? 'Negative Controls (100)' : svc.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Bugs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 max-h-[500px] overflow-y-auto pr-2">
        {filteredBugs.length === 0 ? (
          <div className="col-span-full text-center py-12 text-muted text-xs">
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
                className={`p-3.5 rounded-xl border transition-all cursor-pointer hover:border-brand ${
                  isControl
                    ? 'bg-field border-border-card hover:bg-hover'
                    : isDetected
                    ? 'bg-status-passed-bg/40 border-status-passed/30 hover:bg-status-passed-bg/60'
                    : 'bg-card border-border-card hover:bg-hover'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-xs font-bold text-primary flex items-center gap-1.5">
                    {isControl ? (
                      <ShieldCheck className="w-3.5 h-3.5 text-secondaryAccent" />
                    ) : isDetected ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-status-passed" />
                    ) : (
                      <Bug className="w-3.5 h-3.5 text-brand" />
                    )}
                    {b.bug_id}
                  </span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getCategoryColor(b.category)}`}>
                    {b.category.slice(0, 16)}
                  </span>
                </div>

                <p className="text-xs text-secondary font-medium line-clamp-2 mb-2.5">
                  {b.description}
                </p>

                <div className="flex items-center justify-between text-[11px] font-mono text-muted pt-2 border-t border-border-card">
                  <span className="truncate max-w-[140px] text-secondary font-medium">
                    {b.http_method} {b.endpoint}
                  </span>
                  <span className="text-brand font-semibold hover:underline flex items-center gap-0.5">
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
        <div className="fixed inset-0 z-50 bg-slate-950/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border-card rounded-2xl max-w-2xl w-full p-6 shadow-card space-y-6 relative">
            <div className="flex items-center justify-between border-b border-border-card pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-brand/10 text-brand border border-brand/20">
                  <HelpCircle className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-primary">Detection & Attribution Traceability</h3>
                  <p className="text-xs font-mono text-brand font-semibold">{activeBug.bug_id} • {activeBug.service}</p>
                </div>
              </div>
              <button
                onClick={() => setActiveBug(null)}
                className="p-2 text-secondary hover:text-primary hover:bg-hover rounded-xl transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* 3-State Detection Lifecycle Banner */}
            <div className="p-4 bg-field border border-border-card rounded-xl space-y-3">
              <span className="text-[10px] uppercase font-bold text-muted tracking-wider block">
                ASTRA 3-State Ground-Truth Pipeline
              </span>
              <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                <div className="p-2.5 rounded-lg bg-brand/10 border border-brand/20 text-center">
                  <span className="text-[10px] text-brand block font-bold">STAGE 1</span>
                  <span className="text-primary font-bold">1. TRIGGERED</span>
                  <span className="text-[10px] text-muted block mt-0.5">Payload executed</span>
                </div>
                <div className="p-2.5 rounded-lg bg-status-passed-bg border border-status-passed/30 text-center">
                  <span className="text-[10px] text-status-passed block font-bold">STAGE 2</span>
                  <span className="text-status-passed font-bold">2. DETECTED</span>
                  <span className="text-[10px] text-muted block mt-0.5">Assertion failed</span>
                </div>
                <div className="p-2.5 rounded-lg bg-secondaryAccent/10 border border-secondaryAccent/20 text-center">
                  <span className="text-[10px] text-secondaryAccent block font-bold">STAGE 3</span>
                  <span className="text-secondaryAccent font-bold">3. ATTRIBUTED</span>
                  <span className="text-[10px] text-muted block mt-0.5">Root cause mapped</span>
                </div>
              </div>
            </div>

            {/* In-depth details */}
            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-field border border-border-card rounded-xl space-y-1">
                  <span className="text-[10px] uppercase font-bold text-muted block">Target Endpoint</span>
                  <span className="text-primary font-mono font-bold">{activeBug.http_method} {activeBug.endpoint}</span>
                </div>
                <div className="p-3 bg-field border border-border-card rounded-xl space-y-1">
                  <span className="text-[10px] uppercase font-bold text-muted block">Status Assertion</span>
                  <span className="text-secondary font-mono">
                    Expected <span className="text-status-passed font-bold">{activeBug.expected_status}</span> vs Buggy <span className="text-status-failed font-bold">{activeBug.buggy_status}</span>
                  </span>
                </div>
              </div>

              <div className="p-3 bg-field border border-border-card rounded-xl space-y-1">
                <span className="text-[10px] uppercase font-bold text-muted block">Trigger Payload / Precondition</span>
                <p className="text-secondary font-mono text-[11px] leading-relaxed">{activeBug.trigger_condition}</p>
              </div>

              {activeBug.introduced_in_commit && (
                <div className="p-3 bg-field border border-border-card rounded-xl flex items-center justify-between font-mono">
                  <span className="text-muted flex items-center gap-1.5">
                    <GitCommit className="w-3.5 h-3.5 text-brand" /> Git Fixture Commit
                  </span>
                  <span className="text-brand font-bold">{activeBug.introduced_in_commit}</span>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <Button
                variant="secondary"
                onClick={() => setActiveBug(null)}
              >
                Close Traceability Inspector
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
