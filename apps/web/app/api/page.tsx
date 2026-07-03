import type { Metadata } from 'next';
import { ApiContent } from '@/components/pages/ApiContent';
import { tr } from '@/lib/i18n/tr';

export const metadata: Metadata = {
  title: tr.pages.api.metaTitle,
};

export default function ApiPage() {
  return <ApiContent />;
}
