import type { FileType } from '@/components/icons/FileTypeIcon';
import type { Translations } from '@/lib/i18n';

/** Every tool slug must have a matching `t.tools[slug]` entry (see
 * lib/i18n/tr.ts) — this makes a typo or missing translation a compile
 * error rather than a silent blank title at runtime. */
export type ToolSlug = keyof Translations['tools'];

/** Keys of the form `"{slug}.{fieldName}"` used to look up a field's
 * label/placeholder/hint in `t.toolFields` (see lib/i18n/tr.ts). */
export type ToolFieldKey = keyof Translations['toolFields'];

/** Fixed left-to-right order for the four category chips — a `const` array
 * rather than derived from `TOOLS`, since a category (Excel, today) can be
 * legitimately empty and still needs to appear in the selector. */
export const FILE_CATEGORIES: FileType[] = ['pdf', 'word', 'excel', 'image'];

export interface ToolFieldConfig {
  name: string;
  type: 'text' | 'number' | 'password';
  required?: boolean;
  defaultValue?: string;
}

export interface ToolConfig {
  /** Matches the backend endpoint slug exactly: POST /api/v1/convert/{slug}.
   * Also used to look up this tool's title/description in the i18n tree
   * (`t.tools[slug]`) — see lib/i18n/tr.ts. */
  slug: ToolSlug;
  /** Drives both the tool's icon color (see FileTypeIcon) and which of the
   * four category chips (PDF/Word/Excel/Görseller) surfaces it — grouped by
   * the tool's *input* file type, not its output. */
  fileType: FileType;
  accept: string;
  multiple: boolean;
  /** Only meaningful when `multiple` is true — defaults to 1. */
  minFiles?: number;
  /** Extra form fields sent alongside the file(s), in addition to file/files.
   * Each field's label/placeholder/hint is looked up in the i18n tree via
   * `t.toolFields["{slug}.{name}"]` — see lib/i18n/tr.ts. */
  fields: ToolFieldConfig[];
}

/** Builds the `t.toolFields` lookup key for a given tool + field name. The
 * cast is the one spot this scheme isn't fully statically checked — every
 * `(slug, field.name)` pair in `TOOLS` below must have a matching entry in
 * `t.toolFields`, verified by the i18n audit rather than the compiler. */
export function toolFieldKey(slug: ToolSlug, fieldName: string): ToolFieldKey {
  return `${slug}.${fieldName}` as ToolFieldKey;
}

const PDF_ACCEPT = 'application/pdf,.pdf';

export const TOOLS: ToolConfig[] = [
  // Word input
  {
    slug: 'docx-to-pdf',
    fileType: 'word',
    accept: '.doc,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    multiple: false,
    fields: [],
  },

  // Image input
  {
    slug: 'images-to-pdf',
    fileType: 'image',
    accept: 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp',
    multiple: true,
    fields: [],
  },

  // PDF input
  {
    slug: 'pdf-to-docx',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [],
  },
  {
    slug: 'pdf-to-xlsx',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [],
  },
  {
    slug: 'merge-pdf',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: true,
    minFiles: 2,
    fields: [],
  },
  {
    slug: 'split-pdf',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [{ name: 'pages_per_file', type: 'number', defaultValue: '1' }],
  },
  {
    slug: 'delete-pages',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [{ name: 'pages', type: 'text', required: true }],
  },
  {
    slug: 'extract-pages',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [{ name: 'pages', type: 'text', required: true }],
  },
  {
    slug: 'reorder-pages',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [{ name: 'order', type: 'text', required: true }],
  },
  {
    slug: 'compress-pdf',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [],
  },
  {
    slug: 'rotate-pdf',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [
      { name: 'rotation', type: 'number', defaultValue: '90', required: true },
      { name: 'pages', type: 'text' },
    ],
  },
  {
    slug: 'watermark-pdf',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [
      { name: 'text', type: 'text', required: true },
      { name: 'font_size', type: 'number', defaultValue: '40' },
      { name: 'opacity', type: 'number', defaultValue: '0.3' },
    ],
  },
  {
    slug: 'protect-pdf',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [{ name: 'user_password', type: 'password', required: true }],
  },
  {
    slug: 'unlock-pdf',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [{ name: 'password', type: 'password', required: true }],
  },
  {
    slug: 'pdf-to-images',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [
      { name: 'image_format', type: 'text', defaultValue: 'png' },
      { name: 'dpi', type: 'number', defaultValue: '150' },
    ],
  },
  {
    slug: 'extract-images',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [],
  },
  {
    slug: 'extract-text',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [{ name: 'pages', type: 'text' }],
  },
];

/** Groups tools by `fileType` for the category-chip UI (PDF / Word / Excel /
 * Görseller). There is currently no tool whose *input* is an Excel file, so
 * that group can legitimately be empty — the UI shows `categories.emptyState`
 * rather than force-fitting an output-only tool (like PDF → Excel) into it. */
export function toolsByFileType(fileType: FileType): ToolConfig[] {
  return TOOLS.filter((tool) => tool.fileType === fileType);
}
