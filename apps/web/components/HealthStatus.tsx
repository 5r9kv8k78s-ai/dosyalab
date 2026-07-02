'use client';

import { useEffect, useState } from 'react';
import { getHealth } from '@/lib/api';

type Status = 'checking' | 'online' | 'offline';

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

  const dotColor = {
    checking: 'bg-yellow-400',
    online: 'bg-green-500',
    offline: 'bg-red-500',
  }[status];

  const label = {
    checking: 'Checking backend…',
    online: 'Backend online',
    offline: 'Backend unreachable',
  }[status];

  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-1 text-sm text-gray-600 shadow-sm">
      <span className={`h-2 w-2 rounded-full ${dotColor}`} />
      {label}
    </div>
  );
}
