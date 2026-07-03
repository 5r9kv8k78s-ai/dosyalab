'use client';

import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
import * as ToastPrimitive from '@radix-ui/react-toast';
import { CheckCircle2, Info, X, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

type ToastVariant = 'success' | 'danger' | 'info';

interface ToastItem {
  id: number;
  title: string;
  description?: string;
  variant: ToastVariant;
}

interface ToastInput {
  title: string;
  description?: string;
  variant?: ToastVariant;
}

interface ToastContextValue {
  toast: (input: ToastInput) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within a ToastProvider');
  return ctx;
}

const iconByVariant = { success: CheckCircle2, danger: XCircle, info: Info } as const;
const classByVariant = {
  success: 'border-success/30 bg-success-bg text-success',
  danger: 'border-danger/30 bg-danger-bg text-danger',
  info: 'border-primary/30 bg-primary-light text-primary',
} as const;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const toast = useCallback((input: ToastInput) => {
    setItems((prev) => [...prev, { id: Date.now() + Math.random(), variant: 'info', ...input }]);
  }, []);

  const dismiss = useCallback((id: number) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      <ToastPrimitive.Provider swipeDirection="right">
        {children}
        {items.map((item) => {
          const Icon = iconByVariant[item.variant];
          return (
            <ToastPrimitive.Root
              key={item.id}
              duration={5000}
              onOpenChange={(open) => {
                if (!open) dismiss(item.id);
              }}
              className={cn(
                'data-[state=open]:animate-in data-[state=open]:slide-in-from-bottom-2 data-[state=closed]:animate-out data-[state=closed]:fade-out data-[swipe=end]:animate-out flex items-start gap-3 rounded-lg border p-4 shadow-lg',
                classByVariant[item.variant],
              )}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <div className="text-small text-foreground flex-1">
                <ToastPrimitive.Title className="font-medium">{item.title}</ToastPrimitive.Title>
                {item.description && (
                  <ToastPrimitive.Description className="text-muted mt-0.5">
                    {item.description}
                  </ToastPrimitive.Description>
                )}
              </div>
              <ToastPrimitive.Close
                className="focus-ring shrink-0 rounded p-0.5"
                aria-label="Dismiss"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </ToastPrimitive.Close>
            </ToastPrimitive.Root>
          );
        })}
        <ToastPrimitive.Viewport className="z-toast fixed bottom-0 right-0 flex w-full max-w-sm flex-col gap-2 p-4 outline-none" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}
