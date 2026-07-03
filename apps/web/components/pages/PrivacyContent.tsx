'use client';

import { useTranslation } from '@/lib/i18n';
import { StaticPage } from '@/components/layout/StaticPage';

export function PrivacyContent() {
  const { t } = useTranslation();
  const privacy = t.pages.privacy;

  return (
    <StaticPage title={privacy.heading}>
      <p>{privacy.intro}</p>

      <h2 className="text-h3 pt-2">{privacy.filesTitle}</h2>
      <p>{privacy.filesBody}</p>

      <h2 className="text-h3 pt-2">{privacy.accountsTitle}</h2>
      <p>{privacy.accountsBody}</p>

      <h2 className="text-h3 pt-2">{privacy.changesTitle}</h2>
      <p>{privacy.changesBody}</p>
    </StaticPage>
  );
}
