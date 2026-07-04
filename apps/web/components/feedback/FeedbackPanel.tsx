'use client';

import { useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { DialogClose, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { ApiError, submitFeedback } from '@/lib/api';
import { useTranslation } from '@/lib/i18n';
import { cn } from '@/lib/utils';

// Mirrors the backend's MESSAGE_MIN_LENGTH/MAX_LENGTH (see
// apps/api/app/services/feedback.py) — the server remains authoritative;
// this only gives immediate, friendly feedback before a round trip.
const MESSAGE_MIN_LENGTH = 10;
const MESSAGE_MAX_LENGTH = 2000;

type FeedbackCategory = 'idea' | 'suggestion' | 'problem' | 'other';
const CATEGORIES: FeedbackCategory[] = ['idea', 'suggestion', 'problem', 'other'];

type PanelStage = 'form' | 'submitting' | 'success';

export function FeedbackPanel() {
  const { t } = useTranslation();
  const [stage, setStage] = useState<PanelStage>('form');
  const [category, setCategory] = useState<FeedbackCategory>('idea');
  const [message, setMessage] = useState('');
  const [email, setEmail] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const trimmedLength = message.trim().length;
  const isTooShort = trimmedLength > 0 && trimmedLength < MESSAGE_MIN_LENGTH;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const trimmedMessage = message.trim();
    if (trimmedMessage.length < MESSAGE_MIN_LENGTH) {
      setErrorMessage(t.feedback.errorMessageTooShort);
      return;
    }

    setStage('submitting');
    setErrorMessage(null);
    try {
      await submitFeedback({
        category,
        message: trimmedMessage,
        email: email.trim() || undefined,
      });
      setStage('success');
    } catch (error) {
      setStage('form');
      if (error instanceof ApiError && error.status === 429) {
        setErrorMessage(t.feedback.errorRateLimited);
      } else {
        setErrorMessage(t.feedback.errorGeneric);
      }
    }
  };

  if (stage === 'success') {
    return (
      <DialogContent closeLabel={t.feedback.closeAriaLabel}>
        <div className="flex flex-col items-center gap-3 py-4 text-center">
          <CheckCircle2 className="text-primary h-10 w-10" aria-hidden="true" />
          <p className="text-cardTitle text-foreground font-semibold">{t.feedback.successTitle}</p>
          <p className="text-small text-muted">{t.feedback.successBody}</p>
          <DialogClose asChild>
            <Button variant="outline" size="sm">
              {t.feedback.closeButton}
            </Button>
          </DialogClose>
        </div>
      </DialogContent>
    );
  }

  return (
    <DialogContent closeLabel={t.feedback.closeAriaLabel}>
      <DialogTitle>{t.feedback.title}</DialogTitle>
      <DialogDescription>{t.feedback.description}</DialogDescription>

      <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
        <div>
          <span className="text-small text-foreground font-medium">{t.feedback.categoryLabel}</span>
          <div
            role="radiogroup"
            aria-label={t.feedback.categoryLabel}
            className="mt-2 grid grid-cols-2 gap-2"
          >
            {CATEGORIES.map((option) => {
              const isActive = option === category;
              return (
                <button
                  key={option}
                  type="button"
                  role="radio"
                  aria-checked={isActive}
                  onClick={() => setCategory(option)}
                  className={cn(
                    'focus-ring duration-base text-small rounded-lg border px-3 py-2 font-medium transition-colors',
                    isActive
                      ? 'border-primary bg-primary/[0.08] text-primary'
                      : 'border-border bg-surface text-foreground',
                  )}
                >
                  {t.feedback.categories[option]}
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <Textarea
            label={t.feedback.messageLabel}
            value={message}
            onChange={(event) => setMessage(event.target.value.slice(0, MESSAGE_MAX_LENGTH))}
            rows={4}
            maxLength={MESSAGE_MAX_LENGTH}
            error={isTooShort ? t.feedback.errorMessageTooShort : undefined}
            required
          />
          <p className="text-muted mt-1 text-right text-xs">
            {t.feedback.messageCounter(message.length, MESSAGE_MAX_LENGTH)}
          </p>
        </div>

        <Input
          type="email"
          label={t.feedback.emailLabel}
          hint={t.feedback.emailHint}
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />

        {errorMessage && <Alert variant="danger">{errorMessage}</Alert>}

        <Button
          type="submit"
          size="lg"
          className="w-full"
          disabled={stage === 'submitting' || trimmedLength < MESSAGE_MIN_LENGTH}
          loading={stage === 'submitting'}
        >
          {stage === 'submitting' ? t.feedback.submitting : t.feedback.submit}
        </Button>
      </form>
    </DialogContent>
  );
}
