'use client';

import { useCallback, useRef, useState, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface DropzoneProps {
  accept?: string;
  /** Allow selecting/dropping more than one file. Defaults to false (unchanged single-file behavior). */
  multiple?: boolean;
  disabled?: boolean;
  onFiles: (files: FileList | null) => void;
  children: ReactNode;
  className?: string;
  'aria-label'?: string;
}

export function Dropzone({
  accept,
  multiple,
  disabled,
  onFiles,
  children,
  className,
  ...aria
}: DropzoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsDragActive(false);
      if (disabled) return;
      onFiles(event.dataTransfer.files);
    },
    [disabled, onFiles],
  );

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) setIsDragActive(true);
      }}
      onDragLeave={(event) => {
        event.preventDefault();
        setIsDragActive(false);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled || undefined}
      onKeyDown={(event) => {
        if (!disabled && (event.key === 'Enter' || event.key === ' ')) {
          // Prevent the page from scrolling on Space while still activating the dropzone.
          event.preventDefault();
          inputRef.current?.click();
        }
      }}
      className={cn(
        'focus-ring duration-base flex min-h-[160px] flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors',
        disabled
          ? 'border-border bg-background cursor-default'
          : 'border-border hover:border-primary hover:bg-primary-light/40 cursor-pointer',
        isDragActive && 'border-primary bg-primary-light',
        className,
      )}
      {...aria}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        className="hidden"
        onChange={(event) => onFiles(event.target.files)}
        disabled={disabled}
      />
      {children}
    </div>
  );
}
