'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DosyaLabLogo } from '@/components/brand/DosyaLabLogo';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { isAuthRetryableFetchError } from '@supabase/supabase-js';
import { getOverview } from '@/lib/admin/adminApi';
import { createSupabaseBrowserClient } from '@/lib/supabase/client';

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    const supabase = createSupabaseBrowserClient();
    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });

    if (signInError) {
      // A blocked/failed request (e.g. CSP connect-src, offline, DNS) never
      // reaches Supabase, so it's a distinct failure mode from "wrong email
      // or password" — conflating the two previously made a connectivity
      // problem look like a credentials problem to the user.
      setError(
        isAuthRetryableFetchError(signInError)
          ? 'Sunucuya bağlanılamadı. Bağlantınızı kontrol edip tekrar deneyin.'
          : 'Giriş bilgileri doğrulanamadı.',
      );
      setSubmitting(false);
      return;
    }

    // A valid Supabase session isn't enough — the backend independently
    // checks the verified email against ADMIN_EMAILS. Probe that here so
    // a non-admin user gets a clear message on this screen instead of
    // briefly seeing the Admin shell before being bounced out.
    try {
      await getOverview('today');
      router.push('/admin');
      router.refresh();
    } catch {
      setError('Bu hesap yönetim paneli için yetkili değil.');
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-background flex min-h-screen items-center justify-center px-4">
      <div className="border-border bg-surface w-full max-w-sm rounded-2xl border p-8">
        <div className="flex flex-col items-center text-center">
          <DosyaLabLogo className="text-primary h-9 w-9" />
          <h1 className="text-foreground mt-4 text-lg font-semibold">Yönetim Paneli</h1>
        </div>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <Input
            type="email"
            label="E-posta"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <Input
            type="password"
            label="Şifre"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />

          {error && <Alert variant="danger">{error}</Alert>}

          <Button
            type="submit"
            size="lg"
            className="w-full"
            disabled={submitting}
            loading={submitting}
          >
            Giriş Yap
          </Button>
        </form>
      </div>
    </div>
  );
}
