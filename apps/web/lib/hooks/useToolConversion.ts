'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ApiError,
  fetchConversionResultBlob,
  getConversionStatus,
  submitToolConversion,
} from '@/lib/api';
import { useTranslation } from '@/lib/i18n';
import type { ToolConfig } from '@/lib/tools';
import { triggerBrowserDownload } from '@/lib/utils';

// Drives the redesigned homepage's single upload flow. A fresh, from-scratch
// implementation (not a refactor of ToolCard.tsx's internal hook, which is
// left untouched) that mirrors the same proven approach — real byte-precise
// progress only for the upload itself, a short narrative delay for the
// "converting" label, and every stage after that driven by a real signal
// from the backend (job completion, then the actual download fetch) — never
// a faked precise percentage.

const POLL_INTERVAL_MS = 800;
const PROCESSING_TO_CONVERTING_DELAY_MS = 1600;

export type ConversionStage =
  | 'idle'
  | 'uploading'
  | 'processing'
  | 'converting'
  | 'preparing'
  | 'downloading'
  | 'completed'
  | 'error';

export const IN_FLIGHT_STAGES: ConversionStage[] = [
  'uploading',
  'processing',
  'converting',
  'preparing',
  'downloading',
];

export const STAGE_SEQUENCE: ConversionStage[] = [
  'uploading',
  'processing',
  'converting',
  'preparing',
  'downloading',
];

interface ConversionState {
  stage: ConversionStage;
  uploadProgress: number;
  resultFilename: string | null;
  resultFileSize: number | null;
  errorMessage: string | null;
}

const initialState: ConversionState = {
  stage: 'idle',
  uploadProgress: 0,
  resultFilename: null,
  resultFileSize: null,
  errorMessage: null,
};

function friendlyMessageFor(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message;
  return fallback;
}

export function useToolConversion(tool: ToolConfig) {
  const { t } = useTranslation();
  const [state, setState] = useState<ConversionState>(initialState);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stageTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);
  // Kept outside React state deliberately — the backend deletes the output
  // file right after the first successful download, so a "download again"
  // click can't re-fetch it. Re-saving this already-in-memory blob (via
  // `redownload` below) sidesteps that without a second network request.
  const resultBlobRef = useRef<Blob | null>(null);

  const clearTimers = useCallback(() => {
    if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    if (stageTimeoutRef.current) clearTimeout(stageTimeoutRef.current);
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      clearTimers();
    };
  }, [clearTimers]);

  const fail = useCallback((errorMessage: string) => {
    if (!isMountedRef.current) return;
    setState((prev) => ({ ...prev, stage: 'error', errorMessage }));
  }, []);

  const pollStatus = useCallback(
    (jobId: string) => {
      getConversionStatus(jobId)
        .then(async (job) => {
          if (!isMountedRef.current) return;

          if (job.status === 'completed') {
            if (stageTimeoutRef.current) clearTimeout(stageTimeoutRef.current);
            setState((prev) => ({ ...prev, stage: 'preparing' }));
            setState((prev) => ({ ...prev, stage: 'downloading' }));
            try {
              const blob = await fetchConversionResultBlob(jobId);
              if (!isMountedRef.current) return;
              resultBlobRef.current = blob;
              triggerBrowserDownload(blob, job.filename);
              setState((prev) => ({
                ...prev,
                stage: 'completed',
                resultFilename: job.filename,
                resultFileSize: blob.size,
              }));
            } catch (error) {
              fail(friendlyMessageFor(error, t.errors.somethingWrong));
            }
            return;
          }

          if (job.status === 'failed') {
            if (stageTimeoutRef.current) clearTimeout(stageTimeoutRef.current);
            fail(job.error ?? t.errors.conversionFailedTryDifferent);
            return;
          }

          pollTimeoutRef.current = setTimeout(() => pollStatus(jobId), POLL_INTERVAL_MS);
        })
        .catch((error) => fail(friendlyMessageFor(error, t.errors.somethingWrong)));
    },
    [fail, t.errors.conversionFailedTryDifferent, t.errors.somethingWrong],
  );

  const start = useCallback(
    (files: File[], fieldValues: Record<string, string>) => {
      clearTimers();
      resultBlobRef.current = null;
      setState({ ...initialState, stage: 'uploading' });

      submitToolConversion(tool.slug, files, fieldValues, tool.multiple, (percent) => {
        setState((prev) =>
          prev.stage === 'uploading' ? { ...prev, uploadProgress: percent } : prev,
        );
      })
        .then((job) => {
          if (!isMountedRef.current) return;
          setState((prev) => ({ ...prev, stage: 'processing', uploadProgress: 100 }));

          stageTimeoutRef.current = setTimeout(() => {
            setState((prev) =>
              prev.stage === 'processing' ? { ...prev, stage: 'converting' } : prev,
            );
          }, PROCESSING_TO_CONVERTING_DELAY_MS);

          pollStatus(job.job_id);
        })
        .catch((error) => fail(friendlyMessageFor(error, t.errors.somethingWrong)));
    },
    [clearTimers, fail, pollStatus, t.errors.somethingWrong, tool.multiple, tool.slug],
  );

  const reset = useCallback(() => {
    clearTimers();
    resultBlobRef.current = null;
    setState(initialState);
  }, [clearTimers]);

  const redownload = useCallback(() => {
    if (resultBlobRef.current && state.resultFilename) {
      triggerBrowserDownload(resultBlobRef.current, state.resultFilename);
    }
  }, [state.resultFilename]);

  return { state, start, reset, redownload };
}
