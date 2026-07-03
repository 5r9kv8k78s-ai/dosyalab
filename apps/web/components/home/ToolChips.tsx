'use client';

import { Chip } from '@/components/ui/Chip';
import { useTranslation } from '@/lib/i18n';
import { toolsByFileType, type ToolConfig, type ToolSlug } from '@/lib/tools';
import type { FileType } from '@/components/icons/FileTypeIcon';

export function ToolChips({
  category,
  selectedSlug,
  onSelect,
}: {
  category: FileType;
  selectedSlug: ToolSlug;
  onSelect: (tool: ToolConfig) => void;
}) {
  const { t } = useTranslation();
  const tools = toolsByFileType(category);

  if (tools.length === 0) {
    return <p className="text-small text-muted text-center">{t.categories.emptyState}</p>;
  }

  return (
    <div
      role="radiogroup"
      aria-label={t.toolChips.ariaLabel}
      className="flex flex-wrap items-center justify-center gap-2"
    >
      {tools.map((tool) => (
        <Chip key={tool.slug} selected={tool.slug === selectedSlug} onClick={() => onSelect(tool)}>
          {t.tools[tool.slug].title}
        </Chip>
      ))}
    </div>
  );
}
