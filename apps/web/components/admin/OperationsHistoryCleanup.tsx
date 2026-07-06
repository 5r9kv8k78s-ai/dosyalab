'use client';

import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/Dialog';
import { useToast } from '@/components/ui/Toast';
import { AdminApiError, clearOperationsHistory } from '@/lib/admin/adminApi';

/**
 * Admin Panel's "Geçmişi Temizle" action — deletes operations-events
 * history only (see the backend's `clear_operations_history`, scoped to the
 * `operations_events` table). Feedback, conversion jobs, and uploaded/
 * output files are untouched, by construction of what that endpoint has a
 * handle on.
 *
 * The confirmation dialog is the required second explicit step before the
 * DELETE request ever fires: clicking the button here only opens it, the
 * request itself is only sent from the dialog's own "Evet, Temizle" click.
 */
export function OperationsHistoryCleanup({ onCleared }: { onCleared: () => void }) {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [isClearing, setIsClearing] = useState(false);

  const handleConfirm = async () => {
    setIsClearing(true);
    try {
      const result = await clearOperationsHistory();
      setOpen(false);
      toast({
        title: 'Geçmiş temizlendi',
        description: `${result.deleted_count} kayıt silindi.`,
        variant: 'success',
      });
      onCleared();
    } catch (error) {
      const message = error instanceof AdminApiError ? error.message : 'Bir hata oluştu.';
      toast({ title: 'Temizleme başarısız oldu', description: message, variant: 'danger' });
    } finally {
      setIsClearing(false);
    }
  };

  return (
    <div className="border-border bg-surface rounded-xl border p-4">
      <p className="text-foreground text-small font-semibold">İşlem Geçmişini Temizle</p>
      <p className="text-muted text-small mt-1">
        Genel Bakış, Araçlar ve Hatalar ekranlarını besleyen işlem geçmişini kalıcı olarak siler.
        Geri bildirimler ve devam eden işlemler bundan etkilenmez.
      </p>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button variant="danger" size="sm" className="mt-3">
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            Geçmişi Temizle
          </Button>
        </DialogTrigger>
        <DialogContent closeLabel="Kapat">
          <DialogTitle>Geçmişi Temizle</DialogTitle>
          <DialogDescription>
            Tüm işlem ve hata geçmişi silinecek. Bu işlem geri alınamaz.
          </DialogDescription>
          <div className="mt-5 flex justify-end gap-2">
            <DialogClose asChild>
              <Button variant="outline" size="sm" disabled={isClearing}>
                Vazgeç
              </Button>
            </DialogClose>
            <Button variant="danger" size="sm" loading={isClearing} onClick={handleConfirm}>
              Evet, Temizle
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
