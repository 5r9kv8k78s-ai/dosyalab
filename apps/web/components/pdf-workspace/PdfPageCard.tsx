'use client';

import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { Check } from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { cn } from '@/lib/utils';

const THUMBNAIL_TARGET_WIDTH = 200;

export interface PdfPageCardProps {
  /** The page's original, identity page number — used as the thumbnail's
   * cache/render key. */
  pageNumber: number;
  /** 1-based position to *show* on the card. */
  displayPosition: number;
  renderThumbnail: (pageNumber: number, targetWidth: number) => Promise<string>;
  /** Present only in selection modes (delete/extract) — its absence is what
   * makes a card non-interactive/non-selectable. */
  onSelectToggle?: () => void;
  selected?: boolean;
  className?: string;
}

export function PdfPageCard({
  pageNumber,
  displayPosition,
  renderThumbnail,
  onSelectToggle,
  selected,
  className,
}: PdfPageCardProps) {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [thumbnailSrc, setThumbnailSrc] = useState<string | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  // Lazy/viewport-aware rendering: a card only asks pdf.js to render its
  // page once it's scrolled near the viewport, so a 100-page PDF never
  // renders 100 canvases up front.
  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: '200px' },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!isVisible) return;
    let cancelled = false;
    renderThumbnail(pageNumber, THUMBNAIL_TARGET_WIDTH).then((src) => {
      if (!cancelled) setThumbnailSrc(src);
    });
    return () => {
      cancelled = true;
    };
  }, [isVisible, pageNumber, renderThumbnail]);

  const interactive = !!onSelectToggle;
  const label = t.pdfWorkspace.pageLabel(displayPosition);

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!interactive) return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onSelectToggle?.();
    }
  };

  return (
    <div
      ref={containerRef}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-pressed={interactive ? !!selected : undefined}
      aria-label={interactive ? label : undefined}
      onClick={interactive ? onSelectToggle : undefined}
      onKeyDown={handleKeyDown}
      className={cn(
        'focus-ring duration-base flex flex-col items-center gap-2 rounded-2xl border p-3 shadow-sm transition-all',
        interactive && 'cursor-pointer hover:-translate-y-0.5 hover:shadow-md',
        selected ? 'border-primary bg-primary/[0.08]' : 'border-border bg-surface',
        className,
      )}
    >
      <div className="border-border bg-background relative flex aspect-[3/4] w-full items-center justify-center overflow-hidden rounded-lg border">
        {thumbnailSrc ? (
          // Locally generated data URL from the user's own file, rendered
          // client-side by pdf.js — not a remote/optimizable image.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={thumbnailSrc} alt={label} className="h-full w-full object-contain" />
        ) : (
          <div className="bg-border h-full w-full animate-pulse" aria-hidden="true" />
        )}

        {selected && (
          <span className="bg-primary text-primary-foreground absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full">
            <Check className="h-3.5 w-3.5" aria-hidden="true" />
          </span>
        )}
      </div>

      <span className="text-small text-foreground font-medium">{label}</span>
    </div>
  );
}
