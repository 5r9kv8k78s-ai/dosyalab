'use client';

import { useTranslation } from '@/lib/i18n';
import { StaticPage } from '@/components/layout/StaticPage';

export function AboutContent() {
  const { t } = useTranslation();
  const about = t.pages.about;

  return (
    <StaticPage title={about.heading}>
      <p>{about.paragraph1}</p>
      <p>{about.paragraph2}</p>
      <p>
        {about.paragraph3Prefix}
        <a href="/contact" className="focus-ring rounded font-medium text-primary underline">
          {about.contactLinkText}
        </a>
        {about.paragraph3Suffix}
      </p>
    </StaticPage>
  );
}
