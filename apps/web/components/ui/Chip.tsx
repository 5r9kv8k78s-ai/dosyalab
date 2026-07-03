'use client';

import { cn } from '@/lib/utils';

export interface ChipProps {
  selected?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
  className?: string;
}

/** Single-row selectable pill — used for tool selection on the homepage, but
 * generic enough for any "pick one of several short options" UI. */
export function Chip({ selected, onClick, children, className }: ChipProps) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onClick}
      className={cn(
        'focus-ring text-small duration-base flex h-10 items-center whitespace-nowrap rounded-full border px-5 font-medium transition-all hover:shadow-sm',
        selected
          ? 'border-primary bg-primary text-primary-foreground'
          : 'border-border bg-surface text-foreground hover:bg-background',
        className,
      )}
    >
      {children}
    </button>
  );
}
