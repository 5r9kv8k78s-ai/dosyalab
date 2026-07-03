'use client';

import { forwardRef, useId } from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, hint, id, ...props }, ref) => {
    const generatedId = useId();
    const inputId = id ?? generatedId;
    const hintId = hint ? `${inputId}-hint` : undefined;
    const errorId = error ? `${inputId}-error` : undefined;
    const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined;

    return (
      <div className="space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="text-small font-medium text-foreground">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            'h-10 w-full rounded-md border border-border bg-surface px-3 text-body text-foreground placeholder:text-muted-foreground focus-ring',
            error && 'border-danger focus-visible:ring-danger',
            className,
          )}
          aria-invalid={!!error || undefined}
          aria-describedby={describedBy}
          {...props}
        />
        {hint && !error && (
          <p id={hintId} className="text-small text-muted">
            {hint}
          </p>
        )}
        {error && (
          <p id={errorId} className="text-small text-danger">
            {error}
          </p>
        )}
      </div>
    );
  },
);
Input.displayName = 'Input';
