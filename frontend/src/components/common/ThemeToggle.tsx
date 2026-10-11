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
      className={`w-9 h-9 flex items-center justify-center rounded-lg bg-field hover:bg-hover border border-border-card text-secondary hover:text-primary dark:bg-white/10 dark:hover:bg-white/15 dark:border-white/15 dark:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 focus:ring-offset-card dark:focus:ring-offset-[var(--bg-sidebar)] ${className}`}
    >
      {isDark ? (
        <Sun className="w-4 h-4 text-amber-400 drop-shadow-sm" />
      ) : (
        <Moon className="w-4 h-4 text-brand" />
      )}
    </button>
  );
};
