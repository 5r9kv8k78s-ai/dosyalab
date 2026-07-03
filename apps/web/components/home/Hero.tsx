'use client';

import { motion } from 'framer-motion';
import { useTranslation } from '@/lib/i18n';

const BADGES = [
  { emoji: '⚡', key: 'badgeFast' as const },
  { emoji: '🔒', key: 'badgeSecure' as const },
  { emoji: '☁️', key: 'badgeNoInstall' as const },
];

export function Hero() {
  const { t } = useTranslation();

  return (
    <section className="mx-auto max-w-2xl px-6 pb-6 pt-10 text-center sm:pt-14">
      <motion.h1
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="text-h1 sm:text-hero text-foreground"
      >
        {t.hero.title}
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.08, ease: 'easeOut' }}
        className="text-body sm:text-heroSubtitle text-muted mx-auto mt-2 max-w-xl"
      >
        {t.hero.subtitle}
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.16, ease: 'easeOut' }}
        className="mt-4 flex flex-wrap items-center justify-center gap-3"
      >
        {BADGES.map((badge) => (
          <span
            key={badge.key}
            className="border-border bg-surface text-small text-foreground inline-flex items-center gap-1.5 rounded-full border px-4 py-2 font-medium shadow-sm"
          >
            <span aria-hidden="true">{badge.emoji}</span>
            {t.hero[badge.key]}
          </span>
        ))}
      </motion.div>
    </section>
  );
}
