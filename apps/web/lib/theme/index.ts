export type Theme = 'light' | 'dark';

/** Kept in sync by hand with the inline anti-flash script in app/layout.tsx
 * — that script runs before React hydrates and can't import this module. */
export const THEME_STORAGE_KEY = 'dosyalab-theme';

function isTheme(value: string | null): value is Theme {
  return value === 'light' || value === 'dark';
}

/** Browser-only — always `null` during server rendering. */
export function readStoredTheme(): Theme | null {
  if (typeof window === 'undefined') return null;
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  return isTheme(stored) ? stored : null;
}

/** Browser-only — always `'light'` during server rendering. */
export function detectSystemTheme(): Theme {
  if (typeof window === 'undefined' || !window.matchMedia) return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export { ThemeProvider, useTheme } from './ThemeProvider';
