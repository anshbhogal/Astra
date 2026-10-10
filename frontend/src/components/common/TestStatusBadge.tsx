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
  badgeClass: string;
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
        badgeClass: 'badge-status-passed',
        Icon: CheckCircle2,
      };

    case 'FAILED':
    case 'FAIL':
    case 'FAILURE':
      return {
        key: 'failed',
        label: 'Failed',
        badgeClass: 'badge-status-failed',
        Icon: XCircle,
      };

    case 'FLAKY':
      return {
        key: 'flaky',
        label: 'Flaky',
        badgeClass: 'badge-status-flaky',
        Icon: Shuffle,
      };

    case 'RUNNING':
    case 'IN_PROGRESS':
    case 'EXECUTING':
      return {
        key: 'running',
        label: 'Running',
        badgeClass: 'badge-status-running',
        Icon: Loader2,
        spin: true,
      };

    case 'ERROR':
    case 'CRASH':
    case 'FAILED_INFRA':
      return {
        key: 'error',
        label: 'Error',
        badgeClass: 'badge-status-error',
        Icon: AlertTriangle,
      };

    case 'SKIPPED':
    case 'BLOCKED':
    case 'QUEUED':
    case 'PENDING':
    default:
      return {
        key: 'skipped',
        label: norm === 'SKIPPED' ? 'Skipped' : norm === 'BLOCKED' ? 'Blocked' : norm,
        badgeClass: 'badge-status-skipped',
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
    sm: 'px-2 py-0.5 text-[10px] gap-1',
    md: 'px-2.5 py-1 text-xs gap-1.5',
    lg: 'px-3 py-1.5 text-sm gap-2',
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  };

  return (
    <span
      className={`inline-flex items-center font-bold font-mono rounded-lg transition-colors select-none ${
        config.badgeClass
      } ${sizeClasses[size]} ${className}`}
      role="status"
      aria-label={`Status: ${label || config.label}${count !== undefined ? `, Count: ${count}` : ''}`}
    >
      <Icon className={`${iconSizes[size]} shrink-0 ${config.spin ? 'animate-spin' : ''}`} aria-hidden />
      <span>{label || config.label}</span>
      {count !== undefined && (
        <span className="ml-0.5 px-1.5 py-0.2 rounded bg-black/20 text-[10px] font-mono">
          {count}
        </span>
      )}
    </span>
  );
};
