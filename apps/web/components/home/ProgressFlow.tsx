'use client';

import { motion } from 'framer-motion';
import { useTranslation } from '@/lib/i18n';
import { STAGE_SEQUENCE, type ConversionStage } from '@/lib/hooks/useToolConversion';
import { cn } from '@/lib/utils';

const STAGE_BAND_END: Record<ConversionStage, number> = {
  idle: 0,
  uploading: 20,
  processing: 40,
  converting: 60,
  preparing: 80,
  downloading: 95,
  completed: 100,
  error: 0,
};

export function ProgressFlow({
  stage,
  uploadProgress,
}: {
  stage: ConversionStage;
  uploadProgress: number;
}) {
  const { t } = useTranslation();

  const barWidth =
    stage === 'uploading'
      ? (uploadProgress / 100) * STAGE_BAND_END.uploading
      : STAGE_BAND_END[stage];

  const stepLabels: Record<ConversionStage, string> = {
    idle: '',
    uploading: t.progress.uploading,
    processing: t.progress.processing,
    converting: t.progress.converting,
    preparing: t.progress.preparing,
    downloading: t.progress.downloading,
    completed: t.progress.completed,
    error: '',
  };

  const currentIndex = STAGE_SEQUENCE.indexOf(stage);

  return (
    <div className="w-full" aria-live="polite">
      <div className="bg-border h-2 w-full overflow-hidden rounded-full">
        <motion.div
          className="bg-primary h-full rounded-full"
          animate={{ width: `${barWidth}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
        {STAGE_SEQUENCE.map((step, index) => {
          const isActive = index === currentIndex;
          const isDone = index < currentIndex;
          return (
            <span
              key={step}
              className={cn(
                'text-small duration-base font-medium transition-colors',
                isActive && 'text-primary',
                isDone && 'text-success',
                !isActive && !isDone && 'text-muted',
              )}
            >
              {stepLabels[step]}
            </span>
          );
        })}
      </div>
    </div>
  );
}
