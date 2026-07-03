import type { Metadata } from 'next';
import { StaticPage } from '@/components/layout/StaticPage';

export const metadata: Metadata = {
  title: 'Contact — DosyaLab',
};

export default function ContactPage() {
  return (
    <StaticPage title="Contact">
      <p>
        DosyaLab is a new, actively developed project, and dedicated support channels aren&apos;t
        set up yet.
      </p>
      <p>Real contact details — support email, issue tracker, or feedback form — will be added here.</p>
    </StaticPage>
  );
}
