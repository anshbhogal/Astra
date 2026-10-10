import React from 'react';
import {
  CheckCircle2,
  XCircle,
  Shuffle,
  Loader2,
  AlertTriangle,
  MinusCircle,
  type LucideIcon,
} from 'lucide-react';

export type UnifiedStatus =
  | 'PASSED'
  | 'PASS'
  | 'SUCCESS'
  | 'COMPLETED'
  | 'FAILED'
  | 'FAIL'
  | 'FAILURE'
  | 'FLAKY'
  | 'RUNNING'
  | 'IN_PROGRESS'
  | 'PENDING'
  | 'QUEUED'
  | 'ERROR'
  | 'CRASH'
  | 'SKIPPED'
  | 'BLOCKED';

export type TestStatus =
  | UnifiedStatus
  | 'passed'
  | 'failed'
  | 'flaky'
  | 'running'
  | 'error'
  | 'skipped';

interface TestStatusBadgeProps {
  status: UnifiedStatus | string;
  label?: string;
  count?: number;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

interface StatusConfig {
  key: string;
  label: string;
  pillClasses: string;
  Icon: LucideIcon;
  spin?: boolean;
}

const normalizeStatus = (s: string): StatusConfig => {
  const norm = s.toUpperCase().trim();
  switch (norm) {
    case 'PASSED':
    case 'PASS':
    case 'SUCCESS':
    case 'COMPLETED':
      return {
        key: 'passed',
        label: 'Passed',
        pillClasses: 'bg-status-passed-bg text-status-passed border border-status-passed/30',
        Icon: CheckCircle2,
      };

    case 'FAILED':
    case 'FAIL':
    case 'FAILURE':
      return {
        key: 'failed',
        label: 'Failed',
        pillClasses: 'bg-status-failed-bg text-status-failed border border-status-failed/30',
        Icon: XCircle,
      };

    case 'FLAKY':
      return {
        key: 'flaky',
        label: 'Flaky',
        pillClasses: 'bg-status-flaky-bg text-status-flaky border border-status-flaky/30',
        Icon: Shuffle,
      };

    case 'RUNNING':
    case 'IN_PROGRESS':
    case 'EXECUTING':
    case 'STARTING':
      return {
        key: 'running',
        label: 'Running',
        pillClasses: 'bg-status-running-bg text-status-running border border-status-running/30',
        Icon: Loader2,
        spin: true,
      };

    case 'ERROR':
    case 'CRASH':
    case 'FAILED_INFRA':
    case 'ENVIRONMENT_ERROR':
    case 'TIMED_OUT':
      return {
        key: 'error',
        label: 'Error',
        pillClasses: 'bg-status-error-bg text-status-error border border-status-error/30',
        Icon: AlertTriangle,
      };

    case 'SKIPPED':
    case 'BLOCKED':
    case 'QUEUED':
    case 'PENDING':
    default:
      return {
        key: 'skipped',
        label: norm === 'SKIPPED' ? 'Skipped' : norm === 'BLOCKED' ? 'Blocked' : norm === 'PENDING' ? 'Pending' : 'Queued',
        pillClasses: 'bg-status-skipped-bg text-status-skipped border border-status-skipped/30',
        Icon: MinusCircle,
      };
  }
};

export const TestStatusBadge: React.FC<TestStatusBadgeProps> = ({
  status,
  label,
  count,
  size = 'md',
  className = '',
}) => {
  const config = normalizeStatus(status);
  const Icon = config.Icon;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs gap-1 font-medium',
    md: 'px-2.5 py-1 text-xs gap-1.5 font-semibold',
    lg: 'px-3 py-1.5 text-sm gap-2 font-semibold',
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full transition-colors select-none ${
        config.pillClasses
      } ${sizeClasses[size]} ${className}`}
      role="status"
      aria-label={`Status: ${label || config.label}${count !== undefined ? `, Count: ${count}` : ''}`}
    >
      <Icon className={`${iconSizes[size]} shrink-0 ${config.spin ? 'animate-spin' : ''}`} aria-hidden />
      <span>{label || config.label}</span>
      {count !== undefined && (
        <span className="ml-0.5 px-1.5 py-0.2 rounded-full bg-black/10 dark:bg-white/10 text-[11px] font-mono">
          {count}
        </span>
      )}
    </span>
  );
};
