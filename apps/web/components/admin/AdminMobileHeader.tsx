'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { AlertTriangle, LayoutDashboard, Lightbulb, LogOut, Wrench } from 'lucide-react';
import { DosyaLabLogo } from '@/components/brand/DosyaLabLogo';
import { createSupabaseBrowserClient } from '@/lib/supabase/client';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/admin', label: 'Genel Bakış', icon: LayoutDashboard },
  { href: '/admin/tools', label: 'Araçlar', icon: Wrench },
  { href: '/admin/errors', label: 'Hatalar', icon: AlertTriangle },
  { href: '/admin/feedback', label: 'Fikirler', icon: Lightbulb },
];

/** Compact header + horizontally scrollable nav row for narrow viewports —
 * a full desktop sidebar is never forced into a 375px viewport. */
export function AdminMobileHeader() {
  const pathname = usePathname();
  const router = useRouter();

  const handleSignOut = async () => {
    const supabase = createSupabaseBrowserClient();
    await supabase.auth.signOut();
    router.push('/admin/login');
    router.refresh();
  };

  return (
    <header className="border-border bg-surface sticky top-0 z-30 border-b">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <DosyaLabLogo className="text-primary h-6 w-6" />
          <span className="text-foreground text-small font-semibold">Yönetim</span>
        </div>
        <button
          type="button"
          onClick={handleSignOut}
          aria-label="Çıkış Yap"
          className="focus-ring text-muted hover:text-danger rounded p-1.5"
        >
          <LogOut className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      <nav className="flex gap-1 overflow-x-auto px-3 pb-2">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === '/admin' ? pathname === '/admin' : pathname?.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'focus-ring duration-base flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
                isActive ? 'bg-primary/[0.1] text-primary' : 'text-muted hover:bg-background',
              )}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden="true" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
