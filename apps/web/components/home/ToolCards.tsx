'use client';

import { useTranslation } from '@/lib/i18n';
import type { ToolConfig, ToolSlug } from '@/lib/tools';
import { cn } from '@/lib/utils';

/**
 * Auto-generated grid of tool cards for whatever file type was just dropped
 * (see V3 spec's "DOSYA GELDİKTEN SONRA" section) — replaces the old
 * category-card + tool-chip pair entirely.
 */
export function ToolCards({
  tools,
  selectedSlug,
  onSelect,
}: {
  tools: ToolConfig[];
  selectedSlug: ToolSlug | null;
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
        return (
          <button
            key={tool.slug}
            type="button"
            role="radio"
            aria-checked={isActive}
            onClick={() => onSelect(tool)}
            className={cn(
              'focus-ring duration-base hover:shadow-premium rounded-2xl border p-5 text-left transition-all hover:-translate-y-[3px]',
              isActive ? 'border-primary bg-primary/[0.08]' : 'border-border bg-surface',
            )}
          >
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
