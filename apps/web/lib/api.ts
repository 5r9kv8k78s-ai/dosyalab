const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

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
    throw new ApiError('Failed to reach DosyaLab API', response.status);
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
      const detail = await parseErrorDetail(xhr, 'Upload failed. Please try again.');
      reject(new ApiError(detail, xhr.status));
    };

    xhr.onerror = () => {
      reject(new ApiError('Could not reach the DosyaLab server. Check your connection.', 0));
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
      const detail = await parseErrorDetail(xhr, 'Upload failed. Please try again.');
      reject(new ApiError(detail, xhr.status));
    };

    xhr.onerror = () => {
      reject(new ApiError('Could not reach the DosyaLab server. Check your connection.', 0));
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
      const detail = await parseErrorDetail(xhr, 'Upload failed. Please try again.');
      reject(new ApiError(detail, xhr.status));
    };

    xhr.onerror = () => {
      reject(new ApiError('Could not reach the DosyaLab server. Check your connection.', 0));
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
      const detail = await parseErrorDetail(xhr, 'Upload failed. Please try again.');
      reject(new ApiError(detail, xhr.status));
    };

    xhr.onerror = () => {
      reject(new ApiError('Could not reach the DosyaLab server. Check your connection.', 0));
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
      const detail = await parseErrorDetail(xhr, 'Upload failed. Please try again.');
      reject(new ApiError(detail, xhr.status));
    };

    xhr.onerror = () => {
      reject(new ApiError('Could not reach the DosyaLab server. Check your connection.', 0));
    };

    const formData = new FormData();
    for (const file of files) {
      formData.append('files', file);
    }
    xhr.send(formData);
  });
}

export async function getConversionStatus(jobId: string): Promise<ConvertJobStatus> {
  const response = await fetch(`${API_BASE_URL}/api/v1/convert/jobs/${jobId}`);
  if (!response.ok) {
    throw new ApiError('Lost track of the conversion job.', response.status);
  }
  return response.json();
}

/** Fetches the converted file and triggers a browser save-as download. */
export async function downloadConversionResult(jobId: string, filename: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/convert/jobs/${jobId}/download`);
  if (!response.ok) {
    throw new ApiError('Failed to download the converted file.', response.status);
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}
