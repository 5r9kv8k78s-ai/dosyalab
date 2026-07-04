import { createBrowserClient } from '@supabase/ssr';

/** Official @supabase/ssr browser client — used only by the Admin Panel
 * (public site pages never call this). Manages the session via cookies
 * itself; we never manually read/write tokens to localStorage. */
export function createSupabaseBrowserClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL ?? '',
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '',
  );
}
