'use client';

import Link from 'next/link';
import { LogoMark } from '@/components/icons/LogoMark';
import { LanguageSwitcher } from '@/components/layout/LanguageSwitcher';
import { ThemeToggle } from '@/components/layout/ThemeToggle';
import { useTranslation } from '@/lib/i18n';

export function SiteHeader() {
  const { t } = useTranslation();

  return (
    <header className="z-sticky border-border bg-surface/80 sticky top-0 border-b backdrop-blur">
      <div className="mx-auto flex h-[72px] max-w-[1200px] items-center justify-between px-6">
        <Link href="/" className="focus-ring flex items-center gap-2.5 rounded-md">
          <LogoMark size={40} className="text-primary" />
          <span className="text-foreground text-[1.75rem] font-bold tracking-tight">
            {t.common.brandName}
          </span>
        </Link>

        <div className="flex items-center gap-3">
          <ThemeToggle />
          <LanguageSwitcher />
        </div>
      </div>
    </header>
  );
}
