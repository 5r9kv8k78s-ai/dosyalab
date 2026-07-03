import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** Merges Tailwind class lists, resolving conflicting utilities (e.g. two `px-*` values). */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Saves a blob already held in memory as a file, via a throwaway object URL
 * and an invisible anchor click — the standard trick for triggering a
 * browser "Save As" without a real file on disk. Safe to call more than
 * once for the same blob (e.g. a "download again" button). */
export function triggerBrowserDownload(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}
