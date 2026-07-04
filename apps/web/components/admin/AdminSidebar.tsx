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

export function AdminSidebar({ adminEmail }: { adminEmail: string }) {
  const pathname = usePathname();
  const router = useRouter();

  const handleSignOut = async () => {
    const supabase = createSupabaseBrowserClient();
    await supabase.auth.signOut();
    router.push('/admin/login');
    router.refresh();
  };

  return (
    <aside className="border-border bg-surface flex h-full w-full flex-col border-r px-4 py-5">
      <div className="flex items-center gap-2 px-2">
        <DosyaLabLogo className="text-primary h-7 w-7" />
        <div>
          <p className="text-foreground text-small font-semibold leading-tight">DosyaLab</p>
          <p className="text-muted text-xs leading-tight">Yönetim</p>
        </div>
      </div>

      <nav className="mt-6 flex-1 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === '/admin' ? pathname === '/admin' : pathname?.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'focus-ring duration-base text-small flex items-center gap-2.5 rounded-lg px-3 py-2 font-medium transition-colors',
                isActive
                  ? 'bg-primary/[0.1] text-primary'
                  : 'text-muted hover:bg-background hover:text-foreground',
              )}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-border mt-auto space-y-2 border-t pt-4">
        <p className="text-muted truncate px-2 text-xs">{adminEmail}</p>
        <button
          type="button"
          onClick={handleSignOut}
          className="focus-ring text-muted hover:bg-background hover:text-danger duration-base text-small flex w-full items-center gap-2.5 rounded-lg px-3 py-2 font-medium transition-colors"
        >
          <LogOut className="h-4 w-4 shrink-0" aria-hidden="true" />
          Çıkış Yap
        </button>
      </div>
    </aside>
  );
}
