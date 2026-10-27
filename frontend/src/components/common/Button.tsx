import React from 'react';
import { clsx } from 'clsx';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  className,
  disabled,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 focus:ring-offset-card disabled:opacity-45 disabled:cursor-not-allowed select-none active:translate-y-px tracking-tight';

  const variants = {
    primary:
      'bg-brand text-on-brand hover:bg-brand-hover shadow-tactile border border-brand-hover/40 font-semibold active:shadow-tactile-pressed relative before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/25 before:rounded-t-lg',
    secondary:
      'bg-card text-primary border border-border-card hover:bg-hover shadow-tactile-sm font-medium active:shadow-tactile-pressed relative before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/10 before:rounded-t-lg',
    danger:
      'bg-status-failed text-white hover:opacity-95 shadow-tactile border border-status-failed/40 font-medium active:shadow-tactile-pressed relative before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/20 before:rounded-t-lg',
    outline:
      'border border-border-card text-primary hover:bg-hover hover:border-border-field bg-transparent active:bg-field',
    ghost:
      'text-secondary hover:text-primary hover:bg-hover bg-transparent active:bg-field',
  };

  const sizes = {
    sm: 'text-xs h-8 px-3 gap-1.5',
    md: 'text-sm h-10 px-4 gap-2',
    lg: 'text-base h-11 px-5 gap-2.5',
  };

  return (
    <button
      className={clsx(baseStyles, variants[variant], sizes[size], className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin text-current" />
      ) : (
        leftIcon
      )}
      {children && <span>{children}</span>}
      {!isLoading && rightIcon}
    </button>
  );
};
