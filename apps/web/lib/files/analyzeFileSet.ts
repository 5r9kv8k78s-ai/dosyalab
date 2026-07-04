import type { FileType } from '@/components/icons/FileTypeIcon';
import { TOOLS, inferFileType, type ToolConfig, type ToolSlug } from '@/lib/tools';

/**
 * Coarse shape of a dropped batch, used only for reporting/branching in the
 * UI layer — every actual "what can the user do with this" decision comes
 * from {@link FileSetAnalysis.compatibleToolIds}, computed generically from
 * the tool capability model in lib/tools.ts, not from this label.
 */
export type FileSetKind =
  'empty' | 'single' | 'multi-pdf' | 'multi-image' | 'multi-same-type' | 'multi-mixed';

/** Why `compatibleToolIds` came back empty (or `null` when it didn't). */
export type FileSetValidationReason =
  null | 'unsupported-file-type' | 'mixed-types-unsupported' | 'no-compatible-tool';

export interface FileSetAnalysis {
  kind: FileSetKind;
  fileCount: number;
  /** Unique recognized file types present, in first-seen order. */
  detectedTypes: FileType[];
  /** Every tool slug the current batch can actually be submitted to, per
   * the tool capability model — ordered the same as `TOOLS`. */
  compatibleToolIds: ToolSlug[];
  /** The tool to visually lead with — the first multi-file-capable tool
   * for a batch, otherwise the first compatible tool. `null` if none. */
  primaryToolId: ToolSlug | null;
  isBatch: boolean;
  validationReason: FileSetValidationReason;
}

/** A non-multi-file tool only ever accepts exactly one file — it must not
 * be treated as "compatible" just because a batch happens to shrink to 1
 * (that 1-file case is itself the single-file tool set, handled by picking
 * a fresh `fileType` group, not by loosening this check). A multi-file tool
 * enforces its own real `minFiles`/`maxFiles` even when count is 1, so
 * e.g. merge-pdf (minFiles 2) is correctly excluded for a lone PDF. */
function toolAcceptsFileCount(tool: ToolConfig, count: number): boolean {
  if (!tool.multiple) return count === 1;
  const minFiles = tool.minFiles ?? 1;
  if (count < minFiles) return false;
  if (tool.maxFiles !== undefined && count > tool.maxFiles) return false;
  return true;
}

const EMPTY_ANALYSIS: FileSetAnalysis = {
  kind: 'empty',
  fileCount: 0,
  detectedTypes: [],
  compatibleToolIds: [],
  primaryToolId: null,
  isBatch: false,
  validationReason: null,
};

/**
 * Deterministic, rule-based analysis of an entire dropped/added file
 * batch — always over the full `File[]`, never just `files[0]`. No AI or
 * external service of any kind is involved: type is inferred purely from
 * file extension (see {@link inferFileType}), and every suggestion comes
 * from matching the batch against the real, inspected backend contracts
 * encoded in `TOOLS` (see lib/tools.ts).
 */
export function analyzeFileSet(files: File[]): FileSetAnalysis {
  const fileCount = files.length;
  if (fileCount === 0) return EMPTY_ANALYSIS;

  const isBatch = fileCount > 1;
  const perFileTypes = files.map((file) => inferFileType(file.name));
  const hasUnsupported = perFileTypes.some((type) => type === null);
  const detectedTypes = Array.from(
    new Set(perFileTypes.filter((type): type is FileType => type !== null)),
  );

  if (hasUnsupported) {
    return {
      kind: isBatch ? 'multi-mixed' : 'single',
      fileCount,
      detectedTypes,
      compatibleToolIds: [],
      primaryToolId: null,
      isBatch,
      validationReason: 'unsupported-file-type',
    };
  }

  if (detectedTypes.length > 1) {
    return {
      kind: 'multi-mixed',
      fileCount,
      detectedTypes,
      compatibleToolIds: [],
      primaryToolId: null,
      isBatch,
      validationReason: 'mixed-types-unsupported',
    };
  }

  const fileType = detectedTypes[0];
  const compatibleTools = TOOLS.filter(
    (tool) => tool.fileType === fileType && toolAcceptsFileCount(tool, fileCount),
  );
  const compatibleToolIds = compatibleTools.map((tool) => tool.slug);
  const primaryTool = isBatch
    ? (compatibleTools.find((tool) => tool.multiple) ?? compatibleTools[0] ?? null)
    : (compatibleTools[0] ?? null);

  let kind: FileSetKind;
  if (!isBatch) {
    kind = 'single';
  } else if (fileType === 'pdf') {
    kind = 'multi-pdf';
  } else if (fileType === 'image') {
    kind = 'multi-image';
  } else {
    kind = 'multi-same-type';
  }

  return {
    kind,
    fileCount,
    detectedTypes,
    compatibleToolIds,
    primaryToolId: primaryTool?.slug ?? null,
    isBatch,
    validationReason: compatibleToolIds.length === 0 && isBatch ? 'no-compatible-tool' : null,
  };
}
