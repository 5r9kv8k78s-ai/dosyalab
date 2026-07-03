import type { Metadata } from 'next';
import { StaticPage } from '@/components/layout/StaticPage';

export const metadata: Metadata = {
  title: 'Privacy Policy — DosyaLab',
};

export default function PrivacyPage() {
  return (
    <StaticPage title="Privacy Policy">
      <p>This page describes what actually happens to your files and data when you use DosyaLab.</p>

      <h2 className="text-h3 pt-2">Files you upload</h2>
      <p>
        Files are uploaded to the server only to run the conversion you requested. The converted
        result is deleted immediately after you download it. If a conversion is never downloaded,
        both the original upload and any generated file are automatically deleted on a periodic
        cleanup sweep — nothing is kept indefinitely.
      </p>

      <h2 className="text-h3 pt-2">Accounts and tracking</h2>
      <p>
        DosyaLab doesn&apos;t require an account, and doesn&apos;t use analytics or advertising
        trackers. The only requests the app makes are the ones needed to upload your file, run the
        conversion, and serve the result back to you.
      </p>

      <h2 className="text-h3 pt-2">Changes</h2>
      <p>
        DosyaLab is under active development, and this policy will be updated if that behavior
        changes.
      </p>
    </StaticPage>
  );
}
