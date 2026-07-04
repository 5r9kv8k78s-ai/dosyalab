import type { ReactNode } from 'react';
import { redirect } from 'next/navigation';
import { AdminShell } from '@/components/admin/AdminShell';
import { createSupabaseServerClient } from '@/lib/supabase/server';

// This checks only "is there an authenticated Supabase user" — the same
// check middleware.ts already performs. It intentionally does NOT decide
// admin authorization (that requires the backend-only ADMIN_EMAILS
// allowlist, which must never reach the browser). A signed-in-but-
// non-admin user can render this shell; the first real data request in
// lib/admin/adminApi.ts will get 403 from the API, sign the session out,
// and the page redirects to /admin/login — see that module's adminFetch.
export default async function ProtectedAdminLayout({ children }: { children: ReactNode }) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect('/admin/login');
  }

  return <AdminShell adminEmail={user.email ?? ''}>{children}</AdminShell>;
}
