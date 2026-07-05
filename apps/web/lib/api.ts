import { detectBrowserLocale, readStoredLocale, translations } from '@/lib/i18n';
import { triggerBrowserDownload } from '@/lib/utils';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

/**
 * This module has no access to React context (it's plain functions, not a
 * component/hook), so it can't call `useTranslation()`. `readStoredLocale`
 * and `detectBrowserLocale` are the same plain, non-hook functions
 * `LanguageProvider` uses internally — reusing them here keeps network-level
 * error messages in the user's actual chosen/detected language.
 */
function currentTranslations() {
  return translations[readStoredLocale() ?? detectBrowserLocale()];
}

export interface HealthStatus {
  status: string;
  environment: string;
  version: string;
}

export type ConversionStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ConvertJobCreated {
  job_id: string;
  status: ConversionStatus;
}

export interface ConvertJobStatus {
  job_id: string;
  status: ConversionStatus;
  progress: number;
  filename: string;
  error: string | null;
  download_url: string | null;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function getHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`);
  if (!response.ok) {
    throw new ApiError(currentTranslations().errors.healthCheckFailed, response.status);
  }
  return response.json();
}

async function parseErrorDetail(xhr: XMLHttpRequest, fallback: string): Promise<string> {
  try {
    const body = JSON.parse(xhr.responseText);
    return typeof body?.detail === 'string' ? body.detail : fallback;
  } catch {
    return fallback;
  }
}

/**
 * Submits a PDF for conversion via XMLHttpRequest (not fetch) specifically
 * because only XHR exposes upload progress events in the browser today.
 */
export function submitPdfToDocxConversion(
  file: File,
  onUploadProgress: (percent: number) => void,
): Promise<ConvertJobCreated> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE_URL}/api/v1/convert/pdf-to-docx`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onUploadProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
        return;
      }
      const detail = await parseErrorDetail(xhr, currentTranslations().errors.uploadFailed);
      reject(new ApiError(detail, xhr.status));
    };

    xhr.onerror = () => {
      reject(new ApiError(currentTranslations().errors.serverUnreachable, 0));
    };

    const formData = new FormData();
    formData.append('file', file);
    xhr.send(formData);
  });
}

/**
 * Submits a DOCX for conversion via XMLHttpRequest (not fetch) specifically
 * because only XHR exposes upload progress events in the browser today.
 * Mirrors `submitPdfToDocxConversion` above — kept as a separate function
 * rather than a shared helper so the existing PDF → Word path isn't touched.
 */
export function submitDocxToPdfConversion(
  file: File,
  onUploadProgress: (percent: number) => void,
): Promise<ConvertJobCreated> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE_URL}/api/v1/convert/docx-to-pdf`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onUploadProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
        return;
      }
      const detail = await parseErrorDetail(xhr, currentTranslations().errors.uploadFailed);
      reject(new ApiError(detail, xhr.status));
    };

    xhr.onerror = () => {
      reject(new ApiError(currentTranslations().errors.serverUnreachable, 0));
    };

    const formData = new FormData();
    formData.append('file', file);
    xhr.send(formData);
  });
}

/**
 * Submits a PDF for table extraction to XLSX via XMLHttpRequest (not fetch)
 * specifically because only XHR exposes upload progress events in the
 * browser today. Mirrors `submitPdfToDocxConversion` above — kept as a
 * separate function rather than a shared helper so the existing PDF → Word
 * and Word → PDF paths aren't touched.
 */
export function submitPdfToXlsxConversion(
  file: File,
  onUploadProgress: (percent: number) => void,
): Promise<ConvertJobCreated> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE_URL}/api/v1/convert/pdf-to-xlsx`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onUploadProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
        return;
      }
      const detail = await parseErrorDetail(xhr, currentTranslations().errors.uploadFailed);
      reject(new ApiError(detail, xhr.status));
    };

    xhr.onerror = () => {
      reject(new ApiError(currentTranslations().errors.serverUnreachable, 0));
    };

    const formData = new FormData();
    formData.append('file', file);
    xhr.send(formData);
  });
}

/**
 * Submits one or more images to be combined into a single PDF via
 * XMLHttpRequest (not fetch) specifically because only XHR exposes upload
 * progress events in the browser today. Mirrors `submitPdfToDocxConversion`
 * above — kept as a separate function rather than a shared helper so the
 * existing PDF → Word, Word → PDF, and PDF → Excel paths aren't touched.
 * The only structural difference is appending every file under the same
 * "files" field name, matching the backend's `files: list[UploadFile]`.
 */
export function submitImagesToPdfConversion(
  files: File[],
  onUploadProgress: (percent: number) => void,
): Promise<ConvertJobCreated> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE_URL}/api/v1/convert/images-to-pdf`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onUploadProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
        return;
      }
      const detail = await parseErrorDetail(xhr, currentTranslations().errors.uploadFailed);
      reject(new ApiError(detail, xhr.status));
    };

    xhr.onerror = () => {
      reject(new ApiError(currentTranslations().errors.serverUnreachable, 0));
    };

    const formData = new FormData();
    for (const file of files) {
      formData.append('files', file);
    }
    xhr.send(formData);
  });
}

/**
 * Submits two or more PDFs to be merged into one, in the given order, via
 * XMLHttpRequest (not fetch) specifically because only XHR exposes upload
 * progress events in the browser today. Mirrors `submitImagesToPdfConversion`
 * above — kept as a separate function rather than a shared helper so the
 * existing PDF → Word, Word → PDF, PDF → Excel, and Image → PDF paths aren't
 * touched.
 */
export function submitMergePdfConversion(
  files: File[],
  onUploadProgress: (percent: number) => void,
): Promise<ConvertJobCreated> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE_URL}/api/v1/convert/merge-pdf`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onUploadProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
        return;
      }
      const detail = await parseErrorDetail(xhr, currentTranslations().errors.uploadFailed);
      reject(new ApiError(detail, xhr.status));
    };

    xhr.onerror = () => {
      reject(new ApiError(currentTranslations().errors.serverUnreachable, 0));
    };

    const formData = new FormData();
    for (const file of files) {
      formData.append('files', file);
    }
    xhr.send(formData);
  });
}

/**
 * Submits file(s) plus arbitrary extra form fields to any `/api/v1/convert/{slug}`
 * endpoint via XMLHttpRequest (not fetch) specifically because only XHR exposes
 * upload progress events in the browser today. Generic counterpart to the
 * per-tool `submit*Conversion` functions above — used by `ToolCard`, which
 * drives every tool that doesn't need bespoke UI (like Merge PDF's reorder step).
 */
export function submitToolConversion(
  slug: string,
  files: File[],
  fields: Record<string, string>,
  multiple: boolean,
  onUploadProgress: (percent: number) => void,
): Promise<ConvertJobCreated> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE_URL}/api/v1/convert/${slug}`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onUploadProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
        return;
      }
      const detail = await parseErrorDetail(xhr, currentTranslations().errors.uploadFailed);
      reject(new ApiError(detail, xhr.status));
    };

    xhr.onerror = () => {
      reject(new ApiError(currentTranslations().errors.serverUnreachable, 0));
    };

    const formData = new FormData();
    const fileFieldName = multiple ? 'files' : 'file';
    for (const file of files) {
      formData.append(fileFieldName, file);
    }
    for (const [key, value] of Object.entries(fields)) {
      formData.append(key, value);
    }
    xhr.send(formData);
  });
}

export async function getConversionStatus(
  jobId: string,
  signal?: AbortSignal,
): Promise<ConvertJobStatus> {
  const response = await fetch(`${API_BASE_URL}/api/v1/convert/jobs/${jobId}`, { signal });
  if (!response.ok) {
    throw new ApiError(currentTranslations().errors.jobNotFound, response.status);
  }
  return response.json();
}

/** Fetches the converted file and triggers a browser save-as download. */
/** Fetches the converted file's bytes without triggering a save — callers
 * that need to offer a "download again" affordance (the file is deleted
 * server-side right after the first successful download, so a second fetch
 * would 404) can hold onto the returned blob and re-save it locally via
 * `triggerBrowserDownload` in lib/utils.ts. */
export async function fetchConversionResultBlob(jobId: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/v1/convert/jobs/${jobId}/download`);
  if (!response.ok) {
    throw new ApiError(currentTranslations().errors.downloadFailed, response.status);
  }
  return response.blob();
}

export async function downloadConversionResult(jobId: string, filename: string): Promise<void> {
  const blob = await fetchConversionResultBlob(jobId);
  triggerBrowserDownload(blob, filename);
}

export interface FeedbackCreated {
  feedback_id: string;
  status: string;
}

/** Submits a "Bir fikrim var" entry. No file upload, no upload-progress
 * need, so this uses plain `fetch` rather than the XHR pattern the
 * conversion functions above use specifically for progress events. */
export async function submitFeedback(input: {
  category: string;
  message: string;
  email?: string;
}): Promise<FeedbackCreated> {
  const response = await fetch(`${API_BASE_URL}/api/v1/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const body = await response.json();
      detail = typeof body?.detail === 'string' ? body.detail : undefined;
    } catch {
      detail = undefined;
    }
    throw new ApiError(detail ?? currentTranslations().errors.somethingWrong, response.status);
  }

  return response.json();
}
