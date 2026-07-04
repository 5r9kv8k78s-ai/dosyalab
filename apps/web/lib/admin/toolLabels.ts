import { tr } from '@/lib/i18n/tr';

/** Reuses the same Turkish tool titles the public site already has (see
 * lib/i18n/tr.ts) — the Admin Panel is Turkish-only, so there's no need
 * for a second copy. An unknown/future slug degrades safely to itself. */
export function labelForToolSlug(slug: string): string {
  const entry = (tr.tools as Record<string, { title: string } | undefined>)[slug];
  return entry?.title ?? slug;
}
