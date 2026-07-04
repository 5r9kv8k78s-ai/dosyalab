'use client';

import { Sparkles } from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import type { ToolConfig, ToolSlug } from '@/lib/tools';
import { cn } from '@/lib/utils';

/**
 * Auto-generated grid of tool cards for whatever file type was just dropped
 * (see V3 spec's "DOSYA GELDİKTEN SONRA" section) — replaces the old
 * category-card + tool-chip pair entirely. `recommendedSlug` optionally
 * highlights one card (e.g. Merge PDF for a multi-PDF batch) using the same
 * primary-border/tint tokens as the active state, plus a badge with an icon
 * so the distinction isn't color-only.
 */
export function ToolCards({
  tools,
  selectedSlug,
  recommendedSlug,
  onSelect,
}: {
  tools: ToolConfig[];
  selectedSlug: ToolSlug | null;
  recommendedSlug?: ToolSlug | null;
  onSelect: (tool: ToolConfig) => void;
}) {
  const { t } = useTranslation();

  return (
    <div
      role="radiogroup"
      aria-label={t.toolChips.ariaLabel}
      className="animate-fade-in-up grid grid-cols-1 gap-3 sm:grid-cols-2"
    >
      {tools.map((tool) => {
        const isActive = tool.slug === selectedSlug;
        const isRecommended = tool.slug === recommendedSlug;
        return (
          <button
            key={tool.slug}
            type="button"
            role="radio"
            aria-checked={isActive}
            onClick={() => onSelect(tool)}
            className={cn(
              'focus-ring duration-base hover:shadow-premium relative rounded-2xl border p-5 text-left transition-all hover:-translate-y-[3px]',
              isActive || isRecommended
                ? 'border-primary bg-primary/[0.08]'
                : 'border-border bg-surface',
            )}
          >
            {isRecommended && (
              <span className="bg-primary text-small absolute -top-3 left-4 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-medium text-white">
                <Sparkles className="h-3 w-3" aria-hidden="true" />
                {t.batch.recommendedBadge}
              </span>
            )}
            <p className="text-cardTitle text-foreground font-semibold">
              {t.tools[tool.slug].title}
            </p>
            <p className="text-small text-muted mt-1">{t.tools[tool.slug].description}</p>
          </button>
        );
      })}
    </div>
  );
}
