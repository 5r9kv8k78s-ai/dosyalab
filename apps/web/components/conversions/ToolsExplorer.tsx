'use client';

import { useMemo, useState } from 'react';
import { TOOLS, TOOL_CATEGORIES, type ToolCategory } from '@/lib/tools';
import { cn } from '@/lib/utils';
import { MergePdfCard } from './MergePdfCard';
import { ToolCard } from './ToolCard';

type FilterId = 'all' | ToolCategory;

const FILTERS: { id: FilterId; label: string }[] = [
  { id: 'all', label: 'All' },
  ...TOOL_CATEGORIES,
];

export function ToolsExplorer() {
  const [activeFilter, setActiveFilter] = useState<FilterId>('all');

  const visibleTools = useMemo(
    () => TOOLS.filter((tool) => activeFilter === 'all' || tool.category === activeFilter),
    [activeFilter],
  );

  return (
    <>
      <div
        className="flex flex-wrap justify-center gap-2"
        role="tablist"
        aria-label="Tool categories"
      >
        {FILTERS.map((filter) => (
          <button
            key={filter.id}
            type="button"
            role="tab"
            aria-selected={activeFilter === filter.id}
            onClick={() => setActiveFilter(filter.id)}
            className={cn(
              'focus-ring rounded-full border px-4 py-2 text-small font-medium transition-colors duration-fast',
              activeFilter === filter.id
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-surface text-foreground hover:bg-background',
            )}
          >
            {filter.label}
          </button>
        ))}
      </div>

      <div
        className="mt-8 grid w-full grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4"
        aria-label="Available conversion tools"
      >
        {visibleTools.map((tool) =>
          tool.slug === 'merge-pdf' ? (
            <MergePdfCard key={tool.slug} />
          ) : (
            <ToolCard key={tool.slug} tool={tool} />
          ),
        )}
      </div>
    </>
  );
}
