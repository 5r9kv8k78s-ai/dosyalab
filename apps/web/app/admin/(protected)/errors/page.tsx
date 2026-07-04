'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { RangeSwitcher } from '@/components/admin/RangeSwitcher';
import {
  AdminApiError,
  getErrors,
  type DateRangeKey,
  type ErrorAggregationItem,
} from '@/lib/admin/adminApi';
import { labelForErrorCode } from '@/lib/admin/errorLabels';

export default function AdminErrorsPage() {
  const router = useRouter();
  const [range, setRange] = useState<DateRangeKey>('7d');
  const [errors, setErrors] = useState<ErrorAggregationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    getErrors(range)
      .then((res) => {
        if (!cancelled) setErrors(res.errors);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof AdminApiError && (err.status === 401 || err.status === 403)) {
          router.push('/admin/login');
          return;
        }
        setLoadError('Hata verileri yüklenemedi.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [range, router]);

  const total = errors.reduce((sum, item) => sum + item.count, 0);

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-foreground text-xl font-semibold">Hatalar</h1>
        <RangeSwitcher value={range} onChange={setRange} />
      </div>

      {loadError && <p className="text-danger text-small mt-6">{loadError}</p>}
      {!loadError && loading && <p className="text-muted text-small mt-6">Yükleniyor…</p>}

      {!loadError && !loading && (
        <div className="border-border bg-surface mt-6 rounded-xl border">
          {errors.length === 0 ? (
            <p className="text-muted text-small px-4 py-6 text-center">Bu aralıkta hata yok.</p>
          ) : (
            <ul>
              {errors.map((item) => {
                const share = total > 0 ? Math.round((item.count / total) * 100) : 0;
                return (
                  <li
                    key={item.error_code}
                    className="border-border flex items-center justify-between gap-4 border-b px-4 py-3 last:border-0"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-foreground text-small font-medium">
                        {labelForErrorCode(item.error_code)}
                      </p>
                      <div className="bg-background mt-1.5 h-1.5 w-full overflow-hidden rounded-full">
                        <div
                          className="bg-primary h-full rounded-full"
                          style={{ width: `${share}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-foreground text-small shrink-0 tabular-nums">
                      {item.count}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
