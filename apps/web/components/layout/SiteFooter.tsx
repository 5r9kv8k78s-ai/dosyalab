import Link from 'next/link';
import { LogoMark } from '@/components/icons/LogoMark';

const FOOTER_LINKS = [
  { href: '/about', label: 'About' },
  { href: '/privacy', label: 'Privacy Policy' },
  { href: '/terms', label: 'Terms' },
  { href: '/contact', label: 'Contact' },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-4 px-6 py-8 text-small text-muted sm:flex-row sm:justify-between">
        <div className="flex items-center gap-2">
          <LogoMark size={18} className="text-muted" />
          <span>&copy; {new Date().getFullYear()} DosyaLab</span>
        </div>
        <nav aria-label="Footer" className="flex items-center gap-6">
          {FOOTER_LINKS.map((link) => (
            <Link key={link.href} href={link.href} className="focus-ring rounded hover:text-foreground">
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
