'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ApiError,
  downloadConversionResult,
  getConversionStatus,
  submitPdfToDocxConversion,
} from '@/lib/api';

const MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024;
const POLL_INTERVAL_MS = 800;

type Stage = 'idle' | 'uploading' | 'converting' | 'done' | 'error';

interface State {
  stage: Stage;
  fileName: string | null;
  uploadProgress: number;
  conversionProgress: number;
  resultFilename: string | null;
  errorMessage: string | null;
}

const initialState: State = {
  stage: 'idle',
  fileName: null,
  uploadProgress: 0,
  conversionProgress: 0,
  resultFilename: null,
  errorMessage: null,
};

function friendlyMessageFor(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return 'Something went wrong. Please try again.';
}

export function PdfToWordCard() {
  const [state, setState] = useState<State>(initialState);
  const [isDragActive, setIsDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  }, []);

  const pollStatus = useCallback((jobId: string) => {
    getConversionStatus(jobId)
      .then(async (job) => {
        if (!isMountedRef.current) return;

        if (job.status === 'completed') {
          setState((prev) => ({ ...prev, conversionProgress: 100 }));
          try {
            await downloadConversionResult(jobId, job.filename);
            if (!isMountedRef.current) return;
            setState((prev) => ({ ...prev, stage: 'done', resultFilename: job.filename }));
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
          setState((prev) => ({
            ...prev,
            stage: 'error',
            errorMessage: job.error ?? 'Conversion failed. Please try a different file.',
          }));
          return;
        }

        setState((prev) => ({ ...prev, conversionProgress: job.progress }));
        pollTimeoutRef.current = setTimeout(() => pollStatus(jobId), POLL_INTERVAL_MS);
      })
      .catch((error) => {
        if (!isMountedRef.current) return;
        setState((prev) => ({ ...prev, stage: 'error', errorMessage: friendlyMessageFor(error) }));
      });
  }, []);

  const startConversion = useCallback(
    (file: File) => {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setState({
          ...initialState,
          stage: 'error',
          errorMessage: 'Only PDF files are supported for this conversion.',
        });
        return;
      }
      if (file.size > MAX_FILE_SIZE_BYTES) {
        setState({
          ...initialState,
          stage: 'error',
          errorMessage: 'That file is larger than the 100MB limit for PDF → Word.',
        });
        return;
      }

      setState({
        ...initialState,
        stage: 'uploading',
        fileName: file.name,
      });

      submitPdfToDocxConversion(file, (percent) => {
        setState((prev) =>
          prev.stage === 'uploading' ? { ...prev, uploadProgress: percent } : prev,
        );
      })
        .then((job) => {
          if (!isMountedRef.current) return;
          setState((prev) => ({ ...prev, stage: 'converting', uploadProgress: 100 }));
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
    [pollStatus],
  );

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      const file = fileList?.[0];
      if (file) startConversion(file);
    },
    [startConversion],
  );

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsDragActive(false);
      if (state.stage === 'uploading' || state.stage === 'converting') return;
      handleFiles(event.dataTransfer.files);
    },
    [handleFiles, state.stage],
  );

  const isBusy = state.stage === 'uploading' || state.stage === 'converting';

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <span className="bg-brand-50 text-brand-600 flex h-10 w-10 items-center justify-center rounded-lg">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            className="h-5 w-5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5.586a1 1 0 0 1 .707.293l5.414 5.414a1 1 0 0 1 .293.707V19a2 2 0 0 1-2 2Z"
            />
          </svg>
        </span>
        <div>
          <h2 className="font-semibold text-gray-900">PDF → Word</h2>
          <p className="text-sm text-gray-400">Convert a PDF into an editable .docx file</p>
        </div>
      </div>

      <div
        onDrop={handleDrop}
        onDragOver={(e) => {
          e.preventDefault();
          if (!isBusy) setIsDragActive(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setIsDragActive(false);
        }}
        onClick={() => !isBusy && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (!isBusy && (e.key === 'Enter' || e.key === ' ')) inputRef.current?.click();
        }}
        className={`flex min-h-[160px] flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors ${
          isBusy ? 'cursor-default border-gray-200 bg-gray-50' : 'cursor-pointer'
        } ${
          isDragActive
            ? 'border-brand-500 bg-brand-50'
            : !isBusy
              ? 'hover:border-brand-400 hover:bg-brand-50/40 border-gray-300'
              : ''
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />

        {state.stage === 'idle' && (
          <>
            <p className="text-sm font-medium text-gray-700">Drop a PDF here, or click to browse</p>
            <p className="mt-1 text-xs text-gray-400">Up to 100MB</p>
          </>
        )}

        {state.stage === 'uploading' && (
          <ProgressBlock
            label={`Uploading ${state.fileName ?? 'file'}…`}
            percent={state.uploadProgress}
          />
        )}

        {state.stage === 'converting' && (
          <ProgressBlock
            label={`Converting ${state.fileName ?? 'file'}…`}
            percent={state.conversionProgress}
          />
        )}

        {state.stage === 'done' && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-green-600">
              Converted — {state.resultFilename} downloaded
            </p>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setState(initialState);
              }}
              className="bg-brand-600 hover:bg-brand-700 rounded-md px-3 py-1.5 text-xs font-medium text-white"
            >
              Convert another file
            </button>
          </div>
        )}

        {state.stage === 'error' && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-red-600">{state.errorMessage}</p>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setState(initialState);
              }}
              className="rounded-md bg-gray-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-gray-800"
            >
              Try again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function ProgressBlock({ label, percent }: { label: string; percent: number }) {
  return (
    <div className="w-full max-w-xs space-y-2">
      <p className="text-sm font-medium text-gray-700">{label}</p>
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
        <div
          className="bg-brand-500 h-full rounded-full transition-all duration-300"
          style={{ width: `${percent}%` }}
        />
      </div>
      <p className="text-xs text-gray-400">{percent}%</p>
    </div>
  );
}
