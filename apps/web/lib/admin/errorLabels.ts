/** Maps the backend's stable error_code categories (see
 * apps/api/app/services/operations_events.py) to clear Turkish labels for
 * the Admin Panel — never a raw exception message, which the backend
 * never records in the first place. */
const ERROR_CODE_LABELS: Record<string, string> = {
  invalid_file_type: 'Desteklenmeyen dosya türü',
  invalid_file_count: 'Geçersiz dosya sayısı',
  file_too_large: 'Dosya boyutu sınırı',
  batch_too_large: 'Çok fazla dosya',
  conversion_failed: 'Dönüştürme başarısız',
  rate_limited: 'İstek sınırı',
  validation_failed: 'Dosya doğrulama hatası',
};

export function labelForErrorCode(code: string): string {
  return ERROR_CODE_LABELS[code] ?? code;
}
