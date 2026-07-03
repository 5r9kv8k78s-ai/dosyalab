import type { Metadata } from 'next';
import { ContactContent } from '@/components/pages/ContactContent';
import { tr } from '@/lib/i18n/tr';

export const metadata: Metadata = {
  title: tr.pages.contact.metaTitle,
};

export default function ContactPage() {
  return <ContactContent />;
}
