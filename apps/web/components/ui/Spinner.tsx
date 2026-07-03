import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const sizeMap = {
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-8 w-8',
} as const;

export interface SpinnerProps {
  size?: keyof typeof sizeMap;
  className?: string;
  /** When provided, wraps the icon in a `role="status"` region with screen-reader text. */
  label?: string;
}

export function Spinner({ size = 'md', className, label }: SpinnerProps) {
  const icon = (
    <Loader2 className={cn('animate-spin', sizeMap[size], className)} aria-hidden="true" />
  );

  if (!label) return icon;

  return (
    <span role="status" className="inline-flex items-center gap-2">
      {icon}
      <span className="sr-only">{label}</span>
    </span>
  );
}
