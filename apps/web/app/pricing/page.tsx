import type { Metadata } from 'next';
import { PricingContent } from '@/components/pages/PricingContent';
import { tr } from '@/lib/i18n/tr';

export const metadata: Metadata = {
  title: tr.pages.pricing.metaTitle,
};

export default function PricingPage() {
  return <PricingContent />;
}
