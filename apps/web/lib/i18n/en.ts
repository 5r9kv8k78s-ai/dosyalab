import type { Translations } from './index';

/**
 * English translation. Type-checked against `Translations` (derived from
 * `tr.ts`), so a missing or mis-shaped key here is a compile error.
 */
export const en: Translations = {
  common: {
    brandName: 'DosyaLab',
    file: 'file',
    brandTagline: "Türkiye's file platform",
  },

  hero: {
    title: 'Drop your file. DosyaLab takes it from there.',
    subtitle:
      'Upload your PDF, Word, Excel, or image files. DosyaLab automatically analyzes your file and suggests the best actions.',
    privacyNote: 'Your files are deleted automatically once processing is complete.',
    badgeFast: 'Very Fast',
    badgeSecure: 'Secure',
    badgeNoInstall: 'No Installation',
  },

  nav: {
    footerAriaLabel: 'Footer',
    mainAriaLabel: 'Main navigation',
    tools: 'Tools',
    api: 'API',
    pricing: 'Pricing',
    about: 'About',
    privacy: 'Privacy Policy',
    terms: 'Terms',
    contact: 'Contact',
    github: 'GitHub',
  },

  theme: {
    switchToLight: 'Switch to light theme',
    switchToDark: 'Switch to dark theme',
  },

  categories: {
    sectionAriaLabel: 'Choose a file category',
    pdf: 'PDF',
    word: 'Word',
    excel: 'Excel',
    image: 'Images',
    emptyState: 'No tools in this category yet.',
  },

  toolChips: {
    ariaLabel: 'Choose a tool',
  },

  tools: {
    'pdf-to-docx': {
      title: 'PDF → Word',
      description: 'Convert your PDF into an editable Word document',
    },
    'docx-to-pdf': {
      title: 'Word → PDF',
      description: 'Convert your Word document to PDF format',
    },
    'pdf-to-xlsx': {
      title: 'PDF → Excel',
      description: 'Export tables from a PDF into an Excel file',
    },
    'images-to-pdf': {
      title: 'Image → PDF',
      description: 'Combine your images into a single PDF file',
    },
    'merge-pdf': {
      title: 'Merge PDF',
      description: 'Combine multiple PDF files into one',
    },
    'split-pdf': {
      title: 'Split PDF',
      description: 'Split a PDF file into multiple parts',
    },
    'delete-pages': {
      title: 'Delete Pages',
      description: 'Remove the pages you choose from a PDF',
    },
    'extract-pages': {
      title: 'Extract Pages',
      description: 'Extract the pages you choose into a new PDF',
    },
    'reorder-pages': {
      title: 'Reorder Pages',
      description: 'Rearrange the pages of a PDF into a new order',
    },
    'compress-pdf': {
      title: 'Compress PDF',
      description: 'Reduce the file size of a PDF',
    },
    'rotate-pdf': {
      title: 'Rotate PDF',
      description: 'Rotate the pages of a PDF by the angle you choose',
    },
    'watermark-pdf': {
      title: 'Watermark',
      description: 'Add watermark text to the pages of a PDF',
    },
    'protect-pdf': {
      title: 'Protect PDF',
      description: 'Secure your PDF file with a password',
    },
    'unlock-pdf': {
      title: 'Unlock PDF',
      description: 'Remove password protection from a PDF file',
    },
    'pdf-to-images': {
      title: 'PDF → Images',
      description: 'Export the pages of a PDF as images',
    },
    'extract-images': {
      title: 'Extract Images',
      description: 'Extract the images embedded in a PDF',
    },
    'extract-text': {
      title: 'Extract Text',
      description: 'Export the text content of a PDF',
    },
  },

  toolFields: {
    'split-pdf.pages_per_file': { label: 'Pages per file' },
    'delete-pages.pages': { label: 'Pages to delete', placeholder: 'e.g. 1,3,5' },
    'extract-pages.pages': { label: 'Pages to extract', placeholder: 'e.g. 1,3,5' },
    'reorder-pages.order': {
      label: 'New page order',
      placeholder: 'e.g. 3,1,2 (every page)',
    },
    'rotate-pdf.rotation': {
      label: 'Rotation angle (degrees)',
      hint: 'Must be 90, 180, or 270',
    },
    'rotate-pdf.pages': {
      label: 'Pages (optional)',
      placeholder: 'leave blank for every page',
    },
    'watermark-pdf.text': { label: 'Watermark text' },
    'watermark-pdf.font_size': { label: 'Size' },
    'watermark-pdf.opacity': { label: 'Opacity', hint: 'Between 0 and 1' },
    'protect-pdf.user_password': { label: 'Password' },
    'unlock-pdf.password': { label: 'Current password' },
    'pdf-to-images.image_format': { label: 'Format (png/jpg)' },
    'pdf-to-images.dpi': { label: 'Resolution (DPI)' },
    'extract-text.pages': {
      label: 'Pages (optional)',
      placeholder: 'leave blank for every page',
    },
  },

  upload: {
    dropHere: 'Drop your file here',
    or: 'or',
    chooseFile: 'Choose File',
    maxSizeLabel: 'Maximum 100 MB',
    supportedTypes: 'Supported file types',
    dropZoneAriaLabel: (toolTitle: string) =>
      `Drop your file here, or use Choose File to browse, for ${toolTitle}`,
    mergeDropZoneAriaLabel: 'Drop two or more PDFs here, or click to browse, to merge them',
    mergeHint: 'Two or more PDFs — up to 100MB each',
    selectedCount: (count: number) => `${count} PDFs selected — reorder if needed`,
    selectToolFirst: 'Select a tool first',
    genericDropZoneAriaLabel: 'Drop the file you want to convert here, or browse',
    genericSupportedTypesLine: 'PDF • DOC • DOCX • XLS • XLSX • JPG • PNG',
    chooseActionHeading: 'What would you like to do with this file?',
    pickDifferentFile: 'Choose a different file',
  },

  batch: {
    recommendedBadge: 'Recommended',
    pdfFilesDetected: (count: number) => `${count} PDF files detected`,
    imagesDetected: (count: number) => `${count} images detected`,
    filesSelected: (count: number) => `${count} files selected`,
    totalSizeLabel: (size: string) => `Total size: ${size}`,
    addFiles: 'Add files',
    addMoreDropZoneAriaLabel: 'Drop more files here, or click to browse, to add to this batch',
    moreFilesTruncated: (count: number) => `+${count} files more`,
    showAll: 'Show all',
    showLess: 'Show less',
    clearFiles: 'Clear files',
    differentTypesDetected: 'Different file types detected',
    mixedFilesExplanation:
      "These files can't be processed together because there's no shared conversion for this combination. Select only files of the same type (for example, only PDFs or only images) to continue.",
    unsupportedFileSetTitle: 'Unsupported file combination',
    noCompatibleToolBody:
      "There's no shared operation for this many files of this type. Reduce the number of files and try again.",
    incompatibleFileNotAdded: (fileName: string) =>
      `${fileName} isn't compatible with your current file batch, so it wasn't added.`,
    validationLiveRegionLabel: 'File validation message',
  },

  progress: {
    uploading: 'Uploading…',
    processing: 'Processing…',
    converting: 'Converting…',
    preparing: 'Preparing…',
    downloading: 'Downloading…',
    completed: 'Completed',
    download: 'Download',
    fileUploading: (name: string) => `Uploading ${name}…`,
    filesUploading: (count: number) => `Uploading ${count} PDFs…`,
    creatingTool: (toolTitle: string) => `Creating ${toolTitle}…`,
    creatingMergedPdf: 'Creating merged PDF…',
    doneDownloaded: (filename: string) => `Done — ${filename} downloaded`,
    mergedDownloaded: (filename: string) => `Merged — ${filename} downloaded`,
  },

  errors: {
    invalidFileType: 'Invalid file type',
    fileTooLarge: 'File too large',
    somethingWrong: 'Something went wrong',
    tryAgainMessage: 'Please try again',
    unsupportedFileTypeFor: (fileName: string, toolTitle: string) =>
      `${fileName} is not a supported file type for ${toolTitle}.`,
    fileTooLargeDetail: (fileName: string) => `${fileName} is larger than the 100MB limit.`,
    onlyPdfSupported: 'Only PDF files are supported for this conversion.',
    conversionFailedTryDifferent: 'Conversion failed. Please try a different file.',
    healthCheckFailed: 'Failed to reach DosyaLab API.',
    uploadFailed: 'Upload failed. Please try again.',
    serverUnreachable: 'Could not reach the DosyaLab server. Check your connection.',
    jobNotFound: 'Lost track of the conversion job.',
    downloadFailed: 'Failed to download the converted file.',
  },

  buttons: {
    start: 'Start',
    cancel: 'Cancel',
    clear: 'Clear',
    tryAgain: 'Try Again',
    download: 'Download',
    convertAnotherFile: 'Convert another file',
    newConversion: 'Convert a new file',
    mergePdfs: 'Merge PDFs',
    mergeMoreFiles: 'Merge more files',
    moveFileUp: (fileName: string) => `Move ${fileName} up`,
    moveFileDown: (fileName: string) => `Move ${fileName} down`,
    removeFile: (fileName: string) => `Remove ${fileName}`,
  },

  success: {
    title: 'Conversion complete',
    subtitle: 'Your file was prepared successfully.',
  },

  feedback: {
    buttonLabel: 'I have an idea',
    title: 'I have an idea',
    description:
      "Help us build DosyaLab. Share an idea, a suggestion, or a problem you've run into.",
    categoryLabel: 'Category',
    categories: {
      idea: 'Idea',
      suggestion: 'Suggestion',
      problem: 'Problem',
      other: 'Other',
    },
    messageLabel: 'What do you think?',
    messageCounter: (count: number, max: number) => `${count} / ${max}`,
    emailLabel: 'Email',
    emailHint: "If you'd like us to get back to you. Optional.",
    submit: 'Send',
    submitting: 'Sending…',
    successTitle: 'Your idea made it to DosyaLab.',
    successBody: 'Thank you.',
    closeButton: 'Close',
    errorGeneric: "Your feedback couldn't be sent. Please try again.",
    errorRateLimited: "You've sent a lot of feedback recently. Please try again shortly.",
    errorMessageTooShort: 'Your message needs to be a bit longer.',
    closeAriaLabel: 'Close',
  },

  pdfWorkspace: {
    back: 'Back',
    pageCountLabel: (count: number) => `${count} pages`,
    pageLabel: (pageNumber: number) => `Page ${pageNumber}`,
    preparingPdf: 'Preparing PDF…',
    selectAll: 'Select All',
    clearSelection: 'Clear Selection',
    selectedCount: (count: number) => `${count} pages selected`,
    previewErrorTitle: "This PDF couldn't be previewed.",
    previewErrorBody: 'Your file may be corrupted or password-protected.',
    backButton: 'Go Back',
    delete: {
      title: 'Select the pages to delete',
      helper: 'Select the pages you want to remove from your PDF.',
      action: 'Delete Selected Pages',
      allSelectedError: 'Every page in this PDF cannot be deleted.',
    },
    extract: {
      title: 'Select the pages to extract',
      helper: 'Select the pages you want to build a new PDF from.',
      action: 'Extract Selected Pages',
    },
    reorder: {
      title: 'Reorder the pages',
      helper: 'Drag the pages into the order you want.',
      action: 'Apply New Order',
      reset: 'Reset Order',
    },
  },

  status: {
    checking: 'Checking backend…',
    online: 'Backend Online',
    offline: 'Backend Offline',
  },

  language: {
    switcherAriaLabel: 'Language selection',
    tr: 'Türkçe',
    en: 'English',
  },

  maintenance: {
    title: 'DosyaLab is briefly under maintenance',
    defaultBody:
      "We're doing a short maintenance run to serve you better. We'll be back shortly.",
  },

  pages: {
    about: {
      metaTitle: 'About — DosyaLab',
      heading: 'About DosyaLab',
      paragraph1:
        "DosyaLab is a document conversion tool. Drop in a file, and it's converted on the server and sent straight back to your browser — no account, no installation.",
      paragraph2:
        'Starting with PDF → Word, conversions preserve layout, headings, images, and tables as faithfully as the underlying engine allows. Word → PDF, Image → PDF, PDF → Excel, and many more tools are built on the same conversion pipeline.',
      paragraph3Prefix:
        "DosyaLab is under active development. If something doesn't convert the way you expect, that's useful to know — see the ",
      contactLinkText: 'contact page',
      paragraph3Suffix: '.',
    },
    contact: {
      metaTitle: 'Contact — DosyaLab',
      heading: 'Contact',
      paragraph1:
        "DosyaLab is a new, actively developed project, and dedicated support channels aren't set up yet.",
      paragraph2:
        'Real contact details — support email, issue tracker, or feedback form — will be added here.',
    },
    privacy: {
      metaTitle: 'Privacy Policy — DosyaLab',
      heading: 'Privacy Policy',
      intro:
        'This page describes what actually happens to your files and data when you use DosyaLab.',
      filesTitle: 'Files you upload',
      filesBody:
        'Files are uploaded to the server only to run the conversion you requested. The converted result is deleted immediately after you download it. If a conversion is never downloaded, both the original upload and any generated file are automatically deleted on a periodic cleanup sweep — nothing is kept indefinitely.',
      accountsTitle: 'Accounts and tracking',
      accountsBody:
        "DosyaLab doesn't require an account, and doesn't use analytics or advertising trackers. The only requests the app makes are the ones needed to upload your file, run the conversion, and serve the result back to you.",
      changesTitle: 'Changes',
      changesBody:
        'DosyaLab is under active development, and this policy will be updated if that behavior changes.',
    },
    terms: {
      metaTitle: 'Terms — DosyaLab',
      heading: 'Terms',
      paragraph1:
        "DosyaLab is provided as-is, free to use, with no guarantee of uptime or availability. It's under active development and features, limits, and behavior may change.",
      paragraph2:
        "You're responsible for the files you upload and for having the right to convert and download them. Don't use DosyaLab to process files you don't have permission to handle.",
      paragraph3:
        'This is a minimal starter policy, not a substitute for legal advice — it will be expanded as the product matures.',
    },
    api: {
      metaTitle: 'API — DosyaLab',
      heading: 'API',
      body: "We're working on a DosyaLab API for programmatic access. It'll be announced here.",
    },
    pricing: {
      metaTitle: 'Pricing — DosyaLab',
      heading: 'Pricing',
      body: 'DosyaLab is completely free for now. Details will land here if paid plans are ever added.',
    },
  },
};
