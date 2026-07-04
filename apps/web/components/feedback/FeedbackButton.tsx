'use client';

import { useState } from 'react';
import { Lightbulb } from 'lucide-react';
import { Dialog, DialogTrigger } from '@/components/ui/Dialog';
import { useTranslation } from '@/lib/i18n';
import { FeedbackPanel } from './FeedbackPanel';

/**
 * The public "Bir fikrim var" entry point — a small fixed button, not a
 * loud FAB. Sits at z-[35] (between --z-sticky and --z-overlay, see
 * globals.css) so it never fights the header, but a Toast (z-toast: 60)
 * or the Dialog overlay (z-overlay: 40) it opens still correctly render
 * above it. Respects the safe-area inset so it clears the iOS Safari
 * home-indicator bar.
 */
export function FeedbackButton() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  // Bumped every time the dialog opens, so `<FeedbackPanel key={...} />`
  // remounts with fresh state instead of showing a stale success/error
  // screen from the previous submission.
  const [instanceKey, setInstanceKey] = useState(0);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (next) setInstanceKey((prev) => prev + 1);
        setOpen(next);
      }}
    >
      <DialogTrigger asChild>
        <button
          type="button"
          className="focus-ring border-border bg-surface text-foreground hover:border-primary hover:text-primary duration-base text-small fixed bottom-[max(1.25rem,env(safe-area-inset-bottom))] right-4 z-[35] inline-flex items-center gap-2 rounded-full border p-3.5 font-medium shadow-md transition-colors sm:right-5 sm:px-5 sm:py-3"
        >
          <Lightbulb className="text-primary h-4 w-4 shrink-0" aria-hidden="true" />
          <span className="hidden sm:inline">{t.feedback.buttonLabel}</span>
        </button>
      </DialogTrigger>
      <FeedbackPanel key={instanceKey} />
    </Dialog>
  );
}
