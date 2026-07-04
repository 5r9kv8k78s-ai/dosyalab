import type { ToolSlug } from '@/lib/tools';

/** The page-based operations the PDF workspace currently knows how to
 * drive. Adding a future tool (rotate, split, watermark-selected-pages)
 * means adding a mode here and a matching branch in PdfWorkspace.tsx —
 * nothing else in ConversionFlow needs to change. */
export type PdfWorkspaceMode = 'delete' | 'extract';

const TOOL_TO_WORKSPACE_MODE: Partial<Record<ToolSlug, PdfWorkspaceMode>> = {
  'delete-pages': 'delete',
  'extract-pages': 'extract',
};

/** Single source of truth for "does this tool open the visual PDF
 * workspace instead of starting conversion immediately". */
export function getPdfWorkspaceMode(slug: ToolSlug): PdfWorkspaceMode | null {
  return TOOL_TO_WORKSPACE_MODE[slug] ?? null;
}
