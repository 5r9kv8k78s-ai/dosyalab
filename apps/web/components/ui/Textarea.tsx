'use client';

import { forwardRef, useId } from 'react';
import { cn } from '@/lib/utils';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, hint, id, ...props }, ref) => {
    const generatedId = useId();
    const textareaId = id ?? generatedId;
    const hintId = hint ? `${textareaId}-hint` : undefined;
    const errorId = error ? `${textareaId}-error` : undefined;
    const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined;

    return (
      <div className="space-y-1.5">
        {label && (
          <label htmlFor={textareaId} className="text-small text-foreground font-medium">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          className={cn(
            'border-border bg-surface text-body text-foreground placeholder:text-muted-foreground focus-ring w-full resize-none rounded-md border px-3 py-2',
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
Textarea.displayName = 'Textarea';
