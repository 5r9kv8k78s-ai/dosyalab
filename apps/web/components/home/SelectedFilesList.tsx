'use client';

import { ChevronDown, ChevronUp, X } from 'lucide-react';
import { useTranslation } from '@/lib/i18n';

export function SelectedFilesList({
  files,
  reorderable,
  onRemove,
  onMove,
}: {
  files: File[];
  reorderable: boolean;
  onRemove: (index: number) => void;
  onMove: (index: number, direction: -1 | 1) => void;
}) {
  const { t } = useTranslation();

  if (files.length === 0) return null;

  return (
    <ul className="mt-4 space-y-1.5">
      {files.map((file, index) => (
        <li
          key={`${file.name}-${index}`}
          className="border-border bg-surface flex items-center gap-2 rounded-xl border px-3 py-2"
        >
          <span className="text-small text-foreground flex-1 truncate">
            {index + 1}. {file.name}
          </span>
          {reorderable && (
            <>
              <button
                type="button"
                className="focus-ring text-muted hover:text-foreground rounded p-1 disabled:pointer-events-none disabled:opacity-30"
                disabled={index === 0}
                aria-label={t.buttons.moveFileUp(file.name)}
                onClick={() => onMove(index, -1)}
              >
                <ChevronUp className="h-4 w-4" aria-hidden="true" />
              </button>
              <button
                type="button"
                className="focus-ring text-muted hover:text-foreground rounded p-1 disabled:pointer-events-none disabled:opacity-30"
                disabled={index === files.length - 1}
                aria-label={t.buttons.moveFileDown(file.name)}
                onClick={() => onMove(index, 1)}
              >
                <ChevronDown className="h-4 w-4" aria-hidden="true" />
              </button>
            </>
          )}
          <button
            type="button"
            className="focus-ring text-muted hover:text-danger rounded p-1"
            aria-label={t.buttons.removeFile(file.name)}
            onClick={() => onRemove(index)}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </li>
      ))}
    </ul>
  );
}
