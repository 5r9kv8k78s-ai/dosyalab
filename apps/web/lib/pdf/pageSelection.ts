/** Pure helpers for the page-selection state used by the PDF workspace's
 * delete/extract modes — kept framework-free so they're trivial to reason
 * about and reuse. */

export function toggleSelection(selected: ReadonlySet<number>, page: number): Set<number> {
  const next = new Set(selected);
  if (next.has(page)) {
    next.delete(page);
  } else {
    next.add(page);
  }
  return next;
}

export function selectAllPages(pageCount: number): Set<number> {
  return new Set(Array.from({ length: pageCount }, (_, index) => index + 1));
}

export function clearPageSelection(): Set<number> {
  return new Set();
}

/** Sorted ascending, 1-indexed page numbers ready to join into the
 * comma-separated `pages` field the backend expects. */
export function sortedSelection(selected: ReadonlySet<number>): number[] {
  return [...selected].sort((a, b) => a - b);
}
