import React from 'react';
import { clsx } from 'clsx';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, leftIcon, className, id, ...props }, ref) => {
    const inputId = id || props.name;

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="block text-xs font-semibold text-secondary">
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted">
              {leftIcon}
            </div>
          )}
          <input
            id={inputId}
            ref={ref}
            className={clsx(
              'w-full h-10 bg-field text-primary text-sm rounded-lg border transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 focus:ring-offset-card placeholder-muted px-3.5',
              leftIcon && 'pl-10',
              error
                ? 'border-status-failed focus:ring-status-failed'
                : 'border-border-field hover:border-brand',
              className
            )}
            {...props}
          />
        </div>
        {error ? (
          <p className="text-xs text-status-failed font-medium">{error}</p>
        ) : helperText ? (
          <p className="text-xs text-muted">{helperText}</p>
        ) : null}
      </div>
    );
  }
);

Input.displayName = 'Input';
