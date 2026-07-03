import type { Metadata } from 'next';
import { PrivacyContent } from '@/components/pages/PrivacyContent';
import { tr } from '@/lib/i18n/tr';

export const metadata: Metadata = {
  title: tr.pages.privacy.metaTitle,
};

export default function PrivacyPage() {
  return <PrivacyContent />;
}
