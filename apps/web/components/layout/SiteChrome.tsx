'use client';

import { usePathname } from 'next/navigation';
import { FeedbackButton } from '@/components/feedback/FeedbackButton';
import { SiteFooter } from './SiteFooter';
import { SiteHeader } from './SiteHeader';

/** The public site's header/footer/feedback chrome — omitted entirely for
 * /admin/* routes, which have their own operational shell (see
 * app/admin/layout.tsx) and no public marketing surface. */
export function SiteChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (pathname?.startsWith('/admin')) {
    return <>{children}</>;
  }

  return (
    <>
      <SiteHeader />
      <div className="flex-1">{children}</div>
      <SiteFooter />
      <FeedbackButton />
    </>
  );
}
