export const FEEDBACK_CATEGORY_LABELS: Record<string, string> = {
  idea: 'Fikir',
  suggestion: 'Öneri',
  problem: 'Sorun',
  other: 'Diğer',
};

export const FEEDBACK_STATUS_LABELS: Record<string, string> = {
  new: 'Yeni',
  reviewing: 'İnceleniyor',
  planned: 'Planlandı',
  completed: 'Tamamlandı',
  archived: 'Arşivlendi',
};

export const FEEDBACK_STATUS_ORDER = ['new', 'reviewing', 'planned', 'completed', 'archived'];
