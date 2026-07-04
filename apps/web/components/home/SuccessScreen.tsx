'use client';

import { CheckCircle2, FileIcon } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useTranslation } from '@/lib/i18n';
import { formatFileSize } from '@/lib/utils';

export function SuccessScreen({
  filename,
  fileSize,
  onDownloadAgain,
  onNewConversion,
}: {
  filename: string | null;
  fileSize: number | null;
  onDownloadAgain: () => void;
  onNewConversion: () => void;
}) {
  const { t } = useTranslation();

  return (
    <div className="animate-fade-in-up flex flex-col items-center gap-4 py-8 text-center">
      <div className="animate-pop-in [animation-delay:100ms]">
        <CheckCircle2 className="text-success h-16 w-16" aria-hidden="true" />
      </div>

      <div>
        <p className="text-cardTitle text-foreground font-semibold">{t.success.title}</p>
        <p className="text-small text-muted mt-1">{t.success.subtitle}</p>
      </div>

      {filename && (
        <div className="border-border bg-background flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left">
          <FileIcon className="text-muted h-5 w-5 shrink-0" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <p className="text-small text-foreground truncate font-medium">{filename}</p>
            {fileSize !== null && <p className="text-muted text-xs">{formatFileSize(fileSize)}</p>}
          </div>
        </div>
      )}

      <div className="mt-2 flex w-full flex-col gap-3">
        <Button size="lg" className="w-full" onClick={onDownloadAgain}>
          {t.buttons.download}
        </Button>
        <Button variant="outline" onClick={onNewConversion}>
          {t.buttons.newConversion}
        </Button>
      </div>
    </div>
  );
}
