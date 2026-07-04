'use client';

import type { DateRangeKey } from '@/lib/admin/adminApi';
import { cn } from '@/lib/utils';

const OPTIONS: { key: DateRangeKey; label: string }[] = [
  { key: 'today', label: 'Bugün' },
  { key: '7d', label: '7 Gün' },
  { key: '30d', label: '30 Gün' },
];

export function RangeSwitcher({
  value,
  onChange,
}: {
  value: DateRangeKey;
  onChange: (value: DateRangeKey) => void;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Tarih aralığı"
      className="border-border bg-surface inline-flex gap-1 rounded-lg border p-1"
    >
      {OPTIONS.map((option) => {
        const isActive = option.key === value;
        return (
          <button
            key={option.key}
            type="button"
            role="radio"
            aria-checked={isActive}
            onClick={() => onChange(option.key)}
            className={cn(
              'focus-ring duration-base text-small rounded-md px-3 py-1.5 font-medium transition-colors',
              isActive ? 'bg-primary text-primary-foreground' : 'text-muted hover:text-foreground',
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
