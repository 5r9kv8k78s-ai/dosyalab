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
// A plain `fetch()` has no default timeout — on mobile, a network handoff
// (Wi-Fi/cellular) or a backgrounded tab can leave one poll request neither
// resolving nor rejecting, which (since the *next* poll was only ever
// scheduled from the previous one's `.then()`) silently freezes the entire
// polling chain forever. Every poll request gets its own hard timeout so
// that can never happen — see `pollStatus` below.
const POLL_REQUEST_TIMEOUT_MS = 10_000;
// A single timed-out or failed poll must not fail the whole conversion —
// only a run of consecutive failures does, so a transient blip (one missed
// beat) is invisible to the user and just retries on the same job_id.
const MAX_CONSECUTIVE_POLL_FAILURES = 3;
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
  const stateRef = useRef(state);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stageTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);
  // Kept outside React state deliberately — the backend deletes the output
  // file right after the first successful download, so a "download again"
  // click can't re-fetch it. Re-saving this already-in-memory blob (via
  // `redownload` below) sidesteps that without a second network request.
  const resultBlobRef = useRef<Blob | null>(null);

  // Polling recovery bookkeeping. `currentJobIdRef` and the failure counter
  // let a visibility/pageshow recovery (see below) resume the same job's
  // polling from wherever it was, instead of just resetting to an error.
  const currentJobIdRef = useRef<string | null>(null);
  const pollAbortControllerRef = useRef<AbortController | null>(null);
  const pollRequestTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const consecutiveFailuresRef = useRef(0);
  // Single-flight guard: a visibility/pageshow recovery firing at the same
  // moment as the regular POLL_INTERVAL_MS timer must never result in two
  // concurrent status requests for the same job.
  const isPollInFlightRef = useRef(false);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const clearPollRequestTimeout = useCallback(() => {
    if (pollRequestTimeoutRef.current) {
      clearTimeout(pollRequestTimeoutRef.current);
      pollRequestTimeoutRef.current = null;
    }
  }, []);

  // Aborts whichever poll request is currently in flight (if any) and
  // clears its timeout — used both on unmount and to force a clean restart
  // during visibility/pageshow recovery, so a request that's been silently
  // stuck since before the tab was backgrounded can't linger indefinitely.
  const abortActivePoll = useCallback(() => {
    clearPollRequestTimeout();
    if (pollAbortControllerRef.current) {
      pollAbortControllerRef.current.abort();
      pollAbortControllerRef.current = null;
    }
    isPollInFlightRef.current = false;
  }, [clearPollRequestTimeout]);

  const clearTimers = useCallback(() => {
    if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    if (stageTimeoutRef.current) clearTimeout(stageTimeoutRef.current);
    abortActivePoll();
  }, [abortActivePoll]);

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
      currentJobIdRef.current = jobId;
      if (isPollInFlightRef.current) return; // duplicate-poll guard
      isPollInFlightRef.current = true;

      const controller = new AbortController();
      pollAbortControllerRef.current = controller;
      pollRequestTimeoutRef.current = setTimeout(() => {
        controller.abort();
      }, POLL_REQUEST_TIMEOUT_MS);

      getConversionStatus(jobId, controller.signal)
        .then(async (job) => {
          clearPollRequestTimeout();
          isPollInFlightRef.current = false;
          if (!isMountedRef.current) return;
          consecutiveFailuresRef.current = 0;

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
        .catch((error) => {
          clearPollRequestTimeout();
          isPollInFlightRef.current = false;
          if (!isMountedRef.current) return;

          // An AbortError here is our own POLL_REQUEST_TIMEOUT_MS firing
          // (or a visibility-recovery restart aborting a stale request) —
          // never a user cancellation — so it's treated exactly like any
          // other transient polling failure: retried, not fatal on its own.
          consecutiveFailuresRef.current += 1;
          if (consecutiveFailuresRef.current > MAX_CONSECUTIVE_POLL_FAILURES) {
            fail(friendlyMessageFor(error, t.errors.somethingWrong));
            return;
          }
          pollTimeoutRef.current = setTimeout(() => pollStatus(jobId), POLL_INTERVAL_MS);
        });
    },
    [clearPollRequestTimeout, fail, t.errors.conversionFailedTryDifferent, t.errors.somethingWrong],
  );

  // Mobile Safari (and other mobile browsers) can throttle or fully suspend
  // timers while a tab is backgrounded — if the polling chain was stuck
  // mid-request when that happened, neither POLL_INTERVAL_MS nor
  // POLL_REQUEST_TIMEOUT_MS is guaranteed to fire until the tab is
  // foregrounded again. Once it is, this forces a clean restart regardless
  // of whatever ambiguous in-flight state polling was left in — it can
  // never do harm (a no-op if there's no active conversion) and is the
  // backstop for exactly the "stuck at 60% forever" failure mode.
  const restartPollingIfActive = useCallback(() => {
    const jobId = currentJobIdRef.current;
    if (!jobId) return;
    if (!IN_FLIGHT_STAGES.includes(stateRef.current.stage)) return;

    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
    abortActivePoll();
    pollStatus(jobId);
  }, [abortActivePoll, pollStatus]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') restartPollingIfActive();
    };
    const handlePageShow = (event: PageTransitionEvent) => {
      // `persisted` means this page came back from the back/forward cache
      // (bfcache) — its in-page JS state (including any pending timers)
      // may not have been running at all while cached.
      if (event.persisted) restartPollingIfActive();
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('pageshow', handlePageShow);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('pageshow', handlePageShow);
    };
  }, [restartPollingIfActive]);

  const start = useCallback(
    (files: File[], fieldValues: Record<string, string>) => {
      clearTimers();
      consecutiveFailuresRef.current = 0;
      currentJobIdRef.current = null;
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
    currentJobIdRef.current = null;
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
