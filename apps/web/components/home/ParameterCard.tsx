'use client';

import { motion } from 'framer-motion';
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
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className="border-border bg-surface mt-4 space-y-4 rounded-2xl border p-6 shadow-sm"
    >
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
    </motion.div>
  );
}
