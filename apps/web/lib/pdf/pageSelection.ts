/** Pure helpers for the page-selection and reorder state used by the PDF
 * workspace — kept framework-free so they're trivial to reason about and
 * reuse across delete/extract (selection) and reorder (ordering) modes. */

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

export function identityOrder(pageCount: number): number[] {
  return Array.from({ length: pageCount }, (_, index) => index + 1);
}

export function moveInOrder(order: number[], fromIndex: number, toIndex: number): number[] {
  if (
    fromIndex === toIndex ||
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= order.length ||
    toIndex >= order.length
  ) {
    return order;
  }
  const next = [...order];
  const [moved] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, moved);
  return next;
}

export function isIdentityOrder(order: number[]): boolean {
  return order.every((page, index) => page === index + 1);
}
