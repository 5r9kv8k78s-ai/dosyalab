import type { MetadataRoute } from 'next';
import { SITE_URL } from '@/lib/seo/siteUrl';

// Every route in this app is a public marketing/product page today — there
// is no admin panel, no authenticated area, and no internal namespace to
// disallow. If one is added later (e.g. /admin), add a matching Disallow
// rule here rather than leaving robots.ts silently stale.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
