import React from 'react';
import { clsx } from 'clsx';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'accent' | 'danger' | 'outline' | 'ghost';
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
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-base disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    primary: 'bg-brand hover:bg-brand-hover text-white shadow-brand-glow focus:ring-brand font-semibold',
    accent: 'bg-accent text-accent-text hover:brightness-110 active:scale-[0.98] font-bold shadow-md shadow-accent/20 focus:ring-brand',
    secondary: 'bg-surface hover:bg-raised text-primary border border-border focus:ring-brand',
    danger: 'bg-status-failed hover:opacity-90 text-white shadow-lg focus:ring-status-failed',
    outline: 'border border-border hover:bg-raised text-primary focus:ring-brand',
    ghost: 'hover:bg-raised text-secondary hover:text-primary focus:ring-brand',
  };

  const sizes = {
    sm: 'text-xs px-3 py-1.5 gap-1.5',
    md: 'text-sm px-4 py-2 gap-2',
    lg: 'text-base px-5 py-2.5 gap-2.5',
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
      <span>{children}</span>
      {!isLoading && rightIcon}
    </button>
  );
};
