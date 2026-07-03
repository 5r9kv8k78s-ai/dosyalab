'use client';

import { LOCALES, useTranslation } from '@/lib/i18n';
import { cn } from '@/lib/utils';

export function LanguageSwitcher() {
  const { locale, t, setLocale } = useTranslation();

  return (
    <div
      role="group"
      aria-label={t.language.switcherAriaLabel}
      className="border-border bg-surface flex items-center gap-0.5 rounded-full border p-0.5"
    >
      {LOCALES.map((candidate) => (
        <button
          key={candidate}
          type="button"
          aria-pressed={candidate === locale}
          onClick={() => setLocale(candidate)}
          className={cn(
            'focus-ring rounded-full px-2.5 py-1 text-small font-medium uppercase transition-colors duration-fast',
            candidate === locale
              ? 'bg-primary text-primary-foreground'
              : 'text-muted hover:text-foreground',
          )}
        >
          {candidate}
        </button>
      ))}
    </div>
  );
}
