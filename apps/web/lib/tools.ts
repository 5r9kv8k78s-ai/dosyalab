import type { FileType } from '@/components/icons/FileTypeIcon';

export type ToolCategory = 'convert' | 'organize' | 'optimize' | 'security' | 'extract';

export const TOOL_CATEGORIES: { id: ToolCategory; label: string }[] = [
  { id: 'convert', label: 'Convert' },
  { id: 'organize', label: 'Organize' },
  { id: 'optimize', label: 'Optimize' },
  { id: 'security', label: 'Security' },
  { id: 'extract', label: 'Extract' },
];

export interface ToolFieldConfig {
  name: string;
  label: string;
  type: 'text' | 'number' | 'password';
  placeholder?: string;
  required?: boolean;
  defaultValue?: string;
  hint?: string;
}

export interface ToolConfig {
  /** Matches the backend endpoint slug exactly: POST /api/v1/convert/{slug}. */
  slug: string;
  title: string;
  description: string;
  category: ToolCategory;
  fileType: FileType;
  accept: string;
  multiple: boolean;
  /** Extra form fields sent alongside the file(s), in addition to file/files. */
  fields: ToolFieldConfig[];
}

const PDF_ACCEPT = 'application/pdf,.pdf';

export const TOOLS: ToolConfig[] = [
  // Convert
  {
    slug: 'pdf-to-docx',
    title: 'PDF → Word',
    description: 'PDF dosyanızı düzenlenebilir Word belgesine dönüştürün',
    category: 'convert',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [],
  },
  {
    slug: 'docx-to-pdf',
    title: 'Word → PDF',
    description: 'Word belgenizi PDF formatına dönüştürün',
    category: 'convert',
    fileType: 'word',
    accept: '.doc,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    multiple: false,
    fields: [],
  },
  {
    slug: 'pdf-to-xlsx',
    title: 'PDF → Excel',
    description: 'PDF içindeki tabloları Excel dosyasına aktarın',
    category: 'convert',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [],
  },
  {
    slug: 'images-to-pdf',
    title: 'Image → PDF',
    description: 'Görsellerinizi tek bir PDF dosyasında birleştirin',
    category: 'convert',
    fileType: 'image',
    accept: 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp',
    multiple: true,
    fields: [],
  },

  // Organize
  {
    slug: 'merge-pdf',
    title: 'Merge PDF',
    description: 'Birden çok PDF dosyasını tek dosyada birleştirin',
    category: 'organize',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: true,
    fields: [],
  },
  {
    slug: 'split-pdf',
    title: 'Split PDF',
    description: 'PDF dosyasını birden çok parçaya bölün',
    category: 'organize',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [
      {
        name: 'pages_per_file',
        label: 'Dosya başına sayfa sayısı',
        type: 'number',
        defaultValue: '1',
      },
    ],
  },
  {
    slug: 'delete-pages',
    title: 'Delete Pages',
    description: 'PDF içinden istediğiniz sayfaları silin',
    category: 'organize',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [
      {
        name: 'pages',
        label: 'Silinecek sayfalar',
        type: 'text',
        placeholder: 'örn. 1,3,5',
        required: true,
      },
    ],
  },
  {
    slug: 'extract-pages',
    title: 'Extract Pages',
    description: 'Seçtiğiniz sayfaları yeni bir PDF olarak çıkarın',
    category: 'organize',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [
      {
        name: 'pages',
        label: 'Çıkarılacak sayfalar',
        type: 'text',
        placeholder: 'örn. 1,3,5',
        required: true,
      },
    ],
  },
  {
    slug: 'reorder-pages',
    title: 'Reorder Pages',
    description: 'PDF sayfalarını yeni bir sırayla düzenleyin',
    category: 'organize',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [
      {
        name: 'order',
        label: 'Yeni sayfa sırası',
        type: 'text',
        placeholder: 'örn. 3,1,2 (tüm sayfalar)',
        required: true,
      },
    ],
  },

  // Optimize
  {
    slug: 'compress-pdf',
    title: 'Compress PDF',
    description: 'PDF dosya boyutunu küçültün',
    category: 'optimize',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [],
  },
  {
    slug: 'rotate-pdf',
    title: 'Rotate PDF',
    description: 'PDF sayfalarını istediğiniz açıyla döndürün',
    category: 'optimize',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [
      {
        name: 'rotation',
        label: 'Döndürme açısı (derece)',
        type: 'number',
        defaultValue: '90',
        required: true,
        hint: '90, 180 veya 270 olmalı',
      },
      {
        name: 'pages',
        label: 'Sayfalar (opsiyonel)',
        type: 'text',
        placeholder: 'boş bırakılırsa tüm sayfalar',
      },
    ],
  },

  // Security
  {
    slug: 'watermark-pdf',
    title: 'Watermark',
    description: 'PDF sayfalarına filigran metni ekleyin',
    category: 'security',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [
      { name: 'text', label: 'Filigran metni', type: 'text', required: true },
    ],
  },
  {
    slug: 'protect-pdf',
    title: 'Protect PDF',
    description: 'PDF dosyanızı şifreyle koruyun',
    category: 'security',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [
      { name: 'user_password', label: 'Şifre', type: 'password', required: true },
    ],
  },
  {
    slug: 'unlock-pdf',
    title: 'Unlock PDF',
    description: 'Şifreli PDF dosyasının korumasını kaldırın',
    category: 'security',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [
      { name: 'password', label: 'Mevcut şifre', type: 'password', required: true },
    ],
  },

  // Extract
  {
    slug: 'pdf-to-images',
    title: 'PDF → Images',
    description: 'PDF sayfalarını görsel olarak dışa aktarın',
    category: 'extract',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [
      { name: 'image_format', label: 'Format (png/jpg)', type: 'text', defaultValue: 'png' },
      { name: 'dpi', label: 'Çözünürlük (DPI)', type: 'number', defaultValue: '150' },
    ],
  },
  {
    slug: 'extract-images',
    title: 'Extract Images',
    description: 'PDF içine gömülü görselleri çıkarın',
    category: 'extract',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [],
  },
  {
    slug: 'extract-text',
    title: 'Extract Text',
    description: 'PDF içindeki metni dışa aktarın',
    category: 'extract',
    fileType: 'pdf',
    accept: PDF_ACCEPT,
    multiple: false,
    fields: [
      {
        name: 'pages',
        label: 'Sayfalar (opsiyonel)',
        type: 'text',
        placeholder: 'boş bırakılırsa tüm sayfalar',
      },
    ],
  },
];
