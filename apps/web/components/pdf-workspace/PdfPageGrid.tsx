'use client';

import { PdfPageCard } from './PdfPageCard';

const GRID_CLASSES = 'grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5';

export function PdfPageGrid({
  pageOrder,
  selectedPages,
  renderThumbnail,
  onToggleSelect,
}: {
  /** Page numbers in current visual order — always the identity
   * `[1..pageCount]` for the selection modes this grid renders today. */
  pageOrder: number[];
  selectedPages: ReadonlySet<number>;
  renderThumbnail: (pageNumber: number, targetWidth: number) => Promise<string>;
  onToggleSelect: (pageNumber: number) => void;
}) {
  return (
    <div className={GRID_CLASSES}>
      {pageOrder.map((pageNumber, index) => (
        <PdfPageCard
          key={pageNumber}
          pageNumber={pageNumber}
          displayPosition={index + 1}
          renderThumbnail={renderThumbnail}
          selected={selectedPages.has(pageNumber)}
          onSelectToggle={() => onToggleSelect(pageNumber)}
        />
      ))}
    </div>
  );
}
