import { cn } from '@/lib/utils';

export interface ProgressProps {
  /** 0-100. Represents a narrative stage band, not necessarily a precise measurement — see callers. */
  value: number;
  className?: string;
  showShimmer?: boolean;
  'aria-label'?: string;
}

export function Progress({ value, className, showShimmer = true, ...aria }: ProgressProps) {
  const clamped = Math.min(100, Math.max(0, value));

  return (
    <div
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn('h-2 w-full overflow-hidden rounded-full bg-border', className)}
      {...aria}
    >
      <div
        className="relative h-full rounded-full bg-primary transition-[width] duration-slow ease-out"
        style={{ width: `${clamped}%` }}
      >
        {showShimmer && (
          <div className="animate-progress-shimmer absolute inset-0 bg-gradient-to-r from-transparent via-white/50 to-transparent" />
        )}
      </div>
    </div>
  );
}

export interface StepDotsProps {
  total: number;
  currentIndex: number;
  className?: string;
}

/** Compact stepper indicator for multi-stage flows (e.g. upload → convert → download). */
export function StepDots({ total, currentIndex, className }: StepDotsProps) {
  return (
    <div className={cn('flex items-center justify-center gap-1.5', className)} role="presentation">
      {Array.from({ length: total }).map((_, index) => {
        const isDone = index < currentIndex;
        const isActive = index === currentIndex;
        return (
          <span
            key={index}
            className={cn(
              'h-1.5 rounded-full transition-all duration-slow',
              isActive ? 'w-5 bg-primary' : isDone ? 'w-1.5 bg-primary' : 'w-1.5 bg-border',
            )}
          />
        );
      })}
    </div>
  );
}
