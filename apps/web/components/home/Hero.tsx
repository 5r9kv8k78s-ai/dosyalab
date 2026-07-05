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
    <section className="mx-auto w-full max-w-3xl px-5 pb-1 pt-3 text-center sm:px-6 sm:pb-2 sm:pt-5">
      <h1 className="animate-fade-in-up text-foreground sm:text-display text-[30px] font-bold leading-[1.08] tracking-[-0.03em] min-[360px]:text-[34px]">
        {t.hero.title}
      </h1>

      <p className="animate-fade-in-up text-body text-muted mx-auto mt-1.5 max-w-xl px-1 [animation-delay:80ms]">
        {t.hero.subtitle}
      </p>

      <div className="animate-fade-in-up mt-2.5 flex flex-wrap items-center justify-center gap-2 [animation-delay:160ms] sm:mt-3 sm:gap-3">
        {BADGES.map((badge) => (
          <span
            key={badge.key}
            className="border-border bg-surface text-small text-foreground inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-medium shadow-sm sm:px-4 sm:py-2"
          >
            <span aria-hidden="true">{badge.emoji}</span>
            {t.hero[badge.key]}
          </span>
        ))}
      </div>
    </section>
  );
}
