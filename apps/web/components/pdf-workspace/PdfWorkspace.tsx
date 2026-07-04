'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { useTranslation } from '@/lib/i18n';
import { loadPdfPreview, type PdfPreviewDocument } from '@/lib/pdf/pdfPreview';
import {
  clearPageSelection,
  selectAllPages,
  sortedSelection,
  toggleSelection,
} from '@/lib/pdf/pageSelection';
import type { PdfWorkspaceMode } from '@/lib/pdf/workspaceMode';
import { PdfPageGrid } from './PdfPageGrid';
import { PdfWorkspaceEmptyState } from './PdfWorkspaceEmptyState';
import { PdfWorkspaceHeader } from './PdfWorkspaceHeader';
import { PdfWorkspaceLoading } from './PdfWorkspaceLoading';
import { PdfWorkspaceToolbar } from './PdfWorkspaceToolbar';

type PreviewStatus = 'loading' | 'ready' | 'error';

function identityOrder(pageCount: number): number[] {
  return Array.from({ length: pageCount }, (_, index) => index + 1);
}

/**
 * Pre-conversion configuration stage for page-based PDF tools. Renders in
 * place of the tool-suggestion area once the user picks Delete/Extract
 * Pages (see `getPdfWorkspaceMode`); on confirm it hands the exact
 * form-field values the existing backend contract expects back up to
 * ConversionFlow, which starts the unchanged `useToolConversion` flow.
 */
export function PdfWorkspace({
  file,
  mode,
  onBack,
  onConfirm,
}: {
  file: File;
  mode: PdfWorkspaceMode;
  onBack: () => void;
  onConfirm: (fieldValues: Record<string, string>) => void;
}) {
  const { t } = useTranslation();
  const docRef = useRef<PdfPreviewDocument | null>(null);

  const [status, setStatus] = useState<PreviewStatus>('loading');
  const [pageCount, setPageCount] = useState<number | null>(null);
  const [selectedPages, setSelectedPages] = useState<Set<number>>(clearPageSelection());

  // Load (and re-load on file change) + always release pdf.js resources.
  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    setPageCount(null);
    setSelectedPages(clearPageSelection());

    loadPdfPreview(file)
      .then((doc) => {
        if (cancelled) {
          doc.destroy();
          return;
        }
        docRef.current = doc;
        setPageCount(doc.pageCount);
        setStatus('ready');
      })
      .catch(() => {
        if (cancelled) return;
        // The specific pdf.js/PdfPreviewError message is English-only and
        // meant for logs, not users — the workspace always shows the same
        // localized, generic explanation regardless of failure reason.
        setStatus('error');
      });

    return () => {
      cancelled = true;
      docRef.current?.destroy();
      docRef.current = null;
    };
  }, [file]);

  const renderThumbnail = useCallback(async (pageNumber: number, targetWidth: number) => {
    if (!docRef.current) throw new Error('PDF preview is not ready yet.');
    return docRef.current.renderThumbnail(pageNumber, targetWidth);
  }, []);

  const handleToggleSelect = useCallback((pageNumber: number) => {
    setSelectedPages((prev) => toggleSelection(prev, pageNumber));
  }, []);

  const handleSelectAll = useCallback(() => {
    if (pageCount) setSelectedPages(selectAllPages(pageCount));
  }, [pageCount]);

  const handleClearSelection = useCallback(() => {
    setSelectedPages(clearPageSelection());
  }, []);

  const handleConfirm = useCallback(() => {
    onConfirm({ pages: sortedSelection(selectedPages).join(',') });
  }, [onConfirm, selectedPages]);

  const copy = t.pdfWorkspace[mode];
  const allSelected = pageCount !== null && selectedPages.size >= pageCount;
  const canConfirm =
    mode === 'delete' ? selectedPages.size > 0 && !allSelected : selectedPages.size > 0;

  return (
    <div className="border-border bg-surface shadow-premium rounded-2xl border p-6">
      <PdfWorkspaceHeader
        fileName={file.name}
        pageCount={pageCount}
        operationTitle={copy.title}
        onBack={onBack}
      />

      <p className="text-small text-muted mt-4">{copy.helper}</p>

      <div className="mt-6">
        {status === 'loading' && <PdfWorkspaceLoading />}

        {status === 'error' && (
          <PdfWorkspaceEmptyState
            title={t.pdfWorkspace.previewErrorTitle}
            body={t.pdfWorkspace.previewErrorBody}
            onBack={onBack}
          />
        )}

        {status === 'ready' && pageCount !== null && (
          <>
            <div className="mb-4">
              <PdfWorkspaceToolbar
                selectedCount={selectedPages.size}
                onSelectAll={handleSelectAll}
                onClearSelection={handleClearSelection}
              />
            </div>

            <PdfPageGrid
              pageOrder={identityOrder(pageCount)}
              selectedPages={selectedPages}
              renderThumbnail={renderThumbnail}
              onToggleSelect={handleToggleSelect}
            />

            {mode === 'delete' && allSelected && (
              <p className="text-danger text-small mt-4 text-center font-medium">
                {t.pdfWorkspace.delete.allSelectedError}
              </p>
            )}

            <div className="mt-6 flex justify-center">
              <Button size="lg" disabled={!canConfirm} onClick={handleConfirm}>
                {copy.action}
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
