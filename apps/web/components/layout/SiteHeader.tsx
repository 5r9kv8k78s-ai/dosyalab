import Link from 'next/link';
import { HealthStatus } from '@/components/HealthStatus';

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-sticky border-b border-border bg-surface/80 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="focus-ring flex items-center gap-2 rounded-md">
          {/* eslint-disable-next-line @next/next/no-img-element -- static brand asset, no next/image benefit for a 32px SVG mark */}
          <img src="/brand/logo.svg" width={32} height={32} alt="" className="rounded-md" />
          <span className="text-xl font-extrabold tracking-tight text-foreground">DosyaLab</span>
        </Link>
        <HealthStatus />
      </div>
    </header>
  );
}
