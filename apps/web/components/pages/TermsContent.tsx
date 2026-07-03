'use client';

import { useTranslation } from '@/lib/i18n';
import { StaticPage } from '@/components/layout/StaticPage';

export function TermsContent() {
  const { t } = useTranslation();
  const terms = t.pages.terms;

  return (
    <StaticPage title={terms.heading}>
      <p>{terms.paragraph1}</p>
      <p>{terms.paragraph2}</p>
      <p>{terms.paragraph3}</p>
    </StaticPage>
  );
}
