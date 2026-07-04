'use client';

import { UploadCloud } from 'lucide-react';
import { Dropzone } from '@/components/ui/Dropzone';
import { useTranslation } from '@/lib/i18n';
import { cn } from '@/lib/utils';

/**
 * The homepage's star element (see V3 spec). Deliberately dumb/reusable —
 * takes `accept`/`multiple`/labels as plain props rather than a `ToolConfig`
 * so it can serve both the tool-less initial dropzone and the smaller
 * "add more files" dropzone shown once a multi-file tool is selected.
 */
export function UploadZone({
  accept,
  multiple,
  disabled,
  ariaLabel,
  subtitleLine,
  compact,
  onFiles,
}: {
  accept: string;
  multiple: boolean;
  disabled?: boolean;
  ariaLabel: string;
  subtitleLine: string;
  /** Smaller variant used for the "add more files" dropzone under an
   * already-selected multi-file tool — the big 320px star is only for the
   * very first, tool-less drop. */
  compact?: boolean;
  onFiles: (files: FileList | null) => void;
}) {
  const { t } = useTranslation();

  return (
    <Dropzone
      accept={accept}
      multiple={multiple}
      disabled={disabled}
      onFiles={onFiles}
      aria-label={ariaLabel}
      className={cn(
        'from-surface to-primary/5 hover:border-primary rounded-upload hover:shadow-premium w-full max-w-full border-2 border-dashed bg-gradient-to-br px-5 py-7 transition-all duration-200 hover:scale-[1.01] sm:px-4 sm:py-8',
        compact ? 'min-h-[160px]' : 'min-h-[230px] sm:min-h-[320px]',
      )}
    >
      <UploadCloud
        className={cn('text-primary mb-4', compact ? 'h-9 w-9' : 'h-12 w-12')}
        aria-hidden="true"
      />
      <p className="text-cardTitle text-foreground font-semibold">{t.upload.dropHere}</p>
      <p className="text-small text-muted mt-1">
        {t.upload.or} <span className="text-primary font-medium">{t.upload.chooseFile}</span>
      </p>
      <p className="text-small text-muted mt-4">{subtitleLine}</p>
      <p className="text-muted mt-1 text-xs">{t.upload.maxSizeLabel}</p>
    </Dropzone>
  );
}
