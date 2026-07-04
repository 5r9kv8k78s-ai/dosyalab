import type { MetadataRoute } from 'next';
import { SITE_URL } from '@/lib/seo/siteUrl';

// Only real, currently-existing public routes — see apps/web/app/* for the
// full route list. No invented tool-landing-page URLs (e.g. /pdf-to-word):
// those don't exist yet, since every tool is reached via the homepage's
// upload-first flow, not a dedicated route.
const ROUTES: Array<{
  path: string;
  changeFrequency: MetadataRoute.Sitemap[number]['changeFrequency'];
  priority: number;
}> = [
  { path: '', changeFrequency: 'weekly', priority: 1 },
  { path: '/about', changeFrequency: 'monthly', priority: 0.5 },
  { path: '/pricing', changeFrequency: 'monthly', priority: 0.5 },
  { path: '/api', changeFrequency: 'monthly', priority: 0.4 },
  { path: '/contact', changeFrequency: 'yearly', priority: 0.3 },
  { path: '/privacy', changeFrequency: 'yearly', priority: 0.3 },
  { path: '/terms', changeFrequency: 'yearly', priority: 0.3 },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  return ROUTES.map(({ path, changeFrequency, priority }) => ({
    url: `${SITE_URL}${path}`,
    lastModified,
    changeFrequency,
    priority,
  }));
}
