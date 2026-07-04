'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, X } from 'lucide-react';
import { FileTypeIcon, type FileType } from '@/components/icons/FileTypeIcon';
import { useTranslation } from '@/lib/i18n';
import { formatFileSize } from '@/lib/utils';

const VISIBLE_ROWS_COLLAPSED = 5;

/**
 * Batch-aware replacement for the old single-file summary card. A single
 * file renders the same compact look the homepage shipped with (icon +
 * filename + category + "choose a different file"); two or more files
 * switch to a count + total size + per-file removable list, truncated past
 * {@link VISIBLE_ROWS_COLLAPSED} rows rather than growing into a giant
 * permanent list.
 */
export function FileBatchSummary({
  files,
  fileType,
  reorderable,
  onRemoveFile,
  onMoveFile,
  onClear,
}: {
  files: File[];
  fileType: FileType;
  /** Shows up/down reorder controls per row — used when the active tool
   * cares about upload order (e.g. Merge PDF). */
  reorderable?: boolean;
  onRemoveFile: (index: number) => void;
  onMoveFile?: (index: number, direction: -1 | 1) => void;
  onClear: () => void;
}) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  if (files.length === 0) return null;

  if (files.length === 1) {
    const file = files[0];
    return (
      <div className="border-border bg-surface min-w-0 rounded-2xl border p-4">
        <div className="flex min-w-0 items-center gap-3">
          <FileTypeIcon type={fileType} size={32} className="shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="text-small text-foreground truncate font-medium">{file.name}</p>
            <p className="text-muted hidden text-xs sm:block">{t.categories[fileType]}</p>
          </div>
          <button
            type="button"
            className="focus-ring text-small text-muted hover:text-foreground hidden shrink-0 rounded font-medium sm:block"
            onClick={onClear}
          >
            {t.upload.pickDifferentFile}
          </button>
        </div>

        <div className="mt-2 flex items-center justify-between gap-3 sm:hidden">
          <p className="text-muted truncate text-xs">{t.categories[fileType]}</p>
          <button
            type="button"
            className="focus-ring text-small text-muted hover:text-foreground shrink-0 rounded font-medium"
            onClick={onClear}
          >
            {t.upload.pickDifferentFile}
          </button>
        </div>
      </div>
    );
  }

  const totalSize = files.reduce((sum, file) => sum + file.size, 0);
  const visibleFiles = expanded ? files : files.slice(0, VISIBLE_ROWS_COLLAPSED);
  const hiddenCount = files.length - visibleFiles.length;
  const countLabel =
    fileType === 'pdf'
      ? t.batch.pdfFilesDetected(files.length)
      : fileType === 'image'
        ? t.batch.imagesDetected(files.length)
        : t.batch.filesSelected(files.length);

  return (
    <div className="border-border bg-surface min-w-0 rounded-2xl border p-4">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-small text-foreground truncate font-medium">{countLabel}</p>
          <p className="text-muted text-xs">{t.batch.totalSizeLabel(formatFileSize(totalSize))}</p>
        </div>
        <button
          type="button"
          className="focus-ring text-small text-muted hover:text-foreground shrink-0 rounded font-medium"
          onClick={onClear}
        >
          {t.batch.clearFiles}
        </button>
      </div>

      <ul className="mt-3 space-y-1.5">
        {visibleFiles.map((file, index) => (
          <li
            key={`${file.name}-${index}`}
            className="border-border bg-background flex min-w-0 items-center gap-2 rounded-xl border px-3 py-2"
          >
            <FileTypeIcon type={fileType} size={20} label={false} className="shrink-0" />
            <span className="text-small text-foreground min-w-0 flex-1 truncate">{file.name}</span>
            <span className="text-muted shrink-0 text-xs">{formatFileSize(file.size)}</span>
            {reorderable && onMoveFile && (
              <>
                <button
                  type="button"
                  className="focus-ring text-muted hover:text-foreground rounded p-1 disabled:pointer-events-none disabled:opacity-30"
                  disabled={index === 0}
                  aria-label={t.buttons.moveFileUp(file.name)}
                  onClick={() => onMoveFile(index, -1)}
                >
                  <ChevronUp className="h-4 w-4" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  className="focus-ring text-muted hover:text-foreground rounded p-1 disabled:pointer-events-none disabled:opacity-30"
                  disabled={index === files.length - 1}
                  aria-label={t.buttons.moveFileDown(file.name)}
                  onClick={() => onMoveFile(index, 1)}
                >
                  <ChevronDown className="h-4 w-4" aria-hidden="true" />
                </button>
              </>
            )}
            <button
              type="button"
              className="focus-ring text-muted hover:text-danger shrink-0 rounded p-1"
              aria-label={t.buttons.removeFile(file.name)}
              onClick={() => onRemoveFile(index)}
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>

      {hiddenCount > 0 && (
        <button
          type="button"
          className="focus-ring text-small text-primary mt-2 rounded font-medium"
          onClick={() => setExpanded(true)}
        >
          {t.batch.moreFilesTruncated(hiddenCount)}
        </button>
      )}
      {expanded && files.length > VISIBLE_ROWS_COLLAPSED && (
        <button
          type="button"
          className="focus-ring text-small text-primary mt-2 rounded font-medium"
          onClick={() => setExpanded(false)}
        >
          {t.batch.showLess}
        </button>
      )}
    </div>
  );
}
