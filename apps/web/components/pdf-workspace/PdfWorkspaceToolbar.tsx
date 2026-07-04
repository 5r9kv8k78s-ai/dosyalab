'use client';

import { useTranslation } from '@/lib/i18n';

/** Select All / Clear Selection + live selected-count, used by the delete
 * and extract modes. Reorder mode uses its own reset action instead (see
 * PdfWorkspace.tsx), since page selection isn't its primary interaction. */
export function PdfWorkspaceToolbar({
  selectedCount,
  onSelectAll,
  onClearSelection,
}: {
  selectedCount: number;
  onSelectAll: () => void;
  onClearSelection: () => void;
}) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-small text-muted font-medium">
        {t.pdfWorkspace.selectedCount(selectedCount)}
      </p>
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={onSelectAll}
          className="focus-ring text-small text-primary hover:text-primary-hover duration-base rounded font-medium transition-colors"
        >
          {t.pdfWorkspace.selectAll}
        </button>
        <button
          type="button"
          onClick={onClearSelection}
          disabled={selectedCount === 0}
          className="focus-ring text-small text-muted hover:text-foreground duration-base rounded font-medium transition-colors disabled:pointer-events-none disabled:opacity-40"
        >
          {t.pdfWorkspace.clearSelection}
        </button>
      </div>
    </div>
  );
}
