'use client';

import { useEffect, useState } from 'react';
import { Wrench } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/Dialog';
import { Textarea } from '@/components/ui/Textarea';
import { useToast } from '@/components/ui/Toast';
import {
  AdminApiError,
  getAdminMaintenanceStatus,
  updateMaintenanceStatus,
} from '@/lib/admin/adminApi';

/**
 * "Site Durumu" card — the only place Maintenance Mode is toggled from.
 * State is read/written entirely through the backend's Postgres-backed
 * `site_settings` row (see apps/api/app/services/site_settings.py), never
 * held only here — a page refresh always reflects the real persisted
 * state, not optimistic local state alone.
 */
export function MaintenanceModeCard() {
  const { toast } = useToast();
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [message, setMessage] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getAdminMaintenanceStatus()
      .then((status) => {
        if (cancelled) return;
        setEnabled(status.enabled);
        setMessage(status.message ?? '');
      })
      .catch(() => {
        if (!cancelled) setEnabled(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const applyChange = async (nextEnabled: boolean) => {
    setIsSaving(true);
    try {
      const updated = await updateMaintenanceStatus(nextEnabled, message.trim() || null);
      setEnabled(updated.enabled);
      setMessage(updated.message ?? '');
      toast({
        title: updated.enabled ? 'Bakım modu açıldı' : 'Bakım modu kapatıldı',
        variant: updated.enabled ? 'info' : 'success',
      });
    } catch (error) {
      const detail = error instanceof AdminApiError ? error.message : 'Bir hata oluştu.';
      toast({ title: 'Durum güncellenemedi', description: detail, variant: 'danger' });
    } finally {
      setIsSaving(false);
      setConfirmOpen(false);
    }
  };

  const isLoading = enabled === null;

  return (
    <div className="border-border bg-surface rounded-xl border p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-foreground text-small font-semibold">Site Durumu</p>
        {!isLoading && (
          <Badge variant={enabled ? 'warning' : 'success'}>
            {enabled ? 'Bakım Modunda' : 'Site Aktif'}
          </Badge>
        )}
      </div>

      <div className="mt-3">
        <Textarea
          label="Bakım mesajı (opsiyonel)"
          placeholder="Size daha iyi hizmet verebilmek için kısa bir bakım çalışması yapıyoruz. Birazdan tekrar buradayız."
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          rows={2}
          disabled={isLoading || isSaving}
        />
      </div>

      <div className="mt-3">
        {isLoading ? (
          <Button size="sm" variant="outline" disabled>
            Yükleniyor…
          </Button>
        ) : enabled ? (
          <Button size="sm" variant="outline" loading={isSaving} onClick={() => applyChange(false)}>
            Bakım Modunu Kapat
          </Button>
        ) : (
          <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
            <DialogTrigger asChild>
              <Button size="sm" variant="danger">
                <Wrench className="h-4 w-4" aria-hidden="true" />
                Bakım Modunu Aç
              </Button>
            </DialogTrigger>
            <DialogContent closeLabel="Kapat">
              <DialogTitle>Bakım Modunu Aç</DialogTitle>
              <DialogDescription>
                Site bakım moduna alınacak. Yeni dosya işlemleri geçici olarak durdurulacak.
              </DialogDescription>
              <div className="mt-5 flex justify-end gap-2">
                <DialogClose asChild>
                  <Button variant="outline" size="sm" disabled={isSaving}>
                    Vazgeç
                  </Button>
                </DialogClose>
                <Button
                  variant="danger"
                  size="sm"
                  loading={isSaving}
                  onClick={() => applyChange(true)}
                >
                  Evet, Bakım Moduna Al
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>
    </div>
  );
}
