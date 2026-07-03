import type { HTMLAttributes } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

const alertVariants = cva('flex items-start gap-3 rounded-lg border p-4 text-small', {
  variants: {
    variant: {
      info: 'border-primary/20 bg-primary-light',
      success: 'border-success/20 bg-success-bg',
      warning: 'border-warning/20 bg-warning-bg',
      danger: 'border-danger/20 bg-danger-bg',
    },
  },
  defaultVariants: {
    variant: 'info',
  },
});

const iconByVariant = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
} as const;

const iconColorByVariant = {
  info: 'text-primary',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-danger',
} as const;

export interface AlertProps
  extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof alertVariants> {
  title?: string;
}

export function Alert({ className, variant, title, children, ...props }: AlertProps) {
  const resolved = variant ?? 'info';
  const Icon = iconByVariant[resolved];

  return (
    <div
      role={resolved === 'danger' || resolved === 'warning' ? 'alert' : 'status'}
      className={cn(alertVariants({ variant: resolved }), className)}
      {...props}
    >
      <Icon
        className={cn('mt-0.5 h-4 w-4 shrink-0', iconColorByVariant[resolved])}
        aria-hidden="true"
      />
      <div className="text-foreground">
        {title && <p className={cn('font-medium', iconColorByVariant[resolved])}>{title}</p>}
        <div className={title ? 'mt-1' : ''}>{children}</div>
      </div>
    </div>
  );
}
