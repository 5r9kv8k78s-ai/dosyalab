import type { ReactNode } from 'react';
import { AdminMobileHeader } from './AdminMobileHeader';
import { AdminSidebar } from './AdminSidebar';

export function AdminShell({ adminEmail, children }: { adminEmail: string; children: ReactNode }) {
  return (
    <div className="bg-background min-h-screen">
      <div className="hidden md:fixed md:inset-y-0 md:left-0 md:block md:w-60">
        <AdminSidebar adminEmail={adminEmail} />
      </div>
      <div className="md:hidden">
        <AdminMobileHeader />
      </div>
      <main className="md:ml-60">
        <div className="mx-auto max-w-[1200px] px-4 py-6 sm:px-6 md:py-8">{children}</div>
      </main>
    </div>
  );
}
