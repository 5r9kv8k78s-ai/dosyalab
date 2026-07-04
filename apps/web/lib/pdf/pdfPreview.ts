'use client';

/**
 * Client-side PDF preview engine for the PDF workspace (see
 * components/pdf-workspace/). Everything here runs in the browser via
 * pdfjs-dist — the file never leaves the client for preview purposes, only
 * the existing conversion request (unchanged) sends it to the backend.
 */

export type PdfPreviewErrorReason = 'encrypted' | 'invalid' | 'empty' | 'unknown';

export class PdfPreviewError extends Error {
  constructor(
    message: string,
    public reason: PdfPreviewErrorReason,
  ) {
    super(message);
    this.name = 'PdfPreviewError';
  }
}

export interface PdfPreviewDocument {
  pageCount: number;
  /** Renders one page to a PNG data URL at roughly `targetWidth` CSS
   * pixels wide, preserving aspect ratio. Each call creates and discards
   * its own canvas — nothing is kept in memory beyond the returned string. */
  renderThumbnail(pageNumber: number, targetWidth: number): Promise<string>;
  /** Releases pdf.js's internal document resources. Must be called when the
   * workspace unmounts or the file changes. */
  destroy(): void;
}

let workerConfigured = false;

async function loadPdfjs() {
  const pdfjsLib = await import('pdfjs-dist');
  if (!workerConfigured) {
    // Bundled locally by webpack via `new URL(...)`, not a CDN — required so
    // this keeps working offline and under strict CSP.
    pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
      'pdfjs-dist/build/pdf.worker.min.mjs',
      import.meta.url,
    ).toString();
    workerConfigured = true;
  }
  return pdfjsLib;
}

/** Loads a PDF File for preview only. Throws {@link PdfPreviewError} for
 * anything the workspace needs to show a friendly inline message for. */
export async function loadPdfPreview(file: File): Promise<PdfPreviewDocument> {
  const pdfjsLib = await loadPdfjs();
  const data = await file.arrayBuffer();

  // `destroy()` lives on the loading task, not the resolved document proxy —
  // keep the task around so `PdfPreviewDocument.destroy()` can release it.
  const loadingTask = pdfjsLib.getDocument({ data });

  let doc;
  try {
    doc = await loadingTask.promise;
  } catch (error) {
    const name = error instanceof Error ? error.name : '';
    if (name === 'PasswordException') {
      throw new PdfPreviewError('This PDF is password-protected.', 'encrypted');
    }
    if (name === 'InvalidPDFException') {
      throw new PdfPreviewError('This file is not a valid PDF.', 'invalid');
    }
    throw new PdfPreviewError('Failed to preview this PDF.', 'unknown');
  }

  if (doc.numPages < 1) {
    await loadingTask.destroy();
    throw new PdfPreviewError('This PDF has no pages.', 'empty');
  }

  return {
    pageCount: doc.numPages,
    async renderThumbnail(pageNumber, targetWidth) {
      const page = await doc.getPage(pageNumber);
      try {
        const unscaledViewport = page.getViewport({ scale: 1 });
        const scale = targetWidth / unscaledViewport.width;
        const viewport = page.getViewport({ scale });

        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(viewport.width));
        canvas.height = Math.max(1, Math.round(viewport.height));
        const context = canvas.getContext('2d');
        if (!context) throw new PdfPreviewError('Canvas rendering is unavailable.', 'unknown');

        await page.render({ canvas, canvasContext: context, viewport }).promise;
        const dataUrl = canvas.toDataURL('image/png');
        canvas.width = 0;
        canvas.height = 0;
        return dataUrl;
      } finally {
        page.cleanup();
      }
    },
    destroy() {
      void loadingTask.destroy();
    },
  };
}
