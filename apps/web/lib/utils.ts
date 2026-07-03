import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** Merges Tailwind class lists, resolving conflicting utilities (e.g. two `px-*` values). */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
