'use client';

import { useTranslation } from '@/lib/i18n';
import { StaticPage } from '@/components/layout/StaticPage';

export function ApiContent() {
  const { t } = useTranslation();
  const api = t.pages.api;

  return (
    <StaticPage title={api.heading}>
      <p>{api.body}</p>
    </StaticPage>
  );
}
