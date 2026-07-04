'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { FeedbackStatusSelect } from '@/components/admin/FeedbackStatusSelect';
import {
  AdminApiError,
  listFeedback,
  updateFeedbackStatus,
  type FeedbackAdminItem,
} from '@/lib/admin/adminApi';
import { FEEDBACK_CATEGORY_LABELS, FEEDBACK_STATUS_LABELS } from '@/lib/admin/feedbackLabels';

const SUMMARY_STATUSES = ['new', 'reviewing', 'planned', 'completed'];

export default function AdminFeedbackPage() {
  const router = useRouter();
  const [items, setItems] = useState<FeedbackAdminItem[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    listFeedback({ status: statusFilter || undefined, category: categoryFilter || undefined })
      .then((res) => {
        setItems(res.items);
        setCounts(res.counts_by_status);
      })
      .catch((err) => {
        if (err instanceof AdminApiError && (err.status === 401 || err.status === 403)) {
          router.push('/admin/login');
          return;
        }
        setError('Fikirler yüklenemedi.');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, categoryFilter]);

  const handleStatusChange = async (feedbackId: string, nextStatus: string) => {
    setUpdatingId(feedbackId);
    try {
      const updated = await updateFeedbackStatus(feedbackId, nextStatus);
      setItems((prev) => prev.map((item) => (item.feedback_id === feedbackId ? updated : item)));
    } catch (err) {
      if (err instanceof AdminApiError && (err.status === 401 || err.status === 403)) {
        router.push('/admin/login');
        return;
      }
      // Reflect the real persisted state rather than an optimistic guess.
      load();
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div>
      <h1 className="text-foreground text-xl font-semibold">Fikirler</h1>
      <p className="text-muted text-small mt-1">
        Kullanıcılardan gelen fikir, öneri ve geri bildirimler.
      </p>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {SUMMARY_STATUSES.map((status) => (
          <div key={status} className="border-border bg-surface rounded-xl border p-4">
            <p className="text-muted text-small font-medium">{FEEDBACK_STATUS_LABELS[status]}</p>
            <p className="text-foreground mt-1.5 text-2xl font-semibold tabular-nums">
              {counts[status] ?? 0}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <select
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
          aria-label="Durum filtresi"
          className="border-border bg-surface text-foreground focus-ring text-small rounded-md border px-3 py-2"
        >
          <option value="">Tüm durumlar</option>
          {Object.entries(FEEDBACK_STATUS_LABELS).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={categoryFilter}
          onChange={(event) => setCategoryFilter(event.target.value)}
          aria-label="Kategori filtresi"
          className="border-border bg-surface text-foreground focus-ring text-small rounded-md border px-3 py-2"
        >
          <option value="">Tüm kategoriler</option>
          {Object.entries(FEEDBACK_CATEGORY_LABELS).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="text-danger text-small mt-6">{error}</p>}
      {!error && loading && <p className="text-muted text-small mt-6">Yükleniyor…</p>}

      {!error && !loading && (
        <ul className="mt-4 space-y-3">
          {items.length === 0 && (
            <li className="text-muted text-small border-border bg-surface rounded-xl border px-4 py-6 text-center">
              Gösterilecek fikir yok.
            </li>
          )}
          {items.map((item) => (
            <li key={item.feedback_id} className="border-border bg-surface rounded-xl border p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <span className="bg-primary/[0.1] text-primary rounded-full px-2 py-0.5 text-xs font-medium">
                    {FEEDBACK_CATEGORY_LABELS[item.category] ?? item.category}
                  </span>
                  <p className="text-muted mt-1.5 text-xs">
                    {new Date(item.created_at).toLocaleString('tr-TR')}
                  </p>
                </div>
                <FeedbackStatusSelect
                  value={item.status}
                  disabled={updatingId === item.feedback_id}
                  onChange={(next) => handleStatusChange(item.feedback_id, next)}
                />
              </div>
              <p className="text-foreground text-small mt-3 whitespace-pre-line">{item.message}</p>
              {item.email && <p className="text-muted mt-2 text-xs">{item.email}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
