'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ApiError,
  downloadConversionResult,
  getConversionStatus,
  submitToolConversion,
} from '@/lib/api';
import { useTranslation, type Translations } from '@/lib/i18n';
import { toolFieldKey, type ToolConfig } from '@/lib/tools';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Dropzone } from '@/components/ui/Dropzone';
import { Input } from '@/components/ui/Input';
import { Progress, StepDots } from '@/components/ui/Progress';
import { FileTypeIcon } from '@/components/icons/FileTypeIcon';

// Generic, config-driven counterpart to the individual PdfToWordCard-style
// components: same stage machine, same progress bands, same polling pattern,
// but driven entirely by a `ToolConfig` (see lib/tools.ts) so every tool that
// needs no bespoke UI (i.e. everything except Merge PDF's reorder step) can
// share one implementation instead of seventeen near-identical files.
//
// Tools with extra form fields (rotation, page lists, passwords, ...) get an
// extra "ready" stage between picking a file and submitting, so required
// fields can be filled in first. Tools with no extra fields keep the old
// auto-start-on-drop behavior exactly.

const MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024;
const POLL_INTERVAL_MS = 800;

type Stage =
  | 'idle'
  | 'ready'
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

const STAGE_SEQUENCE: Stage[] = [
  'uploading',
  'processing',
  'creating-document',
  'preparing-download',
  'completed',
];

const STAGE_BAND_END: Record<Stage, number> = {
  idle: 0,
  ready: 0,
  uploading: 20,
  processing: 45,
  'creating-document': 75,
  'preparing-download': 95,
  completed: 100,
  error: 0,
};

const PROCESSING_TO_CREATING_DELAY_MS = 2500;

interface State {
  stage: Stage;
  files: File[];
  fieldValues: Record<string, string>;
  uploadProgress: number;
  resultFilename: string | null;
  errorMessage: string | null;
}

function initialFieldValues(tool: ToolConfig): Record<string, string> {
  return Object.fromEntries(tool.fields.map((field) => [field.name, field.defaultValue ?? '']));
}

function initialStateFor(tool: ToolConfig): State {
  return {
    stage: 'idle',
    files: [],
    fieldValues: initialFieldValues(tool),
    uploadProgress: 0,
    resultFilename: null,
    errorMessage: null,
  };
}

function friendlyMessageFor(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return fallback;
}

function stageLabel(state: State, tool: ToolConfig, t: Translations): string {
  const toolTitle = t.tools[tool.slug].title;
  switch (state.stage) {
    case 'uploading':
      return state.files.length > 1
        ? t.progress.filesUploading(state.files.length)
        : t.progress.fileUploading(state.files[0]?.name ?? '');
    case 'processing':
      return t.progress.processing;
    case 'creating-document':
      return t.progress.creatingTool(toolTitle);
    case 'preparing-download':
      return t.progress.preparing;
    default:
      return '';
  }
}

function barWidthFor(state: State): number {
  if (state.stage === 'uploading') {
    return (state.uploadProgress / 100) * STAGE_BAND_END.uploading;
  }
  return STAGE_BAND_END[state.stage];
}

function extensionsFromAccept(accept: string): string[] {
  return accept
    .split(',')
    .map((part) => part.trim())
    .filter((part) => part.startsWith('.'));
}

export function ToolCard({ tool }: { tool: ToolConfig }) {
  const { t } = useTranslation();
  const toolTitle = t.tools[tool.slug].title;
  const toolDescription = t.tools[tool.slug].description;

  const [state, setState] = useState<State>(() => initialStateFor(tool));
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

  const pollStatus = useCallback(
    (jobId: string) => {
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
                errorMessage: friendlyMessageFor(error, t.errors.somethingWrong),
              }));
            }
            return;
          }

          if (job.status === 'failed') {
            if (stageAdvanceTimeoutRef.current) clearTimeout(stageAdvanceTimeoutRef.current);
            setState((prev) => ({
              ...prev,
              stage: 'error',
              errorMessage: job.error ?? t.errors.conversionFailedTryDifferent,
            }));
            return;
          }

          pollTimeoutRef.current = setTimeout(() => pollStatus(jobId), POLL_INTERVAL_MS);
        })
        .catch((error) => {
          if (!isMountedRef.current) return;
          setState((prev) => ({
            ...prev,
            stage: 'error',
            errorMessage: friendlyMessageFor(error, t.errors.somethingWrong),
          }));
        });
    },
    [t.errors.conversionFailedTryDifferent, t.errors.somethingWrong],
  );

  const startConversion = useCallback(
    (files: File[], fieldValues: Record<string, string>) => {
      clearTimers();
      setState((prev) => ({ ...prev, stage: 'uploading', uploadProgress: 0 }));

      submitToolConversion(tool.slug, files, fieldValues, tool.multiple, (percent) => {
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
            errorMessage: friendlyMessageFor(error, t.errors.somethingWrong),
          }));
        });
    },
    [clearTimers, pollStatus, t.errors.somethingWrong, tool.multiple, tool.slug],
  );

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return;
      let files = Array.from(fileList);
      if (!tool.multiple) files = files.slice(0, 1);

      const allowedExtensions = extensionsFromAccept(tool.accept);
      const invalidFile = files.find(
        (file) => !allowedExtensions.some((ext) => file.name.toLowerCase().endsWith(ext)),
      );
      if (invalidFile) {
        setState({
          ...initialStateFor(tool),
          stage: 'error',
          errorMessage: t.errors.unsupportedFileTypeFor(invalidFile.name, toolTitle),
        });
        return;
      }
      const oversizedFile = files.find((file) => file.size > MAX_FILE_SIZE_BYTES);
      if (oversizedFile) {
        setState({
          ...initialStateFor(tool),
          stage: 'error',
          errorMessage: t.errors.fileTooLargeDetail(oversizedFile.name),
        });
        return;
      }

      const fieldValues = initialFieldValues(tool);
      if (tool.fields.length === 0) {
        setState({ ...initialStateFor(tool), files });
        startConversion(files, fieldValues);
      } else {
        setState({ ...initialStateFor(tool), stage: 'ready', files, fieldValues });
      }
    },
    [startConversion, t.errors, tool, toolTitle],
  );

  const updateField = useCallback((name: string, value: string) => {
    setState((prev) => ({ ...prev, fieldValues: { ...prev.fieldValues, [name]: value } }));
  }, []);

  const missingRequiredField = tool.fields.some(
    (field) => field.required && !state.fieldValues[field.name]?.trim(),
  );

  const isBusy = IN_FLIGHT_STAGES.includes(state.stage);

  return (
    <Card className="flex h-full flex-col">
      <CardHeader>
        <FileTypeIcon type={tool.fileType} size={40} />
        <div>
          <CardTitle as="h3">{toolTitle}</CardTitle>
          <CardDescription>{toolDescription}</CardDescription>
        </div>
      </CardHeader>

      <Dropzone
        accept={tool.accept}
        multiple={tool.multiple}
        disabled={isBusy || state.stage === 'ready'}
        onFiles={handleFiles}
        aria-label={t.upload.dropZoneAriaLabel(toolTitle)}
        className="flex-1"
      >
        {state.stage === 'idle' && (
          <p className="text-small text-foreground font-medium">{t.upload.dropHere}</p>
        )}

        {state.stage === 'ready' && (
          <div
            className="w-full max-w-xs space-y-3"
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(event) => event.stopPropagation()}
          >
            <p className="text-small text-foreground truncate font-medium">
              {state.files[0]?.name}
            </p>
            {tool.fields.map((field) => {
              const fieldText = t.toolFields[toolFieldKey(tool.slug, field.name)];
              return (
                <Input
                  key={field.name}
                  type={field.type}
                  label={fieldText.label}
                  placeholder={'placeholder' in fieldText ? fieldText.placeholder : undefined}
                  hint={'hint' in fieldText ? fieldText.hint : undefined}
                  value={state.fieldValues[field.name] ?? ''}
                  onChange={(event) => updateField(field.name, event.target.value)}
                />
              );
            })}
            <div className="flex gap-2">
              <Button
                size="sm"
                disabled={missingRequiredField}
                onClick={() => startConversion(state.files, state.fieldValues)}
              >
                {t.buttons.start}
              </Button>
              <Button variant="outline" size="sm" onClick={() => setState(initialStateFor(tool))}>
                {t.buttons.cancel}
              </Button>
            </div>
          </div>
        )}

        {isBusy && (
          <div className="w-full max-w-xs space-y-3" aria-live="polite">
            <p className="text-small text-foreground font-medium">{stageLabel(state, tool, t)}</p>
            <Progress value={barWidthFor(state)} aria-label={stageLabel(state, tool, t)} />
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
              {t.progress.doneDownloaded(state.resultFilename ?? '')}
            </p>
            <Button size="sm" onClick={() => setState(initialStateFor(tool))}>
              {t.buttons.convertAnotherFile}
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
            <Button variant="outline" size="sm" onClick={() => setState(initialStateFor(tool))}>
              {t.buttons.tryAgain}
            </Button>
          </div>
        )}
      </Dropzone>
    </Card>
  );
}
