import type { Metadata } from 'next';
import { StaticPage } from '@/components/layout/StaticPage';

export const metadata: Metadata = {
  title: 'About — DosyaLab',
};

export default function AboutPage() {
  return (
    <StaticPage title="About DosyaLab">
      <p>
        DosyaLab is a document conversion tool. Drop in a file, and it&apos;s converted on the
        server and sent straight back to your browser — no account, no installation.
      </p>
      <p>
        The first conversion available is PDF → Word, which preserves layout, headings, images,
        and tables as faithfully as the underlying conversion engine allows. More formats — Word →
        PDF, image → PDF, and PDF → Excel — are on the way, built on the same conversion pipeline.
      </p>
      <p>
        DosyaLab is under active development. If something doesn&apos;t convert the way you
        expect, that&apos;s useful to know — see the{' '}
        <a href="/contact" className="focus-ring rounded font-medium text-primary underline">
          contact page
        </a>
        .
      </p>
    </StaticPage>
  );
}
