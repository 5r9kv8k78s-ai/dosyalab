'use client';

import type { ReactNode } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

export function DialogContent({
  children,
  className,
  closeLabel,
}: {
  children: ReactNode;
  className?: string;
  /** Accessible name for the close button — required since it's icon-only. */
  closeLabel: string;
}) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="z-overlay data-[state=open]:animate-in data-[state=open]:fade-in data-[state=closed]:animate-out data-[state=closed]:fade-out fixed inset-0 bg-black/40" />
      <DialogPrimitive.Content
        className={cn(
          'z-modal border-border bg-surface fixed left-1/2 top-1/2 w-[calc(100vw-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border p-6 shadow-xl',
          'data-[state=open]:animate-in data-[state=open]:fade-in data-[state=open]:zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out data-[state=closed]:zoom-out-95',
          'max-h-[calc(100vh-2rem)] overflow-y-auto',
          className,
        )}
      >
        {children}
        <DialogPrimitive.Close
          className="focus-ring text-muted hover:text-foreground absolute right-4 top-4 rounded p-1"
          aria-label={closeLabel}
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DialogTitle({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <DialogPrimitive.Title
      className={cn('text-cardTitle text-foreground font-semibold', className)}
    >
      {children}
    </DialogPrimitive.Title>
  );
}

export function DialogDescription({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <DialogPrimitive.Description className={cn('text-small text-muted mt-1.5', className)}>
      {children}
    </DialogPrimitive.Description>
  );
}
