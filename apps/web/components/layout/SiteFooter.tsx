'use client';

import Link from 'next/link';
import { useTranslation } from '@/lib/i18n';
import { LogoMark } from '@/components/icons/LogoMark';

export function SiteFooter() {
  const { t } = useTranslation();

  const footerLinks = [
    { href: '/about', label: t.nav.about },
    { href: '/privacy', label: t.nav.privacy },
    { href: '/terms', label: t.nav.terms },
    { href: '/contact', label: t.nav.contact },
  ];

  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-4 px-6 py-8 text-small text-muted sm:flex-row sm:justify-between">
        <div className="flex items-center gap-2">
          <LogoMark size={18} className="text-muted" />
          <span>
            &copy; {new Date().getFullYear()} {t.common.brandName}
          </span>
        </div>
        <nav aria-label={t.nav.footerAriaLabel} className="flex items-center gap-6">
          {footerLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="focus-ring rounded hover:text-foreground"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
