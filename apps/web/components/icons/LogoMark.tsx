import { cn } from '@/lib/utils';

export interface LogoMarkProps {
  size?: number;
  className?: string;
}

/**
 * Inline (not `<img src>`) rendering of the monochrome brand mark so
 * `currentColor` actually resolves against the surrounding text color —
 * referencing the SVG as an external image file would isolate it from the
 * page's CSS and always render black regardless of `className`.
 * Source of truth: public/brand/logo-mono.svg.
 */
export function LogoMark({ size = 18, className }: LogoMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      className={cn(className)}
      role="img"
      aria-label="DosyaLab"
    >
      <mask id="dosyalab-mono-cutout-inline">
        <rect width="64" height="64" fill="white" />
        <circle cx="46" cy="46" r="9" fill="black" />
      </mask>
      <path
        d="M36 14L44 22V50H20V14H36Z"
        fill="currentColor"
        mask="url(#dosyalab-mono-cutout-inline)"
      />
      <circle cx="46" cy="46" r="7" fill="currentColor" />
    </svg>
  );
}
