'use client';

import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useTranslation } from '@/lib/i18n';

/** Inline error/empty shell for anything that keeps the workspace from
 * rendering pages — invalid PDF, encrypted PDF, a pdf.js failure, or a
 * zero-page document. Never crashes the page; always offers a way back. */
export function PdfWorkspaceEmptyState({
  title,
  body,
  onBack,
}: {
  title: string;
  body: string;
  onBack: () => void;
}) {
  const { t } = useTranslation();

  return (
    <div className="animate-fade-in flex flex-col items-center gap-3 py-12 text-center">
      <AlertTriangle className="text-warning h-10 w-10" aria-hidden="true" />
      <p className="text-cardTitle text-foreground font-semibold">{title}</p>
      <p className="text-small text-muted max-w-sm">{body}</p>
      <Button variant="outline" className="mt-2" onClick={onBack}>
        {t.pdfWorkspace.backButton}
      </Button>
    </div>
  );
}
