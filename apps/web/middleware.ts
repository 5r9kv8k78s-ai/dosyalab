import { createServerClient, type CookieOptions } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

/**
 * Refreshes the Supabase session cookie on every request and redirects
 * unauthenticated visitors away from /admin/*. This is UX/navigation
 * protection only — it checks "is there a logged-in Supabase user", not
 * "is this user a DosyaLab admin". The actual authorization boundary
 * (verified Supabase JWT + ADMIN_EMAILS allowlist) lives entirely in the
 * FastAPI backend (see apps/api/app/services/admin_auth.py) and is
 * enforced independently of anything this middleware decides.
 */
export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL ?? '',
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '',
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
          for (const { name, value } of cookiesToSet) {
            request.cookies.set(name, value);
          }
          response = NextResponse.next({ request });
          for (const { name, value, options } of cookiesToSet) {
            response.cookies.set(name, value, options);
          }
        },
      },
    },
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { pathname } = request.nextUrl;
  const isLoginRoute = pathname === '/admin/login';
  const isAdminRoute = pathname.startsWith('/admin') && !isLoginRoute;

  if (isAdminRoute && !user) {
    const url = request.nextUrl.clone();
    url.pathname = '/admin/login';
    return NextResponse.redirect(url);
  }

  if (isLoginRoute && user) {
    const url = request.nextUrl.clone();
    url.pathname = '/admin';
    return NextResponse.redirect(url);
  }

  return response;
}

export const config = {
  matcher: ['/admin/:path*'],
};
