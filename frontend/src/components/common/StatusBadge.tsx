import React from 'react';
import { clsx } from 'clsx';
import { UserRole } from '../../store/authStore';

interface StatusBadgeProps {
  role?: UserRole;
  status?: 'active' | 'inactive' | 'online' | 'ready' | 'pending';
  text?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ role, status, text }) => {
  if (role) {
    const roleStyles: Record<UserRole, string> = {
      ADMIN: 'bg-status-failed-bg text-status-failed border-status-failed/30',
      DEVELOPER: 'bg-brand/10 text-brand border-brand/30',
      TESTER: 'bg-status-flaky-bg text-status-flaky border-status-flaky/30',
      VIEWER: 'bg-field text-secondary border-border-card',
    };

    return (
      <span className={clsx('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border', roleStyles[role])}>
        {text || role}
      </span>
    );
  }

  const statusStyles = {
    active: 'bg-status-passed-bg text-status-passed border-status-passed/30',
    online: 'bg-status-passed-bg text-status-passed border-status-passed/30',
    ready: 'bg-status-passed-bg text-status-passed border-status-passed/30',
    inactive: 'bg-status-failed-bg text-status-failed border-status-failed/30',
    pending: 'bg-status-flaky-bg text-status-flaky border-status-flaky/30',
  };

  const dotColors = {
    active: 'bg-status-passed',
    online: 'bg-status-passed',
    ready: 'bg-status-passed',
    inactive: 'bg-status-failed',
    pending: 'bg-status-flaky',
  };

  const key = status || 'active';

  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border', statusStyles[key])}>
      <span className={clsx('w-1.5 h-1.5 rounded-full', dotColors[key])} />
      {text || key.toUpperCase()}
    </span>
  );
};
