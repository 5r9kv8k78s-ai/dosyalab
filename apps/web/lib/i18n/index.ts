import { en } from './en';
import { tr } from './tr';

export type Locale = 'tr' | 'en';

/** The shape every locale file must satisfy — derived from `tr.ts`, the
 * canonical translation tree, so adding a locale is purely additive: create
 * `xx.ts` typed as `Translations`, add it to `translations` below, and add
 * `'xx'` to `LOCALES`. */
export type Translations = typeof tr;

export const LOCALES: Locale[] = ['tr', 'en'];
export const DEFAULT_LOCALE: Locale = 'tr';
export const LOCALE_STORAGE_KEY = 'dosyalab-locale';

export const LOCALE_LABELS: Record<Locale, string> = {
  tr: 'Türkçe',
  en: 'English',
};

export const translations: Record<Locale, Translations> = { tr, en };

function isLocale(value: string | null): value is Locale {
  return value === 'tr' || value === 'en';
}

/** Reads a previously saved language choice, if any. Browser-only — always
 * `null` during server rendering. */
export function readStoredLocale(): Locale | null {
  if (typeof window === 'undefined') return null;
  const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
  return isLocale(stored) ? stored : null;
}

/** Turkish browsers get Turkish; every other browser language gets English.
 * Browser-only — always the default locale during server rendering. */
export function detectBrowserLocale(): Locale {
  if (typeof navigator === 'undefined') return DEFAULT_LOCALE;
  const language = navigator.language?.toLowerCase() ?? '';
  return language.startsWith('tr') ? 'tr' : 'en';
}

export { LanguageProvider, useTranslation } from './LanguageProvider';
