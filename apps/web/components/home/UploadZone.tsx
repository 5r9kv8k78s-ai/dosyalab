'use client';

import { UploadCloud } from 'lucide-react';
import { Dropzone } from '@/components/ui/Dropzone';
import { useTranslation } from '@/lib/i18n';
import type { ToolConfig } from '@/lib/tools';

function supportedExtensionsLabel(accept: string): string {
  return accept
    .split(',')
    .map((part) => part.trim())
    .filter((part) => part.startsWith('.'))
    .map((ext) => ext.slice(1).toUpperCase())
    .filter((ext, index, all) => all.indexOf(ext) === index)
    .join(' • ');
}

export function UploadZone({
  tool,
  disabled,
  onFiles,
}: {
  tool: ToolConfig;
  disabled?: boolean;
  onFiles: (files: FileList | null) => void;
}) {
  const { t } = useTranslation();

  return (
    <Dropzone
      accept={tool.accept}
      multiple={tool.multiple}
      disabled={disabled}
      onFiles={onFiles}
      aria-label={t.upload.dropZoneAriaLabel(t.tools[tool.slug].title)}
      className="from-surface to-primary/5 hover:border-primary min-h-[220px] rounded-[28px] border-2 border-dashed bg-gradient-to-br transition-all duration-200 hover:scale-[1.01] hover:shadow-lg"
    >
      <UploadCloud className="text-primary mb-4 h-12 w-12" aria-hidden="true" />
      <p className="text-cardTitle text-foreground font-semibold">{t.upload.dropHere}</p>
      <p className="text-small text-muted mt-1">
        {t.upload.or} <span className="text-primary font-medium">{t.upload.chooseFile}</span>
      </p>
      <p className="text-small text-muted mt-4">{supportedExtensionsLabel(tool.accept)}</p>
      <p className="text-muted mt-1 text-xs">{t.upload.maxSizeLabel}</p>
    </Dropzone>
  );
}
