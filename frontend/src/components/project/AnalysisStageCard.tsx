import React from 'react';
import {
  RefreshCw,
  Check,
  AlertTriangle,
  Play,
  FileCode,
  Code2,
  Cpu,
  Sparkles,
  Network,
} from 'lucide-react';
import { Button } from '../common/Button';
import {
  Analysis,
  PIPELINE_STAGES,
  getStageInfo,
  getStageStatus,
} from './types';

interface AnalysisStageCardProps {
  analysis: Analysis | null;
  analyzing: boolean;
  functionsCount: number;
  graphNodesCount: number;
  onTriggerAnalysis: () => void;
  onSelectFunctionsTab?: () => void;
}

export const AnalysisStageCard: React.FC<AnalysisStageCardProps> = ({
  analysis,
  analyzing,
  functionsCount,
  graphNodesCount,
  onTriggerAnalysis,
  onSelectFunctionsTab,
}) => {
  const isRunning = analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED' || analyzing;
  const isCompleted = analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS';
  const isFailed = analysis?.status === 'FAILED';

  const progressPercent = isCompleted ? 100 : analysis?.progress_percent || (analyzing ? 15 : 0);

  return (
    <div
      className={`glass-card rounded-2xl p-6 shadow-card transition-all duration-200 relative overflow-hidden border ${
        isRunning
          ? 'border-brand/40 ring-1 ring-brand/20'
          : isCompleted
          ? 'border-emerald-500/25'
          : isFailed
          ? 'border-rose-500/30'
          : 'border-border-card'
      }`}
    >
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 relative z-10">
        <div className="flex items-center gap-3">
          {isRunning ? (
            <div className="w-9 h-9 rounded-xl bg-brand/10 text-brand border border-brand/25 flex items-center justify-center shrink-0">
              <RefreshCw className="w-4 h-4 animate-spin" />
            </div>
          ) : isCompleted ? (
            <div className="w-9 h-9 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 border border-emerald-200/80 dark:border-emerald-800/50 flex items-center justify-center shrink-0">
              <Check className="w-4 h-4 stroke-[2.5]" />
            </div>
          ) : isFailed ? (
            <div className="w-9 h-9 rounded-xl bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 border border-rose-200/80 dark:border-rose-800/50 flex items-center justify-center shrink-0">
              <AlertTriangle className="w-4 h-4" />
            </div>
          ) : (
            <div className="w-9 h-9 rounded-xl bg-brand/10 text-brand border border-brand/25 flex items-center justify-center shrink-0">
              <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
            </div>
          )}
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h3 className="text-base font-semibold text-primary tracking-tight">
                Repository Static Analysis Pipeline
              </h3>
              {isCompleted ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/40">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  COMPLETED
                </span>
              ) : isRunning ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand/10 text-brand border border-brand/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-brand animate-ping" />
                  RUNNING
                </span>
              ) : isFailed ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800/40">
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                  FAILED
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-field text-secondary border border-border-card">
                  IDLE • READY
                </span>
              )}
            </div>
            <p className="text-xs text-secondary mt-0.5">
              {getStageInfo(analysis?.current_stage, analysis?.status).desc}
            </p>
          </div>
        </div>

        {/* Percentage & Action Button */}
        <div className="flex items-center gap-4 self-start sm:self-auto">
          <div className="flex items-baseline gap-1.5">
            <span className="text-[11px] uppercase font-semibold text-muted tracking-wider">Progress</span>
            <span className="text-2xl font-bold font-mono text-primary">{progressPercent}%</span>
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={onTriggerAnalysis}
            disabled={isRunning}
            isLoading={isRunning}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${analyzing ? 'animate-spin' : ''}`} />}
          >
            {isCompleted ? 'Re-run Analysis' : 'Start Analysis'}
          </Button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="relative z-10 space-y-1 mt-4">
        <div className="w-full bg-field rounded-full h-2 overflow-hidden border border-border-card">
          <div
            className={`h-full rounded-full transition-all duration-500 ease-out ${
              isCompleted ? 'bg-emerald-500' : 'bg-brand'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* 5-Stage Stepper Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 pt-4 relative z-10">
        {PIPELINE_STAGES.map((stg, idx) => {
          const stageStatus = getStageStatus(stg.key, analysis?.current_stage, analysis?.status);
          const isStgCompleted = stageStatus === 'completed';
          const isStgActive = stageStatus === 'active';

          return (
            <div
              key={stg.key}
              className={`rounded-xl p-3 border transition-colors ${
                isStgActive
                  ? 'bg-brand/5 border-brand/40 shadow-sm ring-1 ring-brand/20'
                  : isStgCompleted
                  ? 'bg-card border-emerald-500/25 dark:border-emerald-500/20 shadow-sm'
                  : 'bg-field/50 border-border-card opacity-60'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                {isStgCompleted ? (
                  <div className="w-4 h-4 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                    <Check className="w-2.5 h-2.5 stroke-[3]" />
                  </div>
                ) : isStgActive ? (
                  <RefreshCw className="w-3.5 h-3.5 text-brand animate-spin shrink-0" />
                ) : (
                  <div className="w-4 h-4 rounded-full border border-border-field bg-card flex items-center justify-center text-[9px] font-semibold text-muted shrink-0">
                    {idx + 1}
                  </div>
                )}
                <span
                  className={`text-xs font-medium truncate ${
                    isStgActive ? 'text-brand font-semibold' : isStgCompleted ? 'text-primary' : 'text-secondary'
                  }`}
                >
                  {stg.label}
                </span>
              </div>
              <p className="text-[10px] text-muted leading-tight truncate">{stg.desc}</p>
            </div>
          );
        })}
      </div>

      {/* Discovered Telemetry Counters */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-border-card relative z-10 text-xs">
        <div className="p-3 rounded-xl bg-field/60 border border-border-card flex items-center gap-3 hover:bg-field transition-colors">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
            <FileCode className="w-4 h-4" />
          </div>
          <div>
            <span className="text-muted block text-[10px] uppercase font-semibold">Scanned Files</span>
            <span className="text-primary font-bold text-base mt-0.5 block font-mono">
              {analysis?.scanned_files_count || 0}
            </span>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-field/60 border border-border-card flex items-center gap-3 hover:bg-field transition-colors">
          <div className="w-8 h-8 rounded-lg bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0">
            <Code2 className="w-4 h-4" />
          </div>
          <div>
            <span className="text-muted block text-[10px] uppercase font-semibold">Parsed Modules</span>
            <span className="text-primary font-bold text-base mt-0.5 block font-mono">
              {analysis?.parsed_files_count || 0}
            </span>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-field/60 border border-border-card flex items-center gap-3 hover:bg-field transition-colors">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <span className="text-muted block text-[10px] uppercase font-semibold">Discovered Endpoints</span>
            <span className="text-emerald-600 dark:text-emerald-400 font-bold text-base mt-0.5 block font-mono">
              {analysis?.endpoint_count || 0}
            </span>
          </div>
        </div>

        <div
          className="p-3 rounded-xl bg-field/60 border border-border-card flex items-center gap-3 hover:bg-field transition-colors cursor-pointer"
          onClick={onSelectFunctionsTab}
        >
          <div className="w-8 h-8 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <span className="text-muted block text-[10px] uppercase font-semibold">Functions Discovered</span>
            <span className="text-amber-600 dark:text-amber-400 font-bold text-base mt-0.5 block font-mono">
              {functionsCount}
            </span>
          </div>
        </div>
      </div>

      {/* Failure message if FAILED */}
      {isFailed && analysis?.error_message && (
        <div className="mt-4 p-3.5 rounded-xl bg-status-failed-bg border border-status-failed/30 text-xs text-status-failed">
          <span className="font-bold block mb-1">Execution Failure:</span>
          <pre className="font-mono whitespace-pre-wrap">{analysis.error_message}</pre>
        </div>
      )}
    </div>
  );
};
