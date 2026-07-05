'use client';

import { Input } from '@/components/ui/Input';
import { useTranslation } from '@/lib/i18n';
import { toolFieldKey, type ToolConfig } from '@/lib/tools';

export function ParameterCard({
  tool,
  values,
  onChange,
}: {
  tool: ToolConfig;
  values: Record<string, string>;
  onChange: (name: string, value: string) => void;
}) {
  const { t } = useTranslation();

  if (tool.fields.length === 0) return null;

  return (
    <div className="border-border bg-surface animate-fade-in-up mt-4 space-y-3 rounded-2xl border p-4 shadow-sm sm:space-y-4 sm:p-6">
      {tool.fields.map((field) => {
        const fieldText = t.toolFields[toolFieldKey(tool.slug, field.name)];
        return (
          <Input
            key={field.name}
            type={field.type}
            label={fieldText.label}
            placeholder={'placeholder' in fieldText ? fieldText.placeholder : undefined}
            hint={'hint' in fieldText ? fieldText.hint : undefined}
            value={values[field.name] ?? ''}
            onChange={(event) => onChange(field.name, event.target.value)}
          />
        );
      })}
    </div>
  );
}
