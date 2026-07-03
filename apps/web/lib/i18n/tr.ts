/**
 * Canonical Turkish translation tree. This is the source of truth for the
 * app's string shape — `en.ts` (and any future locale) is type-checked
 * against `Translations = typeof tr`, so a missing key in another locale is
 * a compile error, not a silent runtime fallback.
 */
export const tr = {
  common: {
    brandName: 'DosyaLab',
    file: 'dosya',
  },

  hero: {
    title: 'Belgelerinizi saniyeler içinde dönüştürün.',
    subtitle:
      'PDF, Word, Excel ve görsellerinizi güvenli, hızlı ve tamamen tarayıcınız üzerinden dönüştürün.',
    privacyNote: 'Dosyalarınız işlem tamamlandıktan sonra otomatik silinir.',
    badgeFast: 'Çok Hızlı',
    badgeSecure: 'Güvenli',
    badgeNoInstall: 'Kurulum Gerektirmez',
  },

  nav: {
    footerAriaLabel: 'Alt bilgi',
    mainAriaLabel: 'Ana menü',
    tools: 'Araçlar',
    api: 'API',
    pricing: 'Fiyatlandırma',
    about: 'Hakkımızda',
    privacy: 'Gizlilik Politikası',
    terms: 'Kullanım Şartları',
    contact: 'İletişim',
    github: 'GitHub',
  },

  theme: {
    switchToLight: 'Açık temaya geç',
    switchToDark: 'Koyu temaya geç',
  },

  categories: {
    sectionAriaLabel: 'Dosya kategorisi seçin',
    pdf: 'PDF',
    word: 'Word',
    excel: 'Excel',
    image: 'Görseller',
    emptyState: 'Bu kategoride henüz araç bulunmuyor.',
  },

  toolChips: {
    ariaLabel: 'Araç seçin',
  },

  tools: {
    'pdf-to-docx': {
      title: 'PDF → Word',
      description: 'PDF dosyanızı düzenlenebilir Word belgesine dönüştürün',
    },
    'docx-to-pdf': {
      title: 'Word → PDF',
      description: 'Word belgenizi PDF formatına dönüştürün',
    },
    'pdf-to-xlsx': {
      title: 'PDF → Excel',
      description: 'PDF içindeki tabloları Excel dosyasına aktarın',
    },
    'images-to-pdf': {
      title: 'Görsel → PDF',
      description: 'Görsellerinizi tek bir PDF dosyasında birleştirin',
    },
    'merge-pdf': {
      title: 'PDF Birleştir',
      description: 'Birden çok PDF dosyasını tek dosyada birleştirin',
    },
    'split-pdf': {
      title: 'PDF Böl',
      description: 'PDF dosyasını birden çok parçaya bölün',
    },
    'delete-pages': {
      title: 'Sayfa Sil',
      description: 'PDF içinden istediğiniz sayfaları silin',
    },
    'extract-pages': {
      title: 'Sayfa Çıkart',
      description: 'Seçtiğiniz sayfaları yeni bir PDF olarak çıkarın',
    },
    'reorder-pages': {
      title: 'Sayfa Sırala',
      description: 'PDF sayfalarını yeni bir sırayla düzenleyin',
    },
    'compress-pdf': {
      title: 'PDF Sıkıştır',
      description: 'PDF dosya boyutunu küçültün',
    },
    'rotate-pdf': {
      title: 'PDF Döndür',
      description: 'PDF sayfalarını istediğiniz açıyla döndürün',
    },
    'watermark-pdf': {
      title: 'Filigran Ekle',
      description: 'PDF sayfalarına filigran metni ekleyin',
    },
    'protect-pdf': {
      title: 'PDF Şifrele',
      description: 'PDF dosyanızı şifreyle koruyun',
    },
    'unlock-pdf': {
      title: 'PDF Kilidini Aç',
      description: 'Şifreli PDF dosyasının korumasını kaldırın',
    },
    'pdf-to-images': {
      title: 'PDF → Görseller',
      description: 'PDF sayfalarını görsel olarak dışa aktarın',
    },
    'extract-images': {
      title: 'Görselleri Çıkart',
      description: 'PDF içine gömülü görselleri çıkarın',
    },
    'extract-text': {
      title: 'Metni Çıkart',
      description: 'PDF içindeki metni dışa aktarın',
    },
  },

  // Keyed by "{toolSlug}.{fieldName}" since the same field name (e.g. "pages")
  // carries a different label depending on which tool is asking for it.
  toolFields: {
    'split-pdf.pages_per_file': { label: 'Dosya başına sayfa sayısı' },
    'delete-pages.pages': { label: 'Silinecek sayfalar', placeholder: 'örn. 1,3,5' },
    'extract-pages.pages': { label: 'Çıkarılacak sayfalar', placeholder: 'örn. 1,3,5' },
    'reorder-pages.order': {
      label: 'Yeni sayfa sırası',
      placeholder: 'örn. 3,1,2 (tüm sayfalar)',
    },
    'rotate-pdf.rotation': {
      label: 'Döndürme açısı (derece)',
      hint: '90, 180 veya 270 olmalı',
    },
    'rotate-pdf.pages': {
      label: 'Sayfalar (opsiyonel)',
      placeholder: 'boş bırakılırsa tüm sayfalar',
    },
    'watermark-pdf.text': { label: 'Filigran metni' },
    'watermark-pdf.font_size': { label: 'Boyut' },
    'watermark-pdf.opacity': { label: 'Opaklık', hint: '0 ile 1 arası' },
    'protect-pdf.user_password': { label: 'Şifre' },
    'unlock-pdf.password': { label: 'Mevcut şifre' },
    'pdf-to-images.image_format': { label: 'Format (png/jpg)' },
    'pdf-to-images.dpi': { label: 'Çözünürlük (DPI)' },
    'extract-text.pages': {
      label: 'Sayfalar (opsiyonel)',
      placeholder: 'boş bırakılırsa tüm sayfalar',
    },
  },

  upload: {
    dropHere: 'Dosyanızı buraya bırakın',
    or: 'veya',
    chooseFile: 'Dosya seçin',
    maxSizeLabel: 'Maksimum 100 MB',
    supportedTypes: 'Desteklenen dosya türleri',
    dropZoneAriaLabel: (toolTitle: string) =>
      `${toolTitle} için dosyanızı buraya bırakın veya Dosya seçin ile göz atın`,
    mergeDropZoneAriaLabel: 'Birleştirmek için iki veya daha fazla PDF sürükleyin veya göz atın',
    mergeHint: 'İki veya daha fazla PDF — her biri en fazla 100MB',
    selectedCount: (count: number) => `${count} PDF seçildi — gerekirse sırasını değiştirin`,
    selectToolFirst: 'Önce bir araç seçin',
  },

  progress: {
    uploading: 'Yükleniyor…',
    processing: 'İşleniyor…',
    converting: 'Dönüştürülüyor…',
    preparing: 'Hazırlanıyor…',
    downloading: 'İndiriliyor…',
    completed: 'Tamamlandı',
    download: 'İndir',
    fileUploading: (name: string) => `${name} yükleniyor…`,
    filesUploading: (count: number) => `${count} PDF yükleniyor…`,
    creatingTool: (toolTitle: string) => `${toolTitle} oluşturuluyor…`,
    creatingMergedPdf: 'Birleştirilmiş PDF oluşturuluyor…',
    doneDownloaded: (filename: string) => `Tamamlandı — ${filename} indirildi`,
    mergedDownloaded: (filename: string) => `Birleştirildi — ${filename} indirildi`,
  },

  errors: {
    invalidFileType: 'Geçersiz dosya türü',
    fileTooLarge: 'Dosya çok büyük',
    somethingWrong: 'Bir hata oluştu',
    tryAgainMessage: 'Lütfen tekrar deneyin',
    unsupportedFileTypeFor: (fileName: string, toolTitle: string) =>
      `${fileName}, ${toolTitle} için desteklenmeyen bir dosya türü.`,
    fileTooLargeDetail: (fileName: string) => `${fileName} dosyası 100MB sınırını aşıyor.`,
    onlyPdfSupported: 'Bu dönüştürme için yalnızca PDF dosyaları desteklenir.',
    conversionFailedTryDifferent: 'Dönüştürme başarısız oldu. Lütfen başka bir dosya deneyin.',
    healthCheckFailed: "DosyaLab API'sine ulaşılamadı.",
    uploadFailed: 'Yükleme başarısız oldu. Lütfen tekrar deneyin.',
    serverUnreachable: 'DosyaLab sunucusuna ulaşılamadı. Bağlantınızı kontrol edin.',
    jobNotFound: 'Dönüştürme işi takip edilemedi.',
    downloadFailed: 'Dönüştürülen dosya indirilemedi.',
  },

  buttons: {
    start: 'Başlat',
    cancel: 'İptal',
    clear: 'Temizle',
    tryAgain: 'Tekrar Dene',
    download: 'İndir',
    convertAnotherFile: 'Başka bir dosya dönüştür',
    newConversion: 'Yeni dosya dönüştür',
    mergePdfs: "PDF'leri Birleştir",
    mergeMoreFiles: 'Daha fazla dosya birleştir',
    moveFileUp: (fileName: string) => `${fileName} dosyasını yukarı taşı`,
    moveFileDown: (fileName: string) => `${fileName} dosyasını aşağı taşı`,
    removeFile: (fileName: string) => `${fileName} dosyasını kaldır`,
  },

  success: {
    title: 'Dönüştürme tamamlandı',
    subtitle: 'Dosyanız başarıyla hazırlandı.',
  },

  status: {
    checking: 'Sunucu kontrol ediliyor…',
    online: 'Backend Çevrimiçi',
    offline: 'Backend Çevrimdışı',
  },

  language: {
    switcherAriaLabel: 'Dil seçimi',
    tr: 'Türkçe',
    en: 'English',
  },

  pages: {
    about: {
      metaTitle: 'Hakkımızda — DosyaLab',
      heading: 'DosyaLab Hakkında',
      paragraph1:
        'DosyaLab bir belge dönüştürme aracıdır. Dosyanızı bırakın, sunucuda dönüştürülsün ve doğrudan tarayıcınıza geri gönderilsin — hesap gerekmez, kurulum gerekmez.',
      paragraph2:
        'PDF → Word ile başlayan dönüştürme, temel motorun izin verdiği ölçüde düzeni, başlıkları, görselleri ve tabloları olabildiğince sadık şekilde korur. Word → PDF, Görsel → PDF, PDF → Excel ve daha birçok araç da aynı dönüştürme altyapısı üzerine inşa edilmiş durumda.',
      paragraph3Prefix:
        'DosyaLab aktif olarak geliştiriliyor. Beklediğiniz gibi dönüşmeyen bir şey olursa bunu bilmek bizim için değerli — ',
      contactLinkText: 'iletişim sayfasına',
      paragraph3Suffix: ' göz atın.',
    },
    contact: {
      metaTitle: 'İletişim — DosyaLab',
      heading: 'İletişim',
      paragraph1:
        'DosyaLab yeni ve aktif olarak geliştirilen bir proje; henüz özel destek kanalları kurulmadı.',
      paragraph2:
        'Gerçek iletişim bilgileri — destek e-postası, sorun takip sistemi veya geri bildirim formu — buraya eklenecek.',
    },
    privacy: {
      metaTitle: 'Gizlilik Politikası — DosyaLab',
      heading: 'Gizlilik Politikası',
      intro:
        'Bu sayfa, DosyaLab kullanırken dosyalarınıza ve verilerinize gerçekte ne olduğunu açıklar.',
      filesTitle: 'Yüklediğiniz dosyalar',
      filesBody:
        'Dosyalar yalnızca talep ettiğiniz dönüştürmeyi çalıştırmak için sunucuya yüklenir. Dönüştürülen sonuç, siz indirir indirmez hemen silinir. Bir dönüştürme hiç indirilmezse, hem orijinal yükleme hem de oluşturulan dosya periyodik bir temizlik taramasında otomatik olarak silinir — hiçbir şey süresiz saklanmaz.',
      accountsTitle: 'Hesaplar ve takip',
      accountsBody:
        'DosyaLab hesap gerektirmez ve analitik ya da reklam takip araçları kullanmaz. Uygulamanın yaptığı tek istekler, dosyanızı yüklemek, dönüştürmeyi çalıştırmak ve sonucu size geri sunmak için gereken isteklerdir.',
      changesTitle: 'Değişiklikler',
      changesBody:
        'DosyaLab aktif olarak geliştiriliyor ve bu davranış değiştiğinde bu politika da güncellenecek.',
    },
    terms: {
      metaTitle: 'Kullanım Şartları — DosyaLab',
      heading: 'Kullanım Şartları',
      paragraph1:
        'DosyaLab olduğu gibi, ücretsiz olarak sunulur; çalışma süresi veya kullanılabilirlik garantisi verilmez. Aktif olarak geliştirilmektedir ve özellikler, sınırlar ve davranış değişebilir.',
      paragraph2:
        "Yüklediğiniz dosyalardan ve bunları dönüştürüp indirme hakkına sahip olmaktan siz sorumlusunuz. DosyaLab'ı, işleme izniniz olmayan dosyalar için kullanmayın.",
      paragraph3:
        'Bu, hukuki tavsiye yerine geçmeyen minimal bir başlangıç politikasıdır — ürün olgunlaştıkça genişletilecektir.',
    },
    api: {
      metaTitle: 'API — DosyaLab',
      heading: 'API',
      body: 'Programatik erişim için bir DosyaLab API’si üzerinde çalışıyoruz. Duyurulduğunda burada yer alacak.',
    },
    pricing: {
      metaTitle: 'Fiyatlandırma — DosyaLab',
      heading: 'Fiyatlandırma',
      body: 'DosyaLab şu an için tamamen ücretsiz. Ücretli planlar eklendiğinde detaylar burada olacak.',
    },
  },
};
