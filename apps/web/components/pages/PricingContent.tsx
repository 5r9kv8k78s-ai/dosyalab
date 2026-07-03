'use client';

import { useTranslation } from '@/lib/i18n';
import { StaticPage } from '@/components/layout/StaticPage';

export function PricingContent() {
  const { t } = useTranslation();
  const pricing = t.pages.pricing;

  return (
    <StaticPage title={pricing.heading}>
      <p>{pricing.body}</p>
    </StaticPage>
  );
}
