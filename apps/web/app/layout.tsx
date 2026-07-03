import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { SiteFooter } from '@/components/layout/SiteFooter';
import { SiteHeader } from '@/components/layout/SiteHeader';
import { ToastProvider } from '@/components/ui/Toast';
import { TooltipProvider } from '@/components/ui/Tooltip';
import { LanguageProvider } from '@/lib/i18n';
import { tr } from '@/lib/i18n/tr';
import { ThemeProvider } from '@/lib/theme';
import './globals.css';

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
  title: tr.common.brandName,
  description: tr.hero.subtitle,
  icons: {
    icon: [
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
    apple: [{ url: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' }],
  },
  manifest: '/site.webmanifest',
};

export const viewport = {
  themeColor: '#4F46E5',
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
                <SiteHeader />
                <div className="flex-1">{children}</div>
                <SiteFooter />
              </TooltipProvider>
            </ToastProvider>
          </LanguageProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
