'use client';

import { useTranslation } from '@/lib/i18n';
import { StaticPage } from '@/components/layout/StaticPage';

export function ContactContent() {
  const { t } = useTranslation();
  const contact = t.pages.contact;

  return (
    <StaticPage title={contact.heading}>
      <p>{contact.paragraph1}</p>
      <p>{contact.paragraph2}</p>
    </StaticPage>
  );
}
