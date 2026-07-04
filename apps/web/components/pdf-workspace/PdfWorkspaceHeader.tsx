'use client';

import { ArrowLeft } from 'lucide-react';
import { useTranslation } from '@/lib/i18n';

export function PdfWorkspaceHeader({
  fileName,
  pageCount,
  operationTitle,
  onBack,
}: {
  fileName: string;
  pageCount: number | null;
  operationTitle: string;
  onBack: () => void;
}) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <button
        type="button"
        onClick={onBack}
        className="focus-ring text-small text-muted hover:text-foreground duration-base flex items-center gap-1.5 self-start rounded font-medium transition-colors"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        {t.pdfWorkspace.back}
      </button>

      <div className="min-w-0 text-right">
        <p className="text-cardTitle text-foreground truncate font-semibold">{operationTitle}</p>
        <p className="text-small text-muted truncate">
          {fileName}
          {pageCount !== null ? ` · ${t.pdfWorkspace.pageCountLabel(pageCount)}` : ''}
        </p>
      </div>
    </div>
  );
}
