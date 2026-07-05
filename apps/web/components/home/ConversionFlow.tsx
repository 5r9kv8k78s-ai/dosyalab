'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { PdfWorkspace } from '@/components/pdf-workspace/PdfWorkspace';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { useTranslation } from '@/lib/i18n';
import { useToolConversion } from '@/lib/hooks/useToolConversion';
import { getPdfWorkspaceMode } from '@/lib/pdf/workspaceMode';
import { analyzeFileSet } from '@/lib/files/analyzeFileSet';
import { MAX_FILE_SIZE_BYTES } from '@/lib/files/validateFilesForTool';
import {
  GENERIC_UPLOAD_ACCEPT,
  TOOLS,
  inferFileType,
  toolsByFileType,
  type ToolConfig,
  type ToolSlug,
} from '@/lib/tools';
import { FileBatchSummary } from './FileBatchSummary';
import { ParameterCard } from './ParameterCard';
import { ProgressFlow } from './ProgressFlow';
import { SuccessScreen } from './SuccessScreen';
import { ToolCards } from './ToolCards';
import { UploadZone } from './UploadZone';

// `useToolConversion` always needs a ToolConfig — this stands in only while
// no tool is selected yet (before a file is dropped, `start()` is never
// reachable from the UI, so its slug/multiple are never actually used).
const FALLBACK_TOOL = toolsByFileType('pdf')[0];

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

function toolBySlug(slug: ToolSlug | null): ToolConfig | null {
  if (!slug) return null;
  return TOOLS.find((tool) => tool.slug === slug) ?? null;
}

export function ConversionFlow() {
  const { t } = useTranslation();

  // The whole dropped/added batch — always analyzed in full (never just
  // files[0]) by `analyzeFileSet`, which is the single source of truth for
  // which tools are compatible with it. See lib/files/analyzeFileSet.ts.
  const [files, setFiles] = useState<File[]>([]);
  const [manualToolSlug, setManualToolSlug] = useState<ToolSlug | null>(null);
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [addFileNotice, setAddFileNotice] = useState<string | null>(null);

  const analysis = useMemo(() => analyzeFileSet(files), [files]);

  // The active tool is derived, not stored directly: a user's manual pick
  // (clicking a different ToolCard) sticks around only while it stays
  // compatible with the current batch. The moment the batch changes in a
  // way that invalidates it (e.g. a second PDF is added, so a single-file
  // tool no longer applies), this automatically falls back to the batch's
  // `primaryToolId` — which is what makes add/remove-file re-analysis work
  // without any special-cased "switch back" logic.
  const selectedTool = useMemo(() => {
    if (manualToolSlug && analysis.compatibleToolIds.includes(manualToolSlug)) {
      return toolBySlug(manualToolSlug);
    }
    return toolBySlug(analysis.primaryToolId);
  }, [manualToolSlug, analysis]);

  const compatibleTools = useMemo(
    () =>
      analysis.compatibleToolIds
        .map((slug) => toolBySlug(slug))
        .filter((tool): tool is ToolConfig => !!tool),
    [analysis.compatibleToolIds],
  );

  const { state, start, reset, redownload } = useToolConversion(selectedTool ?? FALLBACK_TOOL);

  const oversizedFile = useMemo(
    () => files.find((file) => file.size > MAX_FILE_SIZE_BYTES),
    [files],
  );

  // Set by handleToolSelect when a card tap should start the conversion the
  // moment its tool becomes selected — see that function for why this can't
  // just call `start()` directly.
  const pendingAutoStartRef = useRef(false);

  // A synchronous double-submit guard for handleToolSelect. `state.stage` is
  // React state — it only reflects a `start()` call after the next render,
  // so several click events dispatched within the same tick (a real rapid
  // double/triple-tap can do this) would all still read `state.stage as
  // 'idle'` and all call `start()`. This ref updates immediately, before
  // React re-renders, so the second of two same-tick taps sees it and bails.
  const submitGuardRef = useRef(false);
  useEffect(() => {
    submitGuardRef.current = false;
  }, [state.stage]);

  // Resets the parameter form (and any stale conversion state) whenever the
  // *effective* tool changes — whether from a manual click or an automatic
  // re-analysis fallback — but not on every render. Also the one place that
  // actually calls `start()` for a tap-to-start card pick (see
  // pendingAutoStartRef above): `start` comes from `useToolConversion
  // (selectedTool ...)`, so it's only bound to the *new* tool once this
  // effect runs after the render where `selectedTool` itself updated —
  // calling it any earlier (e.g. synchronously inside the click handler)
  // would still be bound to whichever tool was selected before the click.
  const prevToolSlugRef = useRef<ToolSlug | null>(null);
  useEffect(() => {
    const slug = selectedTool?.slug ?? null;
    if (slug !== prevToolSlugRef.current) {
      prevToolSlugRef.current = slug;
      const values = selectedTool ? initialFieldValues(selectedTool) : {};
      setFieldValues(values);
      if (pendingAutoStartRef.current && selectedTool) {
        pendingAutoStartRef.current = false;
        start(files, values);
      } else {
        reset();
      }
    }
  }, [selectedTool, reset, start, files]);

  const handleInitialFiles = useCallback((fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    setAddFileNotice(null);
    setManualToolSlug(null);
    setFiles(Array.from(fileList));
  }, []);

  const handleAddFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return;
      const picked = Array.from(fileList);
      const currentType = analysis.detectedTypes[0] ?? null;

      const accepted: File[] = [];
      let rejectionMessage: string | null = null;
      for (const file of picked) {
        const type = inferFileType(file.name);
        if (type === null || (currentType && type !== currentType)) {
          rejectionMessage = t.batch.incompatibleFileNotAdded(file.name);
          continue;
        }
        if (file.size > MAX_FILE_SIZE_BYTES) {
          rejectionMessage = t.errors.fileTooLargeDetail(file.name);
          continue;
        }
        accepted.push(file);
      }

      // The existing valid batch is always preserved — incompatible files
      // are simply not added, never silently merged in and never allowed
      // to wipe out what was already there.
      setAddFileNotice(rejectionMessage);
      if (accepted.length > 0) {
        setFiles((prev) => [...prev, ...accepted]);
      }
    },
    [analysis.detectedTypes, t.batch, t.errors],
  );

  const handleRemoveFile = useCallback((index: number) => {
    setAddFileNotice(null);
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleMoveFile = useCallback((index: number, direction: -1 | 1) => {
    setFiles((prev) => moveItem(prev, index, direction));
  }, []);

  const handleToolSelect = useCallback(
    (tool: ToolConfig) => {
      // Guards both a rapid same-tick double/triple-tap (submitGuardRef,
      // see above) and a click that arrives after a previous one already
      // moved the flow out of idle (state.stage, once React has caught up).
      if (state.stage !== 'idle' || submitGuardRef.current) return;

      const initialValues = initialFieldValues(tool);
      const hasMissingRequiredField = tool.fields.some(
        (field) => field.required && !initialValues[field.name]?.trim(),
      );
      // Only when every required field already has a value (e.g. rotation's
      // default, or a tool with no fields at all like PDF → Word) — a tool
      // like watermark or protect, whose required text/password has no
      // default, still needs the ParameterCard filled in and the Start
      // button pressed, same as before.
      const readyToStartImmediately =
        !hasMissingRequiredField && !oversizedFile && files.length > 0;

      if (!readyToStartImmediately) {
        if (tool.slug !== selectedTool?.slug) setManualToolSlug(tool.slug);
        return;
      }

      submitGuardRef.current = true;

      if (tool.slug === selectedTool?.slug) {
        // Already the active tool (e.g. tapping the auto-recommended card
        // again) — `start` in this render's closure is already bound to it,
        // so it's safe to call directly instead of round-tripping through
        // the tool-change effect below.
        start(files, initialValues);
        return;
      }

      setManualToolSlug(tool.slug);
      pendingAutoStartRef.current = true;
    },
    [files, oversizedFile, selectedTool, start, state.stage],
  );

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
    setManualToolSlug(null);
    setFiles([]);
  }, []);

  const handleReset = useCallback(() => {
    setFiles([]);
    setManualToolSlug(null);
    setFieldValues({});
    setAddFileNotice(null);
    reset();
  }, [reset]);

  const handleTryAgain = useCallback(() => {
    reset();
  }, [reset]);

  const category = analysis.detectedTypes.length === 1 ? analysis.detectedTypes[0] : null;
  // The visual PDF page workspace (Delete/Extract/Reorder) is a single-PDF
  // experience only — for a multi-PDF batch, `selectedTool` can only ever
  // be Merge PDF (the sole compatible tool), which has no workspace mode,
  // so this gate falls through to the ordinary ToolCards grid automatically.
  const workspaceMode =
    files.length === 1 && selectedTool ? getPdfWorkspaceMode(selectedTool.slug) : null;

  const missingRequiredField =
    selectedTool?.fields.some((field) => field.required && !fieldValues[field.name]?.trim()) ??
    false;
  const canStart = !!selectedTool && !oversizedFile && !missingRequiredField && files.length > 0;
  const isIdle = state.stage === 'idle';
  const isBusy = !isIdle && state.stage !== 'error' && state.stage !== 'completed';
  const canAddMoreFiles = isIdle && category !== null && analysis.validationReason === null;
  const recommendedSlug = analysis.isBatch ? analysis.primaryToolId : null;

  return (
    <section id="tools" className="mx-auto w-full max-w-[1200px] px-5 pb-28 sm:px-6 sm:pb-16">
      {isIdle && files.length === 0 && (
        <div className="mx-auto max-w-xl">
          <UploadZone
            accept={GENERIC_UPLOAD_ACCEPT}
            multiple
            ariaLabel={t.upload.genericDropZoneAriaLabel}
            subtitleLine={t.upload.genericSupportedTypesLine}
            onFiles={handleInitialFiles}
          />
        </div>
      )}

      {isIdle && files.length > 0 && (
        <div className="animate-fade-in-up mx-auto mt-6 w-full max-w-2xl sm:mt-8">
          {oversizedFile ? (
            <Alert variant="danger">{t.errors.fileTooLargeDetail(oversizedFile.name)}</Alert>
          ) : category ? (
            <FileBatchSummary
              files={files}
              fileType={category}
              reorderable={!!selectedTool?.multiple && files.length > 1}
              onRemoveFile={handleRemoveFile}
              onMoveFile={handleMoveFile}
              onClear={handleReset}
            />
          ) : (
            <div className="border-border bg-surface min-w-0 rounded-2xl border p-4">
              <p className="text-small text-foreground font-medium">
                {t.batch.filesSelected(files.length)}
              </p>
              <button
                type="button"
                className="focus-ring text-small text-muted hover:text-foreground mt-2 rounded font-medium"
                onClick={handleReset}
              >
                {t.batch.clearFiles}
              </button>
            </div>
          )}

          {canAddMoreFiles && (
            <div className="mt-4">
              <UploadZone
                accept={GENERIC_UPLOAD_ACCEPT}
                multiple
                compact
                ariaLabel={t.batch.addMoreDropZoneAriaLabel}
                subtitleLine={t.batch.addFiles}
                onFiles={handleAddFiles}
              />
            </div>
          )}

          {addFileNotice && (
            <Alert variant="warning" className="mt-4">
              {addFileNotice}
            </Alert>
          )}

          {!oversizedFile && analysis.validationReason && (
            <Alert variant="info" className="mt-6" title={t.batch.unsupportedFileSetTitle}>
              {analysis.validationReason === 'mixed-types-unsupported' &&
                t.batch.mixedFilesExplanation}
              {analysis.validationReason === 'no-compatible-tool' && t.batch.noCompatibleToolBody}
              {analysis.validationReason === 'unsupported-file-type' && t.errors.invalidFileType}
            </Alert>
          )}

          {!oversizedFile && !analysis.validationReason && compatibleTools.length > 0 && (
            <>
              {workspaceMode && files[0] ? (
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
                  <h2 className="text-foreground sm:text-h3 mt-5 text-center text-[24px] font-semibold leading-[1.1] sm:mt-8">
                    {t.upload.chooseActionHeading}
                  </h2>
                  <div className="mt-3 sm:mt-4">
                    <ToolCards
                      tools={compatibleTools}
                      selectedSlug={selectedTool?.slug ?? null}
                      recommendedSlug={recommendedSlug}
                      onSelect={handleToolSelect}
                    />
                  </div>

                  {selectedTool && (
                    <div className="mx-auto mt-5 max-w-xl sm:mt-6">
                      <ParameterCard
                        tool={selectedTool}
                        values={fieldValues}
                        onChange={updateField}
                      />

                      <div className="mt-4 flex justify-center">
                        <Button size="lg" disabled={!canStart} onClick={handleStart}>
                          {t.buttons.start}
                        </Button>
                      </div>
                    </div>
                  )}
                </>
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
