import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';

interface ThemeToggleProps {
  className?: string;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ className = '' }) => {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';
  const label = isDark ? 'Switch to light theme' : 'Switch to dark theme';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      aria-pressed={isDark}
      title={`${label} (press 't')`}
      className={`w-9 h-9 flex items-center justify-center rounded-lg bg-card hover:bg-hover border border-border-card hover:border-brand/40 text-primary shadow-sm dark:bg-white/10 dark:hover:bg-white/20 dark:border-white/20 dark:text-white transition-all focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 focus:ring-offset-card dark:focus:ring-offset-[var(--bg-sidebar)] ${className}`}
    >
      {isDark ? (
        <Sun className="w-4 h-4 text-amber-400 drop-shadow-sm" />
      ) : (
        <Moon className="w-4 h-4 text-brand" />
      )}
    </button>
  );
};
