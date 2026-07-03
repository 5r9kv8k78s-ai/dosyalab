'use client';

import Link from 'next/link';
import { useTranslation } from '@/lib/i18n';

export function SiteFooter() {
  const { t } = useTranslation();

  const footerLinks = [
    { href: '/privacy', label: t.nav.privacy },
    { href: '/terms', label: t.nav.terms },
    { href: '/contact', label: t.nav.contact },
  ];

  return (
    <footer className="border-border border-t">
      <div className="text-muted mx-auto flex max-w-5xl flex-col items-center gap-3 px-6 py-4 text-xs sm:flex-row sm:justify-between">
        <span>
          &copy; {new Date().getFullYear()} {t.common.brandName}
        </span>
        <nav aria-label={t.nav.footerAriaLabel} className="flex items-center gap-5">
          {footerLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="focus-ring hover:text-foreground rounded"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
