'use client';

import { useEffect, useState } from 'react';
import { getHealth } from '@/lib/api';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';

type Status = 'checking' | 'online' | 'offline';

const VARIANT_BY_STATUS = {
  checking: 'neutral',
  online: 'success',
  offline: 'danger',
} as const;

const DOT_COLOR_BY_STATUS = {
  checking: 'bg-warning',
  online: 'bg-success',
  offline: 'bg-danger',
} as const;

const LABEL_BY_STATUS = {
  checking: 'Checking backend…',
  online: 'Backend online',
  offline: 'Backend unreachable',
} as const;

export function HealthStatus() {
  const [status, setStatus] = useState<Status>('checking');

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        await getHealth();
        if (!cancelled) setStatus('online');
      } catch {
        if (!cancelled) setStatus('offline');
      }
    }

    check();
    const interval = setInterval(check, 15000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <Badge
      variant={VARIANT_BY_STATUS[status]}
      className="gap-2 border bg-surface py-1 shadow-sm"
      role="status"
      aria-live="polite"
    >
      <span className={cn('h-2 w-2 rounded-full', DOT_COLOR_BY_STATUS[status])} aria-hidden="true" />
      {LABEL_BY_STATUS[status]}
    </Badge>
  );
}
