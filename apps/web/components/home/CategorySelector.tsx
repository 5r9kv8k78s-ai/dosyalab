'use client';

import { motion } from 'framer-motion';
import { FileTypeIcon, type FileType } from '@/components/icons/FileTypeIcon';
import { useTranslation } from '@/lib/i18n';
import { FILE_CATEGORIES } from '@/lib/tools';
import { cn } from '@/lib/utils';

export function CategorySelector({
  activeCategory,
  onSelect,
}: {
  activeCategory: FileType;
  onSelect: (category: FileType) => void;
}) {
  const { t } = useTranslation();

  return (
    <div
      role="radiogroup"
      aria-label={t.categories.sectionAriaLabel}
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
    >
      {FILE_CATEGORIES.map((category) => {
        const isActive = category === activeCategory;
        return (
          <motion.button
            key={category}
            type="button"
            role="radio"
            aria-checked={isActive}
            onClick={() => onSelect(category)}
            whileHover={{ scale: 1.02 }}
            transition={{ duration: 0.18 }}
            className={cn(
              'focus-ring bg-surface duration-base flex flex-col items-center gap-3 rounded-2xl border px-6 py-8 shadow-sm transition-shadow hover:shadow-lg',
              isActive ? 'border-primary ring-primary ring-1' : 'border-border',
            )}
          >
            <FileTypeIcon type={category} size={48} />
            <span className="text-cardTitle text-foreground font-semibold">
              {t.categories[category]}
            </span>
          </motion.button>
        );
      })}
    </div>
  );
}
