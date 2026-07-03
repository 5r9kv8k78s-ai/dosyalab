import type { ReactNode } from 'react';

export function StaticPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-h1">{title}</h1>
      <div className="text-body text-foreground mt-6 space-y-4">{children}</div>
    </main>
  );
}
