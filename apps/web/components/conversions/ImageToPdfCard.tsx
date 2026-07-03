'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ApiError,
  downloadConversionResult,
  getConversionStatus,
  submitImagesToPdfConversion,
} from '@/lib/api';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Dropzone } from '@/components/ui/Dropzone';
import { Progress, StepDots } from '@/components/ui/Progress';
import { FileTypeIcon } from '@/components/icons/FileTypeIcon';

// Mirrors PdfToWordCard.tsx's stage machine and progress UX (same bands,
// same timers, same polling pattern) for the Image → PDF direction. Kept as
// a separate component rather than sharing code with the other cards so the
// existing PDF → Word, Word → PDF, and PDF → Excel paths aren't touched.
//
// The one real difference from the other cards: this accepts *multiple*
// files (one PDF page per image, combined into a single download), so
// `startConversion`/`handleFiles` work with a File[] instead of a single
// File, and the Dropzone below is given `multiple`.

const MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024;
const POLL_INTERVAL_MS = 800;
const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp'];

// The backend has no real per-page progress signal for the conversion
// itself (see apps/api/app/modules/converter/images_to_pdf.py) — only
// upload has a true byte-level percentage. So conversion is represented as
// named stages with a bar that animates smoothly and continuously, never as
// a faked precise number.
type Stage =
  | 'idle'
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

// Ordered for the stage dots indicator.
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
  fileName: string | null;
  uploadProgress: number;
  resultFilename: string | null;
  errorMessage: string | null;
}

const initialState: State = {
  stage: 'idle',
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
  const name = state.fileName ?? 'file';
  switch (state.stage) {
    case 'uploading':
      return `Uploading ${name}…`;
    case 'processing':
      return `Processing ${name}…`;
    case 'creating-document':
      return 'Creating PDF…';
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

function summarizeFileNames(files: File[]): string {
  if (files.length === 1) return files[0].name;
  return `${files.length} images`;
}

export function ImageToPdfCard() {
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
      const invalidFile = files.find(
        (file) => !ALLOWED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext)),
      );
      if (invalidFile) {
        setState({
          ...initialState,
          stage: 'error',
          errorMessage: 'Only JPG, JPEG, PNG, and WEBP files are supported for this conversion.',
        });
        return;
      }
      const oversizedFile = files.find((file) => file.size > MAX_FILE_SIZE_BYTES);
      if (oversizedFile) {
        setState({
          ...initialState,
          stage: 'error',
          errorMessage: `${oversizedFile.name} is larger than the 100MB limit for Image → PDF.`,
        });
        return;
      }

      clearTimers();
      setState({
        ...initialState,
        stage: 'uploading',
        fileName: summarizeFileNames(files),
      });

      submitImagesToPdfConversion(files, (percent) => {
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

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return;
      startConversion(Array.from(fileList));
    },
    [startConversion],
  );

  const isBusy = IN_FLIGHT_STAGES.includes(state.stage);

  return (
    <Card>
      <CardHeader>
        <FileTypeIcon type="image" size={40} />
        <div>
          <CardTitle as="h2">Image → PDF</CardTitle>
          <CardDescription>Combine images into a single PDF</CardDescription>
        </div>
      </CardHeader>

      <Dropzone
        accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
        multiple
        disabled={isBusy}
        onFiles={handleFiles}
        aria-label="Drop one or more images here, or click to browse, to convert them to PDF"
      >
        {state.stage === 'idle' && (
          <>
            <p className="text-small text-foreground font-medium">
              Drop images here, or click to browse
            </p>
            <p className="text-small text-muted mt-1">JPG, PNG, or WEBP — up to 100MB each</p>
          </>
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
              Converted — {state.resultFilename} downloaded
            </p>
            <Button size="sm" onClick={() => setState(initialState)}>
              Convert another file
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
