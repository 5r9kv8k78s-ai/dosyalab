'use client';

import { Skeleton } from '@/components/ui/Skeleton';
import { useTranslation } from '@/lib/i18n';

/** Shown while the PDF is being loaded/parsed by pdf.js, before page count
 * is known — a skeleton shell rather than a blank area. */
export function PdfWorkspaceLoading() {
  const { t } = useTranslation();

  return (
    <div className="animate-fade-in">
      <p className="text-small text-muted mb-4 text-center font-medium">
        {t.pdfWorkspace.preparingPdf}
      </p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        {Array.from({ length: 10 }, (_, index) => (
          <Skeleton key={index} className="aspect-[3/4] w-full rounded-2xl" />
        ))}
      </div>
    </div>
  );
}
