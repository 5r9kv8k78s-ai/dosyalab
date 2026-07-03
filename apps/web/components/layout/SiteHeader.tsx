'use client';

import Link from 'next/link';
import { Github } from 'lucide-react';
import { LogoMark } from '@/components/icons/LogoMark';
import { LanguageSwitcher } from '@/components/layout/LanguageSwitcher';
import { ThemeToggle } from '@/components/layout/ThemeToggle';
import { useTranslation } from '@/lib/i18n';

const GITHUB_REPO_URL = 'https://github.com/5r9kv8k78s-ai/dosyalab';

export function SiteHeader() {
  const { t } = useTranslation();

  const navLinks = [
    { href: '/#tools', label: t.nav.tools },
    { href: '/api', label: t.nav.api },
    { href: '/pricing', label: t.nav.pricing },
    { href: '/about', label: t.nav.about },
  ];

  return (
    <header className="z-sticky border-border bg-surface/80 sticky top-0 border-b backdrop-blur">
      <div className="mx-auto flex max-w-[1200px] items-center justify-between px-6 py-4">
        <Link href="/" className="focus-ring flex items-center gap-2 rounded-md">
          <LogoMark size={26} className="text-primary" />
          <span className="text-cardTitle text-foreground font-semibold tracking-tight">
            {t.common.brandName}
          </span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex" aria-label={t.nav.mainAriaLabel}>
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="focus-ring text-small text-muted duration-base hover:text-foreground rounded font-medium transition-colors"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <ThemeToggle />
          <LanguageSwitcher />
          <a
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noreferrer"
            aria-label={t.nav.github}
            className="focus-ring border-border bg-surface text-muted hover:text-foreground duration-base flex h-9 w-9 items-center justify-center rounded-full border transition-colors"
          >
            <Github className="h-4 w-4" aria-hidden="true" />
          </a>
        </div>
      </div>
    </header>
  );
}
