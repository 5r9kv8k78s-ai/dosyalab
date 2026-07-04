/**
 * Single source of truth for DosyaLab's canonical public URL, consumed by
 * every metadata surface that needs it (root layout, robots.ts, sitemap.ts,
 * opengraph-image.tsx, JSON-LD) so they can't drift from each other.
 *
 * Reads `NEXT_PUBLIC_SITE_URL` (the repo's documented convention — see
 * apps/web/.env.example) and falls back to a localhost URL in development
 * so metadata generation never crashes when the variable isn't set yet.
 * Deliberately does NOT fall back to a Vercel preview URL — that would bake
 * a throwaway deployment's hostname into canonical/OG/sitemap URLs.
 */

const DEV_FALLBACK_SITE_URL = 'http://localhost:3000';

function normalizeSiteUrl(rawValue: string | undefined): string {
  const trimmed = (rawValue ?? '').trim();
  if (!trimmed) return DEV_FALLBACK_SITE_URL;

  // Accept a bare host (e.g. "dosyalab.com") as well as a full URL — avoids
  // a broken metadataBase if the env var is set without a scheme.
  const withScheme = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;

  try {
    const url = new URL(withScheme);
    return url.origin;
  } catch {
    return DEV_FALLBACK_SITE_URL;
  }
}

export const SITE_URL = normalizeSiteUrl(process.env.NEXT_PUBLIC_SITE_URL);
