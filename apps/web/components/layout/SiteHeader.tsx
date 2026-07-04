'use client';

import Link from 'next/link';
import { DosyaLabLogo } from '@/components/brand/DosyaLabLogo';
import { LanguageSwitcher } from '@/components/layout/LanguageSwitcher';
import { ThemeToggle } from '@/components/layout/ThemeToggle';
import { useTranslation } from '@/lib/i18n';

export function SiteHeader() {
  const { t } = useTranslation();

  return (
    <header className="z-sticky border-border bg-surface/80 sticky top-0 border-b backdrop-blur">
      <div className="mx-auto flex h-[72px] max-w-[1200px] items-center justify-between px-6">
        <Link href="/" className="focus-ring flex min-h-[44px] items-center rounded-md">
          <DosyaLabLogo
            showWordmark
            wordmark={t.common.brandName}
            className="text-primary h-[30px] w-[30px] sm:h-9 sm:w-9"
          />
        </Link>

        <div className="flex items-center gap-3">
          <ThemeToggle />
          <LanguageSwitcher />
        </div>
      </div>
    </header>
  );
}
