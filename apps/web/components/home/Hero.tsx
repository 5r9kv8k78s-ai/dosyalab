'use client';

import { useTranslation } from '@/lib/i18n';

const BADGES = [
  { emoji: '⚡', key: 'badgeFast' as const },
  { emoji: '🔒', key: 'badgeSecure' as const },
  { emoji: '☁️', key: 'badgeNoInstall' as const },
];

export function Hero() {
  const { t } = useTranslation();

  return (
    <section className="mx-auto max-w-3xl px-6 pb-2 pt-4 text-center sm:pt-5">
      <h1 className="animate-fade-in-up text-h1 sm:text-display text-foreground">{t.hero.title}</h1>

      <p className="animate-fade-in-up text-body text-muted mx-auto mt-2 max-w-xl [animation-delay:80ms]">
        {t.hero.subtitle}
      </p>

      <div className="animate-fade-in-up mt-3 flex flex-wrap items-center justify-center gap-3 [animation-delay:160ms]">
        {BADGES.map((badge) => (
          <span
            key={badge.key}
            className="border-border bg-surface text-small text-foreground inline-flex items-center gap-1.5 rounded-full border px-4 py-2 font-medium shadow-sm"
          >
            <span aria-hidden="true">{badge.emoji}</span>
            {t.hero[badge.key]}
          </span>
        ))}
      </div>
    </section>
  );
}
