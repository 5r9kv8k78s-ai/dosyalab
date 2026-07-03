import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { SiteFooter } from '@/components/layout/SiteFooter';
import { SiteHeader } from '@/components/layout/SiteHeader';
import { ToastProvider } from '@/components/ui/Toast';
import { TooltipProvider } from '@/components/ui/Tooltip';
import './globals.css';

// Self-hosted by Next.js at build time (no request to Google Fonts at
// runtime), so this never blocks rendering or causes layout shift.
const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'DosyaLab',
  description: 'Belgelerinizi hızlı, güvenli ve ücretsiz dönüştürün.',
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
    <html lang="en" className={inter.variable}>
      <body className="flex min-h-screen flex-col bg-background font-sans text-foreground antialiased">
        <ToastProvider>
          <TooltipProvider>
            <SiteHeader />
            <div className="flex-1">{children}</div>
            <SiteFooter />
          </TooltipProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
