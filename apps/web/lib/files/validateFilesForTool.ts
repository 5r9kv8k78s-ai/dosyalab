import type { ToolConfig } from '@/lib/tools';

export const MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024;

export type FileValidationReason =
  | 'unsupported-file-type'
  | 'too-few-files'
  | 'too-many-files'
  | 'mixed-types-unsupported'
  | 'file-too-large';

export interface FileValidationResult {
  valid: boolean;
  reason: FileValidationReason | null;
  /** The specific file that failed, when the failure is per-file
   * (unsupported type / too large) rather than about the batch as a whole. */
  invalidFile?: File;
}

const VALID_RESULT: FileValidationResult = { valid: true, reason: null };

export function extensionsFromAccept(accept: string): string[] {
  return accept
    .split(',')
    .map((part) => part.trim())
    .filter((part) => part.startsWith('.'));
}

/**
 * Pure, UI-independent check for "can this exact file list be submitted to
 * this tool" — checked again here rather than relying only on disabled UI,
 * since a batch can be assembled through several code paths (initial drop,
 * add-more-files, tool switch).
 */
export function validateFilesForTool(files: File[], tool: ToolConfig): FileValidationResult {
  const allowedExtensions = extensionsFromAccept(tool.accept);
  const invalidFile = files.find(
    (file) => !allowedExtensions.some((ext) => file.name.toLowerCase().endsWith(ext)),
  );
  if (invalidFile) {
    return { valid: false, reason: 'unsupported-file-type', invalidFile };
  }

  if (files.length > 1 && !tool.multiple && !tool.supportsMixedTypes) {
    return { valid: false, reason: 'too-many-files' };
  }

  const minFiles = tool.multiple ? (tool.minFiles ?? 1) : 1;
  if (files.length < minFiles) {
    return { valid: false, reason: 'too-few-files' };
  }
  if (tool.multiple && tool.maxFiles !== undefined && files.length > tool.maxFiles) {
    return { valid: false, reason: 'too-many-files' };
  }

  const oversizedFile = files.find((file) => file.size > MAX_FILE_SIZE_BYTES);
  if (oversizedFile) {
    return { valid: false, reason: 'file-too-large', invalidFile: oversizedFile };
  }

  return VALID_RESULT;
}
