'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { useTranslation } from '@/lib/i18n';
import { loadPdfPreview, type PdfPreviewDocument } from '@/lib/pdf/pdfPreview';
import {
  clearPageSelection,
  identityOrder,
  isIdentityOrder,
  moveInOrder,
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

/**
 * Pre-conversion configuration stage for page-based PDF tools. Renders in
 * place of the tool-suggestion area once the user picks Delete/Extract/
 * Reorder Pages (see `getPdfWorkspaceMode`); on confirm it hands the exact
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
  const [pageOrder, setPageOrder] = useState<number[]>([]);

  // Load (and re-load on file change) + always release pdf.js resources.
  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    setPageCount(null);
    setSelectedPages(clearPageSelection());
    setPageOrder([]);

    loadPdfPreview(file)
      .then((doc) => {
        if (cancelled) {
          doc.destroy();
          return;
        }
        docRef.current = doc;
        setPageCount(doc.pageCount);
        setPageOrder(identityOrder(doc.pageCount));
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

  const handleReorder = useCallback((fromIndex: number, toIndex: number) => {
    setPageOrder((prev) => moveInOrder(prev, fromIndex, toIndex));
  }, []);

  const handleResetOrder = useCallback(() => {
    if (pageCount) setPageOrder(identityOrder(pageCount));
  }, [pageCount]);

  const handleConfirm = useCallback(() => {
    if (mode === 'reorder') {
      onConfirm({ order: pageOrder.join(',') });
    } else {
      onConfirm({ pages: sortedSelection(selectedPages).join(',') });
    }
  }, [mode, onConfirm, pageOrder, selectedPages]);

  const copy = t.pdfWorkspace[mode];
  const allSelected = pageCount !== null && selectedPages.size >= pageCount;
  const canConfirm =
    mode === 'reorder'
      ? pageCount !== null && pageCount > 1 && !isIdentityOrder(pageOrder)
      : mode === 'delete'
        ? selectedPages.size > 0 && !allSelected
        : selectedPages.size > 0;

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
              {mode === 'reorder' ? (
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={handleResetOrder}
                    disabled={isIdentityOrder(pageOrder)}
                    className="focus-ring text-small text-muted hover:text-foreground duration-base rounded font-medium transition-colors disabled:pointer-events-none disabled:opacity-40"
                  >
                    {t.pdfWorkspace.reorder.reset}
                  </button>
                </div>
              ) : (
                <PdfWorkspaceToolbar
                  selectedCount={selectedPages.size}
                  onSelectAll={handleSelectAll}
                  onClearSelection={handleClearSelection}
                />
              )}
            </div>

            <PdfPageGrid
              mode={mode === 'reorder' ? 'reorder' : 'select'}
              pageOrder={pageOrder}
              selectedPages={selectedPages}
              renderThumbnail={renderThumbnail}
              onToggleSelect={handleToggleSelect}
              onReorder={handleReorder}
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
