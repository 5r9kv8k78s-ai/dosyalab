'use client';

import { useCallback, useState } from 'react';
import { PdfWorkspace } from '@/components/pdf-workspace/PdfWorkspace';
import { FileTypeIcon, type FileType } from '@/components/icons/FileTypeIcon';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { useTranslation } from '@/lib/i18n';
import { useToolConversion } from '@/lib/hooks/useToolConversion';
import { getPdfWorkspaceMode } from '@/lib/pdf/workspaceMode';
import {
  GENERIC_UPLOAD_ACCEPT,
  inferFileType,
  toolsByFileType,
  type ToolConfig,
} from '@/lib/tools';
import { ParameterCard } from './ParameterCard';
import { ProgressFlow } from './ProgressFlow';
import { SelectedFilesList } from './SelectedFilesList';
import { SuccessScreen } from './SuccessScreen';
import { ToolCards } from './ToolCards';
import { UploadZone } from './UploadZone';

const MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024;
// `useToolConversion` always needs a ToolConfig — this stands in only while
// no tool is selected yet (before a file is dropped, `start()` is never
// reachable from the UI, so its slug/multiple are never actually used).
const FALLBACK_TOOL = toolsByFileType('pdf')[0];

function extensionsFromAccept(accept: string): string[] {
  return accept
    .split(',')
    .map((part) => part.trim())
    .filter((part) => part.startsWith('.'));
}

function initialFieldValues(tool: ToolConfig): Record<string, string> {
  return Object.fromEntries(tool.fields.map((field) => [field.name, field.defaultValue ?? '']));
}

function moveItem<T>(items: T[], index: number, direction: -1 | 1): T[] {
  const target = index + direction;
  if (target < 0 || target >= items.length) return items;
  const next = [...items];
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

/** Narrows a raw dropped batch down to what a given tool can actually use —
 * matching extensions only, and a single file unless the tool allows more. */
function filesForTool(candidates: File[], tool: ToolConfig): File[] {
  const allowedExtensions = extensionsFromAccept(tool.accept);
  const matching = candidates.filter((file) =>
    allowedExtensions.some((ext) => file.name.toLowerCase().endsWith(ext)),
  );
  return tool.multiple ? matching : matching.slice(0, 1);
}

export function ConversionFlow() {
  const { t } = useTranslation();

  const [category, setCategory] = useState<FileType | null>(null);
  const [selectedTool, setSelectedTool] = useState<ToolConfig | null>(null);
  const [rawFiles, setRawFiles] = useState<File[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [pickError, setPickError] = useState<string | null>(null);

  const { state, start, reset, redownload } = useToolConversion(selectedTool ?? FALLBACK_TOOL);

  const validateAgainst = useCallback(
    (candidates: File[], tool: ToolConfig): string | null => {
      const allowedExtensions = extensionsFromAccept(tool.accept);
      const invalidFile = candidates.find(
        (file) => !allowedExtensions.some((ext) => file.name.toLowerCase().endsWith(ext)),
      );
      if (invalidFile) {
        return t.errors.unsupportedFileTypeFor(invalidFile.name, t.tools[tool.slug].title);
      }
      const oversizedFile = candidates.find((file) => file.size > MAX_FILE_SIZE_BYTES);
      if (oversizedFile) return t.errors.fileTooLargeDetail(oversizedFile.name);
      return null;
    },
    [t.errors, t.tools],
  );

  const handleToolSelect = useCallback(
    (tool: ToolConfig) => {
      setSelectedTool(tool);
      setFieldValues(initialFieldValues(tool));
      setFiles(filesForTool(rawFiles, tool));
      setPickError(null);
      reset();
    },
    [rawFiles, reset],
  );

  const handleInitialFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return;
      const picked = Array.from(fileList);
      const detected = inferFileType(picked[0].name);
      if (!detected) {
        setPickError(t.errors.invalidFileType);
        return;
      }

      const tool = toolsByFileType(detected)[0] as ToolConfig | undefined;
      if (tool) {
        const error = validateAgainst(picked, tool);
        if (error) {
          setPickError(error);
          return;
        }
      }

      setPickError(null);
      setCategory(detected);
      setRawFiles(picked);
      setSelectedTool(tool ?? null);
      setFieldValues(tool ? initialFieldValues(tool) : {});
      setFiles(tool ? filesForTool(picked, tool) : []);
    },
    [t.errors, validateAgainst],
  );

  const handleAddMoreFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || !selectedTool) return;
      const picked = Array.from(fileList);
      const error = validateAgainst(picked, selectedTool);
      if (error) {
        setPickError(error);
        return;
      }
      setPickError(null);
      setRawFiles((prev) => [...prev, ...picked]);
      setFiles((prev) => [...prev, ...picked]);
    },
    [selectedTool, validateAgainst],
  );

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const moveFile = useCallback((index: number, direction: -1 | 1) => {
    setFiles((prev) => moveItem(prev, index, direction));
  }, []);

  const updateField = useCallback((name: string, value: string) => {
    setFieldValues((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleStart = useCallback(() => {
    start(files, fieldValues);
  }, [fieldValues, files, start]);

  const handleWorkspaceConfirm = useCallback(
    (values: Record<string, string>) => {
      setFieldValues(values);
      start(files, values);
    },
    [files, start],
  );

  const handleWorkspaceBack = useCallback(() => {
    setSelectedTool(null);
  }, []);

  const handleReset = useCallback(() => {
    setCategory(null);
    setSelectedTool(null);
    setRawFiles([]);
    setFiles([]);
    setFieldValues({});
    setPickError(null);
    reset();
  }, [reset]);

  const handleTryAgain = useCallback(() => {
    setFiles([]);
    setPickError(null);
    reset();
  }, [reset]);

  const categoryTools = category ? toolsByFileType(category) : [];
  const workspaceMode = selectedTool ? getPdfWorkspaceMode(selectedTool.slug) : null;
  const missingRequiredField =
    selectedTool?.fields.some((field) => field.required && !fieldValues[field.name]?.trim()) ??
    false;
  const minFiles = selectedTool ? (selectedTool.multiple ? (selectedTool.minFiles ?? 1) : 1) : 1;
  const canStart = !!selectedTool && files.length >= minFiles && !missingRequiredField;
  const needsMoreFiles = !!selectedTool?.multiple && files.length < minFiles;
  const isIdle = state.stage === 'idle';
  const isBusy = !isIdle && state.stage !== 'error' && state.stage !== 'completed';

  return (
    <section id="tools" className="mx-auto w-full max-w-[1200px] px-5 pb-16 sm:px-6">
      {isIdle && (
        <div className="mx-auto max-w-xl">
          <UploadZone
            accept={GENERIC_UPLOAD_ACCEPT}
            multiple
            ariaLabel={t.upload.genericDropZoneAriaLabel}
            subtitleLine={t.upload.genericSupportedTypesLine}
            onFiles={handleInitialFiles}
          />

          {pickError && (
            <Alert variant="danger" className="mt-4">
              {pickError}
            </Alert>
          )}
        </div>
      )}

      {isIdle && category && (
        <div className="animate-fade-in-up mx-auto mt-8 w-full max-w-2xl">
          <div className="border-border bg-surface min-w-0 rounded-2xl border p-4">
            <div className="flex min-w-0 items-center gap-3">
              <FileTypeIcon type={category} size={32} className="shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-small text-foreground truncate font-medium">
                  {rawFiles[0]?.name}
                </p>
                <p className="text-muted hidden text-xs sm:block">{t.categories[category]}</p>
              </div>
              <button
                type="button"
                className="focus-ring text-small text-muted hover:text-foreground hidden shrink-0 rounded font-medium sm:block"
                onClick={handleReset}
              >
                {t.upload.pickDifferentFile}
              </button>
            </div>

            <div className="mt-2 flex items-center justify-between gap-3 sm:hidden">
              <p className="text-muted truncate text-xs">{t.categories[category]}</p>
              <button
                type="button"
                className="focus-ring text-small text-muted hover:text-foreground shrink-0 rounded font-medium"
                onClick={handleReset}
              >
                {t.upload.pickDifferentFile}
              </button>
            </div>
          </div>

          {categoryTools.length === 0 ? (
            <p className="text-small text-muted mt-6 text-center">{t.categories.emptyState}</p>
          ) : workspaceMode && files[0] ? (
            <div className="mt-8">
              <PdfWorkspace
                file={files[0]}
                mode={workspaceMode}
                onBack={handleWorkspaceBack}
                onConfirm={handleWorkspaceConfirm}
              />
            </div>
          ) : (
            <>
              <h2 className="text-foreground sm:text-h3 mt-8 text-center text-[30px] font-semibold leading-[1.1]">
                {t.upload.chooseActionHeading}
              </h2>
              <div className="mt-4">
                <ToolCards
                  tools={categoryTools}
                  selectedSlug={selectedTool?.slug ?? null}
                  onSelect={handleToolSelect}
                />
              </div>

              {selectedTool && (
                <div className="mx-auto mt-6 max-w-xl">
                  <SelectedFilesList
                    files={files}
                    reorderable={selectedTool.multiple && files.length > 1}
                    onRemove={removeFile}
                    onMove={moveFile}
                  />

                  {needsMoreFiles && (
                    <div className="mt-4">
                      <UploadZone
                        accept={selectedTool.accept}
                        multiple
                        compact
                        ariaLabel={t.upload.mergeDropZoneAriaLabel}
                        subtitleLine={t.upload.mergeHint}
                        onFiles={handleAddMoreFiles}
                      />
                    </div>
                  )}

                  <ParameterCard tool={selectedTool} values={fieldValues} onChange={updateField} />

                  <div className="mt-4 flex justify-center">
                    <Button size="lg" disabled={!canStart} onClick={handleStart}>
                      {t.buttons.start}
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {isBusy && (
        <div className="border-border bg-surface animate-fade-in-up rounded-upload mx-auto mt-8 max-w-xl border px-8 py-12">
          <ProgressFlow stage={state.stage} uploadProgress={state.uploadProgress} />
        </div>
      )}

      {state.stage === 'completed' && (
        <div className="border-border bg-surface animate-fade-in-up rounded-upload mx-auto mt-8 max-w-xl border px-8">
          <SuccessScreen
            filename={state.resultFilename}
            fileSize={state.resultFileSize}
            onDownloadAgain={redownload}
            onNewConversion={handleReset}
          />
        </div>
      )}

      {state.stage === 'error' && (
        <div className="border-border bg-surface animate-fade-in-up rounded-upload mx-auto mt-8 max-w-xl space-y-4 border px-8 py-12 text-center">
          <Alert variant="danger">{state.errorMessage}</Alert>
          <Button variant="outline" onClick={handleTryAgain}>
            {t.buttons.tryAgain}
          </Button>
        </div>
      )}
    </section>
  );
}
