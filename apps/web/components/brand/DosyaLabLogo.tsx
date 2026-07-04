import { cn } from '@/lib/utils';

export interface DosyaLabLogoProps {
  /** Symbol size in px. Falls back to the header's desktop size (36px) —
   * override via `className` (e.g. responsive height/width utilities) when
   * the symbol needs to change size across breakpoints, since CSS
   * width/height always wins over this SVG attribute. */
  size?: number;
  className?: string;
  /** Renders the wordmark next to the symbol. */
  showWordmark?: boolean;
  /** Wordmark text — defaults to the literal brand name, but callers can
   * pass `t.common.brandName` to keep it flowing through i18n even though
   * the string itself is identical in every locale. */
  wordmark?: string;
  /** Optional small brand signature line rendered under the wordmark (e.g.
   * "Türkiye'nin dosya platformu"). Ignored unless `showWordmark` is also
   * set. Hidden below the `sm` breakpoint and marked `aria-hidden` — the
   * logo link's accessible name already identifies the brand, so this is
   * purely a visual signature, not additional announced text. */
  tagline?: string;
}

/**
 * The DosyaLab brand mark: a single continuous, three-segment route drawn
 * as one rounded stroke — a file entering, being recognized, and moving out
 * to a different, useful shape. Abstract geometry only (no cloud/upload/
 * document/folder/hexagon/monogram motifs), one solid color via
 * `currentColor` so it inherits `text-primary` from the caller.
 */
export function DosyaLabLogo({
  size = 36,
  className,
  showWordmark = false,
  wordmark = 'DosyaLab',
  tagline,
}: DosyaLabLogoProps) {
  return (
    <span className="inline-flex items-center gap-2 sm:gap-2.5">
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        role="img"
        aria-label="DosyaLab"
        className={cn('shrink-0', className)}
      >
        <path
          d="M8 27H16L24 13H32"
          stroke="currentColor"
          strokeWidth="5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {showWordmark && (
        <span className="flex flex-col justify-center">
          <span className="text-foreground text-xl font-bold leading-tight sm:text-2xl">
            {wordmark}
          </span>
          {tagline && (
            <span
              aria-hidden="true"
              className="text-muted mt-0.5 hidden text-[11px] font-medium leading-tight sm:block"
            >
              {tagline}
            </span>
          )}
        </span>
      )}
    </span>
  );
}
