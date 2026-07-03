import type { Metadata } from 'next';
import { StaticPage } from '@/components/layout/StaticPage';

export const metadata: Metadata = {
  title: 'Terms — DosyaLab',
};

export default function TermsPage() {
  return (
    <StaticPage title="Terms">
      <p>
        DosyaLab is provided as-is, free to use, with no guarantee of uptime or availability. It&apos;s
        under active development and features, limits, and behavior may change.
      </p>
      <p>
        You&apos;re responsible for the files you upload and for having the right to convert and
        download them. Don&apos;t use DosyaLab to process files you don&apos;t have permission to
        handle.
      </p>
      <p>
        This is a minimal starter policy, not a substitute for legal advice — it will be expanded
        as the product matures.
      </p>
    </StaticPage>
  );
}
