import type { NextConfig } from 'next';

const isProd = process.env.NODE_ENV === 'production';

/** Derives just the origin (scheme+host+port) from the configured API URL,
 * for use in `connect-src` — never wildcarded, since the app only ever
 * talks to this one backend (see lib/api.ts). */
function apiOrigin(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  try {
    return new URL(raw).origin;
  } catch {
    return 'http://localhost:8000';
  }
}

/**
 * Practical CSP V1 for the actual DosyaLab architecture (see the SEO/
 * security audit report for the full reasoning per directive). Not a
 * generic template — every relaxed source below exists because a real,
 * inspected part of this app needs it:
 *
 * - `script-src`/`style-src` 'unsafe-inline': Next.js's inline RSC bootstrap
 *   script and this app's dark-mode anti-flash script (app/layout.tsx), plus
 *   Radix UI's inline positioning styles (Toast/Tooltip/Dialog), are not
 *   nonce-tagged. A per-request nonce would remove this but requires
 *   middleware — out of scope for V1, documented as a V2 hardening target.
 * - `img-src` data:/blob:: PDF page thumbnails are rendered as data-URL
 *   `<img>` tags (components/pdf-workspace/PdfPageCard.tsx).
 * - `worker-src` blob:: pdf.js's worker is a same-origin bundled asset
 *   (lib/pdf/pdfPreview.ts); blob: is kept only as pdf.js's own defensive
 *   fallback path, not something this app deliberately uses.
 * - `connect-src`: 'self' plus the one real, configured API origin — never
 *   a wildcard.
 */
function buildCsp(): string {
  const directives: Record<string, string[]> = {
    'default-src': ["'self'"],
    'script-src': ["'self'", "'unsafe-inline'"],
    'style-src': ["'self'", "'unsafe-inline'"],
    'img-src': ["'self'", 'data:', 'blob:'],
    'font-src': ["'self'", 'data:'],
    'worker-src': ["'self'", 'blob:'],
    'connect-src': ["'self'", apiOrigin()],
    'object-src': ["'none'"],
    'base-uri': ["'self'"],
    'form-action': ["'self'"],
    'frame-ancestors': ["'none'"],
    'manifest-src': ["'self'"],
  };

  if (!isProd) {
    // next dev's Fast Refresh client needs eval + a local HMR websocket —
    // kept out of the production policy entirely rather than weakening it
    // for every environment.
    directives['script-src'].push("'unsafe-eval'");
    directives['connect-src'].push('ws://localhost:*', 'http://localhost:*');
  }

  return Object.entries(directives)
    .map(([directive, sources]) => `${directive} ${sources.join(' ')}`)
    .join('; ');
}

const nextConfig: NextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  async headers() {
    const securityHeaders = [
      { key: 'X-Content-Type-Options', value: 'nosniff' },
      { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
      { key: 'X-Frame-Options', value: 'DENY' },
      // No popups/OAuth flows and nothing embeds DosyaLab in a frame (see
      // frame-ancestors above) — 'same-origin' for both is safe here and
      // doesn't affect the separate-origin API fetch, which is governed by
      // the API's own CORS policy, not these response headers.
      { key: 'Cross-Origin-Opener-Policy', value: 'same-origin' },
      { key: 'Cross-Origin-Resource-Policy', value: 'same-origin' },
      {
        key: 'Permissions-Policy',
        value: 'camera=(), microphone=(), geolocation=()',
      },
      { key: 'Content-Security-Policy', value: buildCsp() },
    ];

    if (isProd) {
      // Deployed behind HTTPS (Vercel) — no `preload` since that's a
      // separate, harder-to-reverse commitment beyond this task's scope.
      securityHeaders.push({
        key: 'Strict-Transport-Security',
        value: 'max-age=63072000; includeSubDomains',
      });
    }

    return [{ source: '/:path*', headers: securityHeaders }];
  },
};

export default nextConfig;
