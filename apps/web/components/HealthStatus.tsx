'use client';

import { useEffect, useState } from 'react';
import { getHealth } from '@/lib/api';
import { useTranslation } from '@/lib/i18n';
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

export function HealthStatus() {
  const { t } = useTranslation();
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

  const labelByStatus: Record<Status, string> = {
    checking: t.status.checking,
    online: t.status.online,
    offline: t.status.offline,
  };

  return (
    <Badge
      variant={VARIANT_BY_STATUS[status]}
      className="bg-surface gap-2 border py-1 shadow-sm"
      role="status"
      aria-live="polite"
    >
      <span
        className={cn('h-2 w-2 rounded-full', DOT_COLOR_BY_STATUS[status])}
        aria-hidden="true"
      />
      {labelByStatus[status]}
    </Badge>
  );
}
