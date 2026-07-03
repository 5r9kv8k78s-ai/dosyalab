'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import {
  ApiError,
  downloadConversionResult,
  getConversionStatus,
  submitMergePdfConversion,
} from '@/lib/api';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Dropzone } from '@/components/ui/Dropzone';
import { Progress, StepDots } from '@/components/ui/Progress';
import { FileTypeIcon } from '@/components/icons/FileTypeIcon';

// Mirrors PdfToWordCard.tsx's stage machine and progress UX (same bands,
// same timers, same polling pattern) for the Merge PDF direction. Kept as a
// separate component rather than sharing code with the other cards so the
// existing conversion paths aren't touched.
//
// The one real difference from the other cards: merging needs the user to
// review and reorder the files before the job starts (the merge order
// determines page order in the output), so there's an extra "selecting"
// stage between picking files and submitting them.

const MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024;
const POLL_INTERVAL_MS = 800;
const ALLOWED_EXTENSIONS = ['.pdf'];

type Stage =
  | 'idle'
  | 'selecting'
  | 'uploading'
  | 'processing'
  | 'creating-document'
  | 'preparing-download'
  | 'completed'
  | 'error';

const IN_FLIGHT_STAGES: Stage[] = [
  'uploading',
  'processing',
  'creating-document',
  'preparing-download',
];

// Ordered for the stage dots indicator (selecting isn't a job stage, so it's
// excluded from this sequence).
const STAGE_SEQUENCE: Stage[] = [
  'uploading',
  'processing',
  'creating-document',
  'preparing-download',
  'completed',
];

// Bar fill target per stage, as a percent of the bar's width. These are
// narrative bands, not measurements — kept comfortably short of 100% until
// the job is actually done, so the bar never appears to finish early then
// freeze.
const STAGE_BAND_END: Record<Stage, number> = {
  idle: 0,
  selecting: 0,
  uploading: 20,
  processing: 45,
  'creating-document': 75,
  'preparing-download': 95,
  completed: 100,
  error: 0,
};

// How long to sit on "Processing" before the label advances to "Creating
// PDF". The backend doesn't expose a distinct signal for this hand-off, so
// it's a fixed narrative delay rather than a derived number — if the real
// job finishes first, the status poll short-circuits straight to
// "Preparing download" regardless of where this timer is.
const PROCESSING_TO_CREATING_DELAY_MS = 2500;

interface State {
  stage: Stage;
  files: File[];
  fileName: string | null;
  uploadProgress: number;
  resultFilename: string | null;
  errorMessage: string | null;
}

const initialState: State = {
  stage: 'idle',
  files: [],
  fileName: null,
  uploadProgress: 0,
  resultFilename: null,
  errorMessage: null,
};

function friendlyMessageFor(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return 'Something went wrong. Please try again.';
}

function stageLabel(state: State): string {
  switch (state.stage) {
    case 'uploading':
      return `Uploading ${state.files.length} PDFs…`;
    case 'processing':
      return 'Processing…';
    case 'creating-document':
      return 'Creating merged PDF…';
    case 'preparing-download':
      return 'Preparing your download…';
    default:
      return '';
  }
}

function barWidthFor(state: State): number {
  if (state.stage === 'uploading') {
    // Real, precise data — bytes actually sent — so it's fine to track it
    // exactly within the uploading band.
    return (state.uploadProgress / 100) * STAGE_BAND_END.uploading;
  }
  return STAGE_BAND_END[state.stage];
}

function moveFile(files: File[], index: number, direction: -1 | 1): File[] {
  const targetIndex = index + direction;
  if (targetIndex < 0 || targetIndex >= files.length) return files;
  const reordered = [...files];
  [reordered[index], reordered[targetIndex]] = [reordered[targetIndex], reordered[index]];
  return reordered;
}

export function MergePdfCard() {
  const [state, setState] = useState<State>(initialState);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stageAdvanceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  const clearTimers = useCallback(() => {
    if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    if (stageAdvanceTimeoutRef.current) clearTimeout(stageAdvanceTimeoutRef.current);
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      clearTimers();
    };
  }, [clearTimers]);

  const pollStatus = useCallback((jobId: string) => {
    getConversionStatus(jobId)
      .then(async (job) => {
        if (!isMountedRef.current) return;

        if (job.status === 'completed') {
          if (stageAdvanceTimeoutRef.current) clearTimeout(stageAdvanceTimeoutRef.current);
          setState((prev) => ({ ...prev, stage: 'preparing-download' }));
          try {
            await downloadConversionResult(jobId, job.filename);
            if (!isMountedRef.current) return;
            setState((prev) => ({ ...prev, stage: 'completed', resultFilename: job.filename }));
          } catch (error) {
            if (!isMountedRef.current) return;
            setState((prev) => ({
              ...prev,
              stage: 'error',
              errorMessage: friendlyMessageFor(error),
            }));
          }
          return;
        }

        if (job.status === 'failed') {
          if (stageAdvanceTimeoutRef.current) clearTimeout(stageAdvanceTimeoutRef.current);
          setState((prev) => ({
            ...prev,
            stage: 'error',
            errorMessage: job.error ?? 'Conversion failed. Please try a different file.',
          }));
          return;
        }

        pollTimeoutRef.current = setTimeout(() => pollStatus(jobId), POLL_INTERVAL_MS);
      })
      .catch((error) => {
        if (!isMountedRef.current) return;
        setState((prev) => ({ ...prev, stage: 'error', errorMessage: friendlyMessageFor(error) }));
      });
  }, []);

  const startConversion = useCallback(
    (files: File[]) => {
      clearTimers();
      setState((prev) => ({
        ...prev,
        stage: 'uploading',
        uploadProgress: 0,
      }));

      submitMergePdfConversion(files, (percent) => {
        setState((prev) =>
          prev.stage === 'uploading' ? { ...prev, uploadProgress: percent } : prev,
        );
      })
        .then((job) => {
          if (!isMountedRef.current) return;
          setState((prev) => ({ ...prev, stage: 'processing', uploadProgress: 100 }));

          stageAdvanceTimeoutRef.current = setTimeout(() => {
            setState((prev) =>
              prev.stage === 'processing' ? { ...prev, stage: 'creating-document' } : prev,
            );
          }, PROCESSING_TO_CREATING_DELAY_MS);

          pollStatus(job.job_id);
        })
        .catch((error) => {
          if (!isMountedRef.current) return;
          setState((prev) => ({
            ...prev,
            stage: 'error',
            errorMessage: friendlyMessageFor(error),
          }));
        });
    },
    [clearTimers, pollStatus],
  );

  const handleFiles = useCallback((fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList);

    const invalidFile = files.find(
      (file) => !ALLOWED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext)),
    );
    if (invalidFile) {
      setState({
        ...initialState,
        stage: 'error',
        errorMessage: 'Only PDF files are supported for this conversion.',
      });
      return;
    }
    const oversizedFile = files.find((file) => file.size > MAX_FILE_SIZE_BYTES);
    if (oversizedFile) {
      setState({
        ...initialState,
        stage: 'error',
        errorMessage: `${oversizedFile.name} is larger than the 100MB limit for Merge PDF.`,
      });
      return;
    }

    setState({ ...initialState, stage: 'selecting', files });
  }, []);

  const moveSelectedFile = useCallback((index: number, direction: -1 | 1) => {
    setState((prev) => ({ ...prev, files: moveFile(prev.files, index, direction) }));
  }, []);

  const isBusy = IN_FLIGHT_STAGES.includes(state.stage);

  return (
    <Card>
      <CardHeader>
        <FileTypeIcon type="pdf" size={40} />
        <div>
          <CardTitle as="h2">Merge PDF</CardTitle>
          <CardDescription>Combine multiple PDFs into one</CardDescription>
        </div>
      </CardHeader>

      <Dropzone
        accept="application/pdf,.pdf"
        multiple
        disabled={isBusy || state.stage === 'selecting'}
        onFiles={handleFiles}
        aria-label="Drop two or more PDFs here, or click to browse, to merge them"
      >
        {state.stage === 'idle' && (
          <>
            <p className="text-small text-foreground font-medium">
              Drop PDFs here, or click to browse
            </p>
            <p className="text-small text-muted mt-1">Two or more PDFs — up to 100MB each</p>
          </>
        )}

        {state.stage === 'selecting' && (
          <div
            className="w-full max-w-xs space-y-3"
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(event) => event.stopPropagation()}
          >
            <p className="text-small text-foreground font-medium">
              {state.files.length} PDFs selected — reorder if needed
            </p>
            <ul className="space-y-1.5">
              {state.files.map((file, index) => (
                <li
                  key={`${file.name}-${index}`}
                  className="border-border bg-background flex items-center gap-2 rounded-md border px-2 py-1.5"
                >
                  <span className="text-small text-foreground flex-1 truncate text-left">
                    {index + 1}. {file.name}
                  </span>
                  <button
                    type="button"
                    className="focus-ring rounded p-1 text-muted hover:text-foreground disabled:pointer-events-none disabled:opacity-30"
                    disabled={index === 0}
                    aria-label={`Move ${file.name} up`}
                    onClick={() => moveSelectedFile(index, -1)}
                  >
                    <ChevronUp className="h-4 w-4" aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    className="focus-ring rounded p-1 text-muted hover:text-foreground disabled:pointer-events-none disabled:opacity-30"
                    disabled={index === state.files.length - 1}
                    aria-label={`Move ${file.name} down`}
                    onClick={() => moveSelectedFile(index, 1)}
                  >
                    <ChevronDown className="h-4 w-4" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
            <div className="flex gap-2">
              <Button
                size="sm"
                disabled={state.files.length < 2}
                onClick={() => startConversion(state.files)}
              >
                Merge PDFs
              </Button>
              <Button variant="outline" size="sm" onClick={() => setState(initialState)}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        {isBusy && (
          <div className="w-full max-w-xs space-y-3" aria-live="polite">
            <p className="text-small text-foreground font-medium">{stageLabel(state)}</p>
            <Progress value={barWidthFor(state)} aria-label={stageLabel(state)} />
            <StepDots
              total={STAGE_SEQUENCE.length}
              currentIndex={STAGE_SEQUENCE.indexOf(state.stage)}
            />
          </div>
        )}

        {state.stage === 'completed' && (
          <div
            className="space-y-3"
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(event) => event.stopPropagation()}
          >
            <p className="text-small text-success font-medium">
              Merged — {state.resultFilename} downloaded
            </p>
            <Button size="sm" onClick={() => setState(initialState)}>
              Merge more files
            </Button>
          </div>
        )}

        {state.stage === 'error' && (
          <div
            className="w-full max-w-xs space-y-3"
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(event) => event.stopPropagation()}
          >
            <Alert variant="danger">{state.errorMessage}</Alert>
            <Button variant="outline" size="sm" onClick={() => setState(initialState)}>
              Try again
            </Button>
          </div>
        )}
      </Dropzone>
    </Card>
  );
}
