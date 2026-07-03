'use client';

import { ShieldCheck } from 'lucide-react';
import { ToolsExplorer } from '@/components/conversions/ToolsExplorer';
import { useTranslation } from '@/lib/i18n';

export default function Home() {
  const { t } = useTranslation();

  return (
    <main className="mx-auto flex max-w-6xl flex-col items-center px-6 py-16">
      <section className="max-w-2xl text-center">
        <h1 className="text-h1 sm:text-display">{t.hero.title}</h1>
        <p className="text-body text-muted sm:text-h3 mt-4 sm:font-normal">{t.hero.subtitle}</p>
      </section>

      <section className="mt-12 w-full">
        <ToolsExplorer />
      </section>

      <section className="border-primary/20 bg-primary-light mt-12 flex w-full max-w-2xl items-center gap-3 rounded-lg border px-5 py-4">
        <ShieldCheck className="text-primary h-5 w-5 shrink-0" aria-hidden="true" />
        <p className="text-small text-primary">{t.hero.privacyNote}</p>
      </section>
    </main>
  );
}
