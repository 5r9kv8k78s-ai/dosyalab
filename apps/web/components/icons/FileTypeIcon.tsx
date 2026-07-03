'use client';

import { useTranslation } from '@/lib/i18n';
import { cn } from '@/lib/utils';

export type FileType = 'pdf' | 'word' | 'excel' | 'image';

const FILE_TYPE_STYLE: Record<FileType, { color: string; tint: string; label: string }> = {
  pdf: { color: '#EF4444', tint: '#FEF2F2', label: 'PDF' },
  word: { color: '#2563EB', tint: '#EFF6FF', label: 'DOC' },
  excel: { color: '#16A34A', tint: '#F0FDF4', label: 'XLS' },
  image: { color: '#9333EA', tint: '#FAF5FF', label: 'IMG' },
};

export interface FileTypeIconProps {
  type: FileType;
  size?: number;
  /** Shows the 3-letter type label on the folded corner tag. Best left off below ~32px. */
  label?: boolean;
  className?: string;
}

/**
 * Consistent colored file-type badge, built on the same folded-document
 * silhouette as the DosyaLab brand mark (see public/brand/logo.svg) so file
 * type icons and the logo read as one visual family.
 */
export function FileTypeIcon({ type, size = 40, label = true, className }: FileTypeIconProps) {
  const { t } = useTranslation();
  const style = FILE_TYPE_STYLE[type];

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label={`${style.label} ${t.common.file}`}
      className={cn(className)}
    >
      <path d="M23 6L31 14V34H9V6H23Z" fill={style.tint} stroke={style.color} strokeWidth="1.5" />
      <path
        d="M23 6L31 14H24C23.4477 14 23 13.5523 23 13V6Z"
        fill={style.color}
        fillOpacity="0.25"
      />
      <rect x="13" y="21" width="14" height="2" rx="1" fill={style.color} fillOpacity="0.5" />
      <rect x="13" y="26" width="14" height="2" rx="1" fill={style.color} fillOpacity="0.5" />
      {label && (
        <>
          <rect x="9" y="29" width="18" height="9" rx="2" fill={style.color} />
          <text
            x="18"
            y="35.5"
            textAnchor="middle"
            fontFamily="ui-sans-serif, system-ui, sans-serif"
            fontSize="6.5"
            fontWeight="700"
            fill="white"
          >
            {style.label}
          </text>
        </>
      )}
    </svg>
  );
}
