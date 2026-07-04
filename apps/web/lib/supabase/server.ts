import { createServerClient, type CookieOptions } from '@supabase/ssr';
import { cookies } from 'next/headers';

/** Official @supabase/ssr server client for Server Components — reads the
 * session from request cookies (refreshed by middleware.ts). Writing
 * cookies from a Server Component itself is a no-op by design (Next.js
 * only allows cookie writes from Server Actions/Route Handlers); the
 * try/catch below matches the pattern Supabase's own docs use. */
export async function createSupabaseServerClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL ?? '',
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '',
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
          try {
            for (const { name, value, options } of cookiesToSet) {
              cookieStore.set(name, value, options);
            }
          } catch {
            // Called from a Server Component render — middleware.ts is
            // responsible for actually refreshing the session cookie.
          }
        },
      },
    },
  );
}
