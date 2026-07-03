'use client';

import { motion } from 'framer-motion';
import { CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useTranslation } from '@/lib/i18n';

export function SuccessScreen({
  onDownloadAgain,
  onNewConversion,
}: {
  onDownloadAgain: () => void;
  onNewConversion: () => void;
}) {
  const { t } = useTranslation();

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="flex flex-col items-center gap-4 py-8 text-center"
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ duration: 0.35, ease: 'backOut', delay: 0.1 }}
      >
        <CheckCircle2 className="text-success h-16 w-16" aria-hidden="true" />
      </motion.div>

      <p className="text-cardTitle text-foreground font-semibold">{t.success.title}</p>

      <div className="mt-2 flex flex-wrap items-center justify-center gap-3">
        <Button onClick={onDownloadAgain}>{t.buttons.download}</Button>
        <Button variant="outline" onClick={onNewConversion}>
          {t.buttons.newConversion}
        </Button>
      </div>
    </motion.div>
  );
}
