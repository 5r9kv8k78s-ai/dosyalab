import { createSupabaseBrowserClient } from '@/lib/supabase/client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export type DateRangeKey = 'today' | '7d' | '30d';

export class AdminApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = 'AdminApiError';
  }
}

export interface OverviewMetrics {
  range: string;
  conversion_attempts: number;
  successful_conversions: number;
  failed_conversions: number;
  validation_rejections: number;
  rate_limit_rejections: number;
  success_rate: number;
  average_duration_ms: number | null;
  total_files_processed: number;
}

export interface DailyActivityItem {
  day: string;
  attempts: number;
  successes: number;
  failures_or_rejections: number;
}

export interface OverviewChart {
  range: string;
  days: DailyActivityItem[];
}

export interface ToolAggregationItem {
  tool_slug: string;
  attempt_count: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  average_duration_ms: number | null;
}

export interface ToolsResponse {
  range: string;
  tools: ToolAggregationItem[];
}

export interface ErrorAggregationItem {
  error_code: string;
  count: number;
}

export interface ErrorsResponse {
  range: string;
  errors: ErrorAggregationItem[];
}

export interface FeedbackAdminItem {
  feedback_id: string;
  category: string;
  message: string;
  email: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface FeedbackListResponse {
  items: FeedbackAdminItem[];
  counts_by_status: Record<string, number>;
}

/**
 * The one place every Admin Panel screen calls through. Attaches the
 * current Supabase session's access token as a bearer token (never stored
 * manually — @supabase/ssr owns the session/cookie lifecycle) and signs
 * the user out on any 401/403, so a non-admin authenticated session never
 * lingers inside the Admin UI (see Phase 21's "sign the session out"
 * requirement) — the caller is expected to redirect to /admin/login after
 * catching this.
 */
async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const supabase = createSupabaseBrowserClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    throw new AdminApiError('Not authenticated.', 401);
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/admin${path}`, {
    ...init,
    headers: {
      ...init?.headers,
      Authorization: `Bearer ${session.access_token}`,
    },
  });

  if (response.status === 401 || response.status === 403) {
    await supabase.auth.signOut();
    throw new AdminApiError('Not authorized.', response.status);
  }

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const body = await response.json();
      detail = typeof body?.detail === 'string' ? body.detail : undefined;
    } catch {
      detail = undefined;
    }
    throw new AdminApiError(detail ?? 'Something went wrong.', response.status);
  }

  return response.json();
}

export function getOverview(range: DateRangeKey): Promise<OverviewMetrics> {
  return adminFetch(`/overview?range=${range}`);
}

export function getOverviewChart(range: DateRangeKey): Promise<OverviewChart> {
  return adminFetch(`/overview/chart?range=${range}`);
}

export function getTools(range: DateRangeKey): Promise<ToolsResponse> {
  return adminFetch(`/tools?range=${range}`);
}

export function getErrors(range: DateRangeKey): Promise<ErrorsResponse> {
  return adminFetch(`/errors?range=${range}`);
}

export function listFeedback(filters: {
  status?: string;
  category?: string;
}): Promise<FeedbackListResponse> {
  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.category) params.set('category', filters.category);
  const query = params.toString();
  return adminFetch(`/feedback${query ? `?${query}` : ''}`);
}

export function updateFeedbackStatus(
  feedbackId: string,
  newStatus: string,
): Promise<FeedbackAdminItem> {
  return adminFetch(`/feedback/${feedbackId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus }),
  });
}
