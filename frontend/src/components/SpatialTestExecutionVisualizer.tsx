import React, { useState, useRef, useMemo } from 'react';
import {
  Layers,
  Box,
  Cpu,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Eye,
  Activity,
  Maximize2,
  Minimize2,
  Sparkles,
  Zap,
  Clock,
  Compass,
} from 'lucide-react';
import { TestStatusBadge } from './common/TestStatusBadge';

export interface CurrentTestMeta {
  index: number;
  total: number;
  name: string;
  method: string;
  path: string;
}

export interface TestRunVisualizerData {
  id: string;
  status: string;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  error_tests: number;
  duration_ms: number;
  target_environment?: {
    base_url?: string;
    environment_type?: string;
    current_test?: CurrentTestMeta;
  };
}

export interface VisualizerTestResult {
  id: string;
  endpoint: string;
  method: string;
  test_type: string;
  outcome: 'PASS' | 'FAIL' | 'ERROR' | 'TIMEOUT' | 'SKIP';
  status_code: number | null;
  execution_time_ms: number;
  assertion_failures?: Array<{ type: string; message: string }>;
}

interface SpatialTestExecutionVisualizerProps {
  testRun: TestRunVisualizerData;
  results: VisualizerTestResult[];
  onSelectResult?: (id: string) => void;
  selectedResultId?: string | null;
}

export const SpatialTestExecutionVisualizer: React.FC<SpatialTestExecutionVisualizerProps> = ({
  testRun,
  results,
  onSelectResult,
  selectedResultId,
}) => {
  const [is3D, setIs3D] = useState(true);
  const [activeStage, setActiveStage] = useState<number | null>(null);
  const [hoveredNode, setHoveredNode] = useState<VisualizerTestResult | null>(null);
  const [tilt, setTilt] = useState({ x: 18, y: -4 });
  const containerRef = useRef<HTMLDivElement>(null);

  const isRunning =
    testRun.status === 'RUNNING' || testRun.status === 'STARTING' || testRun.status === 'PENDING';

  const currentTest = testRun.target_environment?.current_test;
  const totalSteps =
    testRun.total_tests || currentTest?.total || (results.length > 0 ? results.length : 1);
  const completedSteps =
    (testRun.passed_tests || 0) + (testRun.failed_tests || 0) + (testRun.error_tests || 0);
  const progressPercent = totalSteps > 0 ? Math.min(100, Math.round((completedSteps / totalSteps) * 100)) : 0;

  // Mouse interactive tilt handler for subtle spatial parallax
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!is3D || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    const rotX = Math.max(8, Math.min(26, 18 - (y / rect.height) * 12));
    const rotY = Math.max(-12, Math.min(8, -4 + (x / rect.width) * 14));
    setTilt({ x: rotX, y: rotY });
  };

  const handleMouseLeave = () => {
    setTilt({ x: 18, y: -4 });
  };

  // Up to 24 sample nodes displayed on the 3D execution plane
  const displayNodes = useMemo(() => {
    if (results.length > 0) {
      return results.slice(0, 24);
    }
    // If no executed results yet, generate placeholders based on totalSteps
    const count = Math.min(totalSteps || 12, 18);
    return Array.from({ length: count }, (_, i) => ({
      id: `pending-${i}`,
      endpoint: currentTest && i === 0 ? currentTest.path : `/api/v1/resource/${i + 1}`,
      method: currentTest && i === 0 ? currentTest.method : 'GET',
      test_type: 'contract',
      outcome: (i === 0 && isRunning ? 'RUNNING' : 'SKIP') as any,
      status_code: null,
      execution_time_ms: 0,
    }));
  }, [results, totalSteps, isRunning, currentTest]);

  // Stage execution telemetry definitions
  const stages = [
    {
      id: 1,
      title: 'Contract Blueprint',
      subtitle: 'OpenAPI Spec & Seed',
      icon: Cpu,
      status: 'COMPLETED',
      metric: '100% Validated',
    },
    {
      id: 2,
      title: 'Sandbox Dispatch',
      subtitle: 'SSRF Guard & Isolation',
      icon: ShieldCheck,
      status: isRunning || completedSteps > 0 ? 'ACTIVE' : 'READY',
      metric: testRun.target_environment?.base_url ? 'Container Healthy' : 'Isolated Network',
    },
    {
      id: 3,
      title: 'Execution Matrix',
      subtitle: 'Fuzzing & Assertions',
      icon: Activity,
      status: isRunning ? 'STREAMING' : completedSteps > 0 ? 'RESOLVED' : 'QUEUED',
      metric: `${completedSteps} / ${totalSteps} Complete`,
    },
    {
      id: 4,
      title: 'Telemetry Basin',
      subtitle: 'SLA & Invariant Guard',
      icon: Layers,
      status: completedSteps > 0 ? 'RECORDING' : 'STANDBY',
      metric: `${Number(testRun.duration_ms || 0).toFixed(0)} ms latency`,
    },
  ];

  return (
    <div className="glass-restrained p-5 border border-border-card shadow-tactile rounded-2xl space-y-4 overflow-hidden relative select-none">
      {/* Top Header & Perspective Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-card/60 pb-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand/10 border border-brand/20 flex items-center justify-center text-brand shadow-tactile-sm">
            <Compass className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-primary tracking-tight">
                Spatial Execution Pipeline
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-brand/10 text-brand border border-brand/20 shadow-tactile-sm">
                3D Orthographic
              </span>
            </div>
            <p className="text-[11px] text-muted tracking-tight">
              Hardware-grade multi-plane telemetry of sandbox runner state and test conduits
            </p>
          </div>
        </div>

        {/* View Mode Toggle: Spatial 3D vs Planar Minimalist */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <div className="p-1 tactile-well flex items-center gap-1 text-xs">
            <button
              type="button"
              onClick={() => setIs3D(true)}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all font-semibold ${
                is3D
                  ? 'bg-brand text-on-brand shadow-tactile-sm'
                  : 'text-secondary hover:text-primary'
              }`}
            >
              <Box className="w-3.5 h-3.5" />
              <span>Spatial 3D</span>
            </button>
            <button
              type="button"
              onClick={() => setIs3D(false)}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all font-semibold ${
                !is3D
                  ? 'bg-brand text-on-brand shadow-tactile-sm'
                  : 'text-secondary hover:text-primary'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Flat Minimal</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Spatial Stage Canvas */}
      <div
        ref={containerRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className="perspective-spatial relative min-h-[320px] rounded-xl tactile-well p-4 sm:p-6 overflow-hidden flex items-center justify-center border border-border-card/80 transition-all duration-300"
        style={{
          background:
            'radial-gradient(circle at 50% 30%, rgba(91, 61, 245, 0.05) 0%, rgba(11, 12, 20, 0.95) 75%)',
        }}
      >
        {/* Subtle Ambient Circuit Etch Grid */}
        <div
          className="absolute inset-0 opacity-15 pointer-events-none"
          style={{
            backgroundImage:
              'linear-gradient(to right, rgba(255, 255, 255, 0.1) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.1) 1px, transparent 1px)',
            backgroundSize: '32px 32px',
          }}
        />

        {/* 3D Tilted Plane vs Flat Planar Mode */}
        <div
          className={`w-full max-w-4xl transition-all duration-500 ease-out preserve-3d ${
            is3D ? 'spatial-board-3d' : 'spatial-board-flat'
          }`}
          style={
            is3D
              ? {
                  transform: `rotateX(${tilt.x}deg) rotateZ(${tilt.y}deg) translateY(-8px)`,
                }
              : {}
          }
        >
          {/* Plane 1: 4 Stage Pipeline Modules */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 relative preserve-3d mb-6">
            {stages.map((stg) => {
              const Icon = stg.icon;
              const isSelected = activeStage === stg.id;
              const isActive = stg.status === 'ACTIVE' || stg.status === 'STREAMING';

              return (
                <div
                  key={stg.id}
                  onClick={() => setActiveStage(isSelected ? null : stg.id)}
                  className={`group relative p-3.5 rounded-xl border transition-all duration-300 cursor-pointer ${
                    is3D ? 'spatial-elevation-1 hover:spatial-elevation-active' : ''
                  } ${
                    isSelected
                      ? 'bg-brand/25 border-brand ring-1 ring-brand/50'
                      : isActive
                      ? 'bg-zinc-900/90 border-brand/50 shadow-tactile'
                      : 'bg-zinc-900/70 border-white/10 hover:border-brand/40 shadow-tactile-sm'
                  }`}
                >
                  {/* Top Specular Line */}
                  <div className="absolute inset-x-2 top-0 h-px bg-white/20 rounded-t-xl" />

                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-bold">
                      Stage 0{stg.id}
                    </span>
                    <div
                      className={`w-6 h-6 rounded-md flex items-center justify-center ${
                        isActive
                          ? 'bg-brand/20 text-brand border border-brand/30'
                          : 'bg-zinc-800/80 text-zinc-400 border border-white/10'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                  </div>

                  <h4 className="text-xs font-bold text-white tracking-tight">{stg.title}</h4>
                  <p className="text-[10px] text-zinc-400 truncate">{stg.subtitle}</p>

                  <div className="mt-2.5 pt-2 border-t border-white/10 flex items-center justify-between text-[10px]">
                    <span className="text-zinc-300 font-mono">{stg.metric}</span>
                    <span
                      className={`tactile-led ${
                        isActive
                          ? 'text-brand animate-pulse'
                          : stg.status === 'COMPLETED' || stg.status === 'RESOLVED'
                          ? 'text-status-passed'
                          : 'text-zinc-500'
                      }`}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Glowing Animated Conduit Track between Stage Modules */}
          <div className="relative h-2 rounded-full tactile-well my-4 overflow-hidden border border-white/10 shadow-inner">
            <div
              className={`h-full transition-all duration-500 rounded-full ${
                isRunning
                  ? 'spatial-conduit-active bg-gradient-to-r from-brand via-secondary to-brand'
                  : 'bg-gradient-to-r from-brand via-status-passed to-emerald-400'
              }`}
              style={{ width: `${Math.max(isRunning ? 8 : 0, progressPercent)}%` }}
            />
          </div>

          {/* Plane 2: Floating 3D Test Node Matrix */}
          <div className="p-4 rounded-xl bg-zinc-950/85 border border-white/10 shadow-tactile preserve-3d">
            <div className="flex items-center justify-between mb-3 text-xs">
              <div className="flex items-center gap-2">
                <span className="tactile-led text-brand" />
                <span className="font-bold text-zinc-200 text-[11px] uppercase tracking-wider">
                  Live Test Matrix Plane
                </span>
                <span className="text-[10px] text-zinc-400 font-mono">
                  ({displayNodes.length} active nodes)
                </span>
              </div>
              <div className="flex items-center gap-3 text-[10px] font-mono text-zinc-400">
                <span className="flex items-center gap-1 text-emerald-400 font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" /> Passed
                </span>
                <span className="flex items-center gap-1 text-rose-400 font-medium">
                  <span className="w-2 h-2 rounded-full bg-rose-400" /> Failed
                </span>
                <span className="flex items-center gap-1 text-sky-400 font-medium">
                  <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping" /> Running
                </span>
              </div>
            </div>

            {/* Matrix of floating test cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2.5 preserve-3d">
              {displayNodes.map((node, idx) => {
                const isNodeRunning = node.outcome === 'RUNNING';
                const isNodePassed = node.outcome === 'PASS';
                const isNodeFailed = node.outcome === 'FAIL' || node.outcome === 'ERROR';
                const isSelected = selectedResultId === node.id;

                return (
                  <div
                    key={node.id}
                    onMouseEnter={() => setHoveredNode(node)}
                    onMouseLeave={() => setHoveredNode(null)}
                    onClick={() => onSelectResult && onSelectResult(node.id)}
                    className={`relative p-2.5 rounded-lg border transition-all duration-200 cursor-pointer ${
                      is3D
                        ? isNodeRunning
                          ? 'spatial-elevation-active'
                          : isSelected
                          ? 'spatial-elevation-2 ring-2 ring-brand'
                          : 'spatial-elevation-1 hover:spatial-elevation-2'
                        : ''
                    } ${
                      isNodeRunning
                        ? 'bg-brand/10 border-brand/60 shadow-tactile'
                        : isNodePassed
                        ? 'bg-card border-status-passed/30 hover:border-status-passed/60 shadow-tactile-sm'
                        : isNodeFailed
                        ? 'bg-card border-status-failed/35 hover:border-status-failed/70 shadow-tactile-sm'
                        : 'bg-card/60 border-border-card/60 shadow-tactile-sm opacity-60'
                    }`}
                  >
                    {/* Top specular highlight line */}
                    <div className="absolute inset-x-1.5 top-0 h-px bg-white/20 rounded-t" />

                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-[9px] font-bold text-brand uppercase">
                        {node.method}
                      </span>
                      {isNodeRunning ? (
                        <Loader2 className="w-2.5 h-2.5 animate-spin text-brand" />
                      ) : isNodePassed ? (
                        <CheckCircle2 className="w-2.5 h-2.5 text-status-passed" />
                      ) : isNodeFailed ? (
                        <XCircle className="w-2.5 h-2.5 text-status-failed" />
                      ) : (
                        <span className="w-1.5 h-1.5 rounded-full bg-border-field" />
                      )}
                    </div>

                    <div className="text-[10px] font-mono text-primary truncate font-medium">
                      {node.endpoint.replace('/api/v1', '') || '/'}
                    </div>

                    <div className="mt-1 flex items-center justify-between text-[9px] text-muted font-mono">
                      <span>{node.status_code || '---'}</span>
                      <span>{node.execution_time_ms ? `${node.execution_time_ms}ms` : '--'}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Hover Telemetry HUD Overlay */}
        {hoveredNode && (
          <div className="absolute bottom-3 right-3 max-w-xs p-3 rounded-xl glass-restrained border border-border-card shadow-tactile pointer-events-none z-30 space-y-1 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between gap-2 text-xs">
              <span className="font-mono font-bold text-brand">{hoveredNode.method}</span>
              <span className="text-[10px] font-mono text-muted">
                {hoveredNode.execution_time_ms} ms
              </span>
            </div>
            <p className="text-[11px] font-mono text-primary font-semibold truncate">
              {hoveredNode.endpoint}
            </p>
            <div className="flex items-center gap-2 pt-1 border-t border-border-card/50 text-[10px]">
              <span className="text-muted">Status:</span>
              <span className="font-mono font-bold text-primary">
                {hoveredNode.status_code || 'Pending'}
              </span>
              <span className="text-muted ml-auto font-sans">
                {hoveredNode.outcome}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Micro-Telemetry Footer Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs pt-1 px-1">
        <div className="flex items-center gap-2 text-secondary">
          <Activity className="w-3.5 h-3.5 text-brand" />
          <span className="text-[11px] font-medium">
            {isRunning && currentTest
              ? `Currently executing: ${currentTest.method} ${currentTest.path}`
              : `Pipeline telemetry synchronized (${completedSteps} of ${totalSteps} verified)`}
          </span>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-muted font-mono">
          <span>Concurrency: 4 workers</span>
          <span>&bull;</span>
          <span>SLA target: &le; 250ms</span>
          <span>&bull;</span>
          <span>Sandbox: isolated</span>
        </div>
      </div>
    </div>
  );
};
