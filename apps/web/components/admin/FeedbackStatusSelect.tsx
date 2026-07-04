'use client';

import { FEEDBACK_STATUS_LABELS, FEEDBACK_STATUS_ORDER } from '@/lib/admin/feedbackLabels';

export function FeedbackStatusSelect({
  value,
  disabled,
  onChange,
}: {
  value: string;
  disabled?: boolean;
  onChange: (next: string) => void;
}) {
  return (
    <select
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      aria-label="Durum"
      className="border-border bg-surface text-foreground focus-ring text-small rounded-md border px-2.5 py-1.5 disabled:opacity-50"
    >
      {FEEDBACK_STATUS_ORDER.map((status) => (
        <option key={status} value={status}>
          {FEEDBACK_STATUS_LABELS[status]}
        </option>
      ))}
    </select>
  );
}
