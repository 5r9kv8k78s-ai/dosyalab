import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { SiteChrome } from '@/components/layout/SiteChrome';
import { ToastProvider } from '@/components/ui/Toast';
import { TooltipProvider } from '@/components/ui/Tooltip';
import { LanguageProvider } from '@/lib/i18n';
import { tr } from '@/lib/i18n/tr';
import { SITE_URL } from '@/lib/seo/siteUrl';
import { ThemeProvider } from '@/lib/theme';
import './globals.css';

const TITLE = "DosyaLab — Türkiye'nin Dosya Platformu";
const DESCRIPTION =
  'PDF, Word, Excel ve görsel dosyalarınızı tarayıcınızdan dönüştürün, birleştirin ve düzenleyin. Hızlı ve kullanışlı dosya araçları.';

// Must match lib/theme/index.ts's THEME_STORAGE_KEY — duplicated here
// because this script runs before hydration and can't import that module.
// Applies the dark class synchronously, before first paint, so there's no
// flash of the wrong theme while React boots.
const THEME_ANTI_FLASH_SCRIPT = `(function(){try{var k='dosyalab-theme';var stored=localStorage.getItem(k);var dark=stored?stored==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;if(dark){document.documentElement.classList.add('dark');}}catch(e){}})();`;

// Self-hosted by Next.js at build time (no request to Google Fonts at
// runtime), so this never blocks rendering or causes layout shift.
const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: TITLE,
    template: '%s | DosyaLab',
  },
  description: DESCRIPTION,
  applicationName: tr.common.brandName,
  creator: tr.common.brandName,
  publisher: tr.common.brandName,
  category: 'technology',
  formatDetection: {
    telephone: false,
    email: false,
    address: false,
  },
  // TR and EN are served from the same URL via client-side language state
  // (see lib/i18n/LanguageProvider.tsx), not separate routes — there is no
  // real /en variant to point hreflang at, so `languages` is intentionally
  // left out here rather than declaring alternates that don't exist.
  alternates: {
    canonical: '/',
  },
  icons: {
    icon: [
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
    apple: [{ url: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' }],
  },
  manifest: '/site.webmanifest',
  openGraph: {
    type: 'website',
    url: '/',
    siteName: tr.common.brandName,
    locale: 'tr_TR',
    title: TITLE,
    description: DESCRIPTION,
  },
  twitter: {
    card: 'summary_large_image',
    title: TITLE,
    description: DESCRIPTION,
  },
};

export const viewport = {
  themeColor: '#0D5C54',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" className={inter.variable} suppressHydrationWarning>
      <head>
        {/* Runs before hydration, before first paint, so there's no flash of the wrong theme. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_ANTI_FLASH_SCRIPT }} />
      </head>
      <body className="bg-background text-foreground flex min-h-screen flex-col font-sans antialiased">
        <ThemeProvider>
          <LanguageProvider>
            <ToastProvider>
              <TooltipProvider>
                <SiteChrome>{children}</SiteChrome>
              </TooltipProvider>
            </ToastProvider>
          </LanguageProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
