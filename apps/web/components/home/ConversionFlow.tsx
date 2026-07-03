'use client';

import { useCallback, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import type { FileType } from '@/components/icons/FileTypeIcon';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { useTranslation } from '@/lib/i18n';
import { useToolConversion } from '@/lib/hooks/useToolConversion';
import { toolsByFileType, type ToolConfig } from '@/lib/tools';
import { CategorySelector } from './CategorySelector';
import { ParameterCard } from './ParameterCard';
import { ProgressFlow } from './ProgressFlow';
import { SelectedFilesList } from './SelectedFilesList';
import { SuccessScreen } from './SuccessScreen';
import { ToolChips } from './ToolChips';
import { UploadZone } from './UploadZone';

const MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024;

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

export function ConversionFlow() {
  const { t } = useTranslation();

  const [category, setCategory] = useState<FileType>('pdf');
  const [selectedTool, setSelectedTool] = useState<ToolConfig>(() => toolsByFileType('pdf')[0]);
  const [files, setFiles] = useState<File[]>([]);
  const [fieldValues, setFieldValues] = useState<Record<string, string>>(() =>
    initialFieldValues(selectedTool),
  );
  const [pickError, setPickError] = useState<string | null>(null);

  const { state, start, reset, redownload } = useToolConversion(selectedTool);

  const applyTool = useCallback((tool: ToolConfig) => {
    setSelectedTool(tool);
    setFiles([]);
    setFieldValues(initialFieldValues(tool));
    setPickError(null);
  }, []);

  const handleCategorySelect = useCallback(
    (nextCategory: FileType) => {
      setCategory(nextCategory);
      reset();
      const tools = toolsByFileType(nextCategory);
      if (tools.length > 0) applyTool(tools[0]);
    },
    [applyTool, reset],
  );

  const handleToolSelect = useCallback(
    (tool: ToolConfig) => {
      reset();
      applyTool(tool);
    },
    [applyTool, reset],
  );

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return;
      let picked = Array.from(fileList);
      if (!selectedTool.multiple) picked = picked.slice(0, 1);

      const allowedExtensions = extensionsFromAccept(selectedTool.accept);
      const invalidFile = picked.find(
        (file) => !allowedExtensions.some((ext) => file.name.toLowerCase().endsWith(ext)),
      );
      if (invalidFile) {
        setPickError(
          t.errors.unsupportedFileTypeFor(invalidFile.name, t.tools[selectedTool.slug].title),
        );
        return;
      }
      const oversizedFile = picked.find((file) => file.size > MAX_FILE_SIZE_BYTES);
      if (oversizedFile) {
        setPickError(t.errors.fileTooLargeDetail(oversizedFile.name));
        return;
      }

      setPickError(null);
      setFiles((prev) => (selectedTool.multiple ? [...prev, ...picked] : picked));
    },
    [selectedTool, t.errors, t.tools],
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

  const handleTryAgain = useCallback(() => {
    setFiles([]);
    setPickError(null);
    reset();
  }, [reset]);

  const missingRequiredField = selectedTool.fields.some(
    (field) => field.required && !fieldValues[field.name]?.trim(),
  );
  const minFiles = selectedTool.multiple ? (selectedTool.minFiles ?? 1) : 1;
  const canStart = files.length >= minFiles && !missingRequiredField;

  const isBusy = state.stage !== 'idle' && state.stage !== 'error' && state.stage !== 'completed';
  const categoryHasTools = toolsByFileType(category).length > 0;
  const showUploadArea = state.stage === 'idle' && categoryHasTools;

  return (
    <section id="tools" className="mx-auto max-w-[1200px] px-6 py-8">
      <CategorySelector activeCategory={category} onSelect={handleCategorySelect} />

      <div className="mt-6">
        <ToolChips
          category={category}
          selectedSlug={selectedTool.slug}
          onSelect={handleToolSelect}
        />
      </div>

      <div className="mx-auto mt-8 max-w-xl">
        <AnimatePresence mode="wait">
          {showUploadArea && (
            <motion.div
              key="upload"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
            >
              <UploadZone tool={selectedTool} onFiles={handleFiles} />

              {pickError && (
                <Alert variant="danger" className="mt-4">
                  {pickError}
                </Alert>
              )}

              <SelectedFilesList
                files={files}
                reorderable={selectedTool.multiple && files.length > 1}
                onRemove={removeFile}
                onMove={moveFile}
              />

              <ParameterCard tool={selectedTool} values={fieldValues} onChange={updateField} />

              {files.length > 0 && (
                <div className="mt-4 flex justify-center">
                  <Button size="lg" disabled={!canStart} onClick={handleStart}>
                    {t.buttons.start}
                  </Button>
                </div>
              )}
            </motion.div>
          )}

          {isBusy && (
            <motion.div
              key="progress"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="border-border bg-surface rounded-[28px] border px-8 py-12"
            >
              <ProgressFlow stage={state.stage} uploadProgress={state.uploadProgress} />
            </motion.div>
          )}

          {state.stage === 'completed' && (
            <motion.div
              key="success"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="border-border bg-surface rounded-[28px] border px-8"
            >
              <SuccessScreen onDownloadAgain={redownload} onNewConversion={handleTryAgain} />
            </motion.div>
          )}

          {state.stage === 'error' && (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="border-border bg-surface space-y-4 rounded-[28px] border px-8 py-12 text-center"
            >
              <Alert variant="danger">{state.errorMessage}</Alert>
              <Button variant="outline" onClick={handleTryAgain}>
                {t.buttons.tryAgain}
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
