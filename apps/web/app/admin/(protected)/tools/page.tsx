'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { RangeSwitcher } from '@/components/admin/RangeSwitcher';
import {
  AdminApiError,
  getTools,
  type DateRangeKey,
  type ToolAggregationItem,
} from '@/lib/admin/adminApi';
import { labelForToolSlug } from '@/lib/admin/toolLabels';

function formatDuration(ms: number | null): string {
  if (ms === null) return '—';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} sn`;
}

type SortKey = 'attempt_count' | 'success_rate' | 'average_duration_ms';

export default function AdminToolsPage() {
  const router = useRouter();
  const [range, setRange] = useState<DateRangeKey>('7d');
  const [tools, setTools] = useState<ToolAggregationItem[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>('attempt_count');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getTools(range)
      .then((res) => {
        if (!cancelled) setTools(res.tools);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof AdminApiError && (err.status === 401 || err.status === 403)) {
          router.push('/admin/login');
          return;
        }
        setError('Araç verileri yüklenemedi.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [range, router]);

  const sorted = [...tools].sort((a, b) => {
    const av = a[sortKey] ?? 0;
    const bv = b[sortKey] ?? 0;
    return bv - av;
  });

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-foreground text-xl font-semibold">Araçlar</h1>
        <RangeSwitcher value={range} onChange={setRange} />
      </div>

      {error && <p className="text-danger text-small mt-6">{error}</p>}
      {!error && loading && <p className="text-muted text-small mt-6">Yükleniyor…</p>}

      {!error && !loading && (
        <div className="border-border bg-surface mt-6 overflow-x-auto rounded-xl border">
          <table className="w-full min-w-[600px] text-left">
            <thead>
              <tr className="border-border text-muted border-b text-xs">
                <th className="px-4 py-3 font-medium">Araç</th>
                <ThSort
                  label="İşlem"
                  active={sortKey === 'attempt_count'}
                  onClick={() => setSortKey('attempt_count')}
                />
                <th className="px-4 py-3 font-medium">Başarılı</th>
                <th className="px-4 py-3 font-medium">Başarısız</th>
                <ThSort
                  label="Başarı Oranı"
                  active={sortKey === 'success_rate'}
                  onClick={() => setSortKey('success_rate')}
                />
                <ThSort
                  label="Ortalama Süre"
                  active={sortKey === 'average_duration_ms'}
                  onClick={() => setSortKey('average_duration_ms')}
                />
              </tr>
            </thead>
            <tbody>
              {sorted.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-muted text-small px-4 py-6 text-center">
                    Bu aralıkta veri yok.
                  </td>
                </tr>
              )}
              {sorted.map((tool) => (
                <tr
                  key={tool.tool_slug}
                  className="border-border text-small border-b last:border-0"
                >
                  <td className="text-foreground px-4 py-3 font-medium">
                    {labelForToolSlug(tool.tool_slug)}
                  </td>
                  <td className="text-foreground px-4 py-3 tabular-nums">{tool.attempt_count}</td>
                  <td className="text-foreground px-4 py-3 tabular-nums">{tool.success_count}</td>
                  <td className="text-foreground px-4 py-3 tabular-nums">{tool.failure_count}</td>
                  <td className="text-foreground px-4 py-3 tabular-nums">
                    {Math.round(tool.success_rate * 100)}%
                  </td>
                  <td className="text-foreground px-4 py-3 tabular-nums">
                    {formatDuration(tool.average_duration_ms)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ThSort({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <th className="px-4 py-3 font-medium">
      <button
        type="button"
        onClick={onClick}
        className={`focus-ring rounded ${active ? 'text-primary' : 'text-muted hover:text-foreground'}`}
      >
        {label}
      </button>
    </th>
  );
}
