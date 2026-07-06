'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ActivityChart } from '@/components/admin/ActivityChart';
import { MaintenanceModeCard } from '@/components/admin/MaintenanceModeCard';
import { MetricCard } from '@/components/admin/MetricCard';
import { OperationsHistoryCleanup } from '@/components/admin/OperationsHistoryCleanup';
import { RangeSwitcher } from '@/components/admin/RangeSwitcher';
import {
  AdminApiError,
  getOverview,
  getOverviewChart,
  getTools,
  getErrors,
  type DailyActivityItem,
  type DateRangeKey,
  type ErrorAggregationItem,
  type OverviewMetrics,
  type ToolAggregationItem,
} from '@/lib/admin/adminApi';
import { labelForErrorCode } from '@/lib/admin/errorLabels';
import { labelForToolSlug } from '@/lib/admin/toolLabels';

function formatDuration(ms: number | null): string {
  if (ms === null) return '—';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} sn`;
}

function formatPercent(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

export default function AdminOverviewPage() {
  const router = useRouter();
  const [range, setRange] = useState<DateRangeKey>('7d');
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [days, setDays] = useState<DailyActivityItem[]>([]);
  const [topTools, setTopTools] = useState<ToolAggregationItem[]>([]);
  const [topErrors, setTopErrors] = useState<ErrorAggregationItem[]>([]);
  const [error, setErrorState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // Bumped after a successful "Geçmişi Temizle" so the effect below
  // re-fetches every screen's data without duplicating its fetch logic.
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErrorState(null);

    Promise.all([getOverview(range), getOverviewChart(range), getTools(range), getErrors(range)])
      .then(([overviewRes, chartRes, toolsRes, errorsRes]) => {
        if (cancelled) return;
        setOverview(overviewRes);
        setDays(chartRes.days);
        setTopTools(toolsRes.tools.slice(0, 5));
        setTopErrors(errorsRes.errors.slice(0, 5));
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof AdminApiError && (err.status === 401 || err.status === 403)) {
          router.push('/admin/login');
          return;
        }
        setErrorState('Veriler yüklenemedi. Lütfen tekrar deneyin.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [range, router, refreshKey]);

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-foreground text-xl font-semibold">Genel Bakış</h1>
          <p className="text-muted text-small mt-1">DosyaLab operasyonlarının güncel görünümü.</p>
        </div>
        <RangeSwitcher value={range} onChange={setRange} />
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <MaintenanceModeCard />
        <OperationsHistoryCleanup onCleared={() => setRefreshKey((prev) => prev + 1)} />
      </div>

      {error && <p className="text-danger text-small mt-6">{error}</p>}

      {!error && (
        <>
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <MetricCard
              label="Toplam İşlem"
              value={loading ? '—' : String(overview?.conversion_attempts ?? 0)}
            />
            <MetricCard
              label="Başarılı"
              value={loading ? '—' : String(overview?.successful_conversions ?? 0)}
            />
            <MetricCard
              label="Başarı Oranı"
              value={loading ? '—' : formatPercent(overview?.success_rate ?? 0)}
            />
            <MetricCard
              label="İşlenen Dosya"
              value={loading ? '—' : String(overview?.total_files_processed ?? 0)}
            />
            <MetricCard
              label="Ortalama Süre"
              value={loading ? '—' : formatDuration(overview?.average_duration_ms ?? null)}
            />
            <MetricCard
              label="Hata / Red"
              value={
                loading
                  ? '—'
                  : String(
                      (overview?.failed_conversions ?? 0) +
                        (overview?.validation_rejections ?? 0) +
                        (overview?.rate_limit_rejections ?? 0),
                    )
              }
            />
          </div>

          <div className="mt-6">
            <ActivityChart days={days} />
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="border-border bg-surface rounded-xl border p-4">
              <p className="text-foreground text-small font-semibold">En Çok Kullanılan Araçlar</p>
              <ul className="mt-3 space-y-2">
                {topTools.length === 0 && <li className="text-muted text-small">Veri yok.</li>}
                {topTools.map((tool) => (
                  <li key={tool.tool_slug} className="text-small flex items-center justify-between">
                    <span className="text-foreground">{labelForToolSlug(tool.tool_slug)}</span>
                    <span className="text-muted tabular-nums">{tool.attempt_count}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="border-border bg-surface rounded-xl border p-4">
              <p className="text-foreground text-small font-semibold">Son Hata Dağılımı</p>
              <ul className="mt-3 space-y-2">
                {topErrors.length === 0 && <li className="text-muted text-small">Veri yok.</li>}
                {topErrors.map((item) => (
                  <li
                    key={item.error_code}
                    className="text-small flex items-center justify-between"
                  >
                    <span className="text-foreground">{labelForErrorCode(item.error_code)}</span>
                    <span className="text-muted tabular-nums">{item.count}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
