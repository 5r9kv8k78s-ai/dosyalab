import type { Metadata } from 'next';
import { TermsContent } from '@/components/pages/TermsContent';
import { tr } from '@/lib/i18n/tr';

export const metadata: Metadata = {
  title: tr.pages.terms.metaTitle,
};

export default function TermsPage() {
  return <TermsContent />;
}
