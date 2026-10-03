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
      ADMIN: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
      DEVELOPER: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
      TESTER: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      VIEWER: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
    };

    return (
      <span className={clsx('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border', roleStyles[role])}>
        {text || role}
      </span>
    );
  }

  const statusStyles = {
    active: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    online: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    ready: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    inactive: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    pending: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  };

  const key = status || 'active';

  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border', statusStyles[key])}>
      <span className={clsx('w-1.5 h-1.5 rounded-full', key === 'inactive' ? 'bg-rose-400' : 'bg-emerald-400')} />
      {text || key.toUpperCase()}
    </span>
  );
};
