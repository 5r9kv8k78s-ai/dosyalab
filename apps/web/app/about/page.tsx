import type { Metadata } from 'next';
import { AboutContent } from '@/components/pages/AboutContent';
import { tr } from '@/lib/i18n/tr';

export const metadata: Metadata = {
  title: tr.pages.about.metaTitle,
};

export default function AboutPage() {
  return <AboutContent />;
}
