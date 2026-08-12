export type UserProfile = {
  id: string;
  email: string | null;
  full_name: string | null;
  avatar_url: string | null;
  status: "pending" | "active" | "rejected" | "suspended";
  is_platform_owner: boolean;
  timezone: string;
  locale: string;
  permissions: string[];
};

export type DashboardSummary = {
  total_accounts: number;
  connected_accounts: number;
  expired_accounts: number;
  active_campaigns: number;
  completed_campaigns: number;
  publications_today: number;
  publications_yesterday: number;
  publications_7d: number;
  publications_30d: number;
  views: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  saves: number | null;
  engagement_rate: number | null;
  engagement_period: "today" | "yesterday" | "month" | "custom";
  engagement_date_from: string;
  engagement_date_to: string;
  insights_status: "available" | "pending" | "permission_required" | "no_publications";
  insights_updated_at: string | null;
  queue_depth: number;
  total_proxies: number;
  online_proxies: number;
  offline_proxies: number;
  average_proxy_latency_ms: number | null;
  accounts_using_proxy: number;
  campaigns_using_proxy: number;
};

export type MonthlyRankingEntry = {
  position: number;
  user_id: string;
  full_name: string;
  avatar_url: string | null;
  is_current_user: boolean;
  score: number;
  publications: number;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
  engagement_rate: number;
};

export type MonthlyRanking = {
  month: string;
  period_start: string;
  period_end: string;
  timezone: string;
  is_current_month: boolean;
  generated_at: string;
  total_participants: number;
  entries: MonthlyRankingEntry[];
};

export type Account = {
  id: string;
  instagram_user_id: string;
  username: string;
  display_name: string | null;
  profile_picture_url: string | null;
  account_type: string | null;
  status: string;
  health_status: "unknown" | "checking" | "operational" | "reauth_required" | "action_required" | "permission_required" | "temporarily_restricted" | "possibly_suspended" | "provider_unavailable";
  health_confidence: "unknown" | "inferred" | "confirmed";
  health_source: string | null;
  health_checked_at: string | null;
  health_last_success_at: string | null;
  health_next_check_at: string;
  health_consecutive_failures: number;
  health_error_code: string | null;
  health_error_subcode: string | null;
  health_message: string | null;
  health_action_required: string | null;
  granted_scopes: string[];
  token_expires_at: string | null;
  published_count: number;
  last_published_at: string | null;
  connected_at: string;
  proxy_id: string | null;
  proxy_name: string | null;
  proxy_status: string | null;
  proxy_pool_size: number;
  proxy_rotation_mode: "fixed" | "per_post" | "every_n_posts";
  proxy_rotation_every: number;
  proxy_rotation_counter: number;
  proxy_rotation_current_proxy_id: string | null;
};

export type AccountHealthCheck = {
  id: string;
  status: string;
  details: {
    confidence?: string;
    source?: string;
    provider_code?: number | null;
    provider_subcode?: number | null;
    message?: string;
    action_required?: string | null;
  };
  checked_at: string;
};

export type AccountProxyPool = {
  account_id: string;
  rotation_mode: "fixed" | "per_post" | "every_n_posts";
  rotate_every: number;
  counter: number;
  current_proxy_id: string | null;
  proxies: Array<{
    id: string;
    name: string;
    status: string;
    is_active: boolean;
    priority: number;
    last_selected_at: string | null;
    cooldown_until: string | null;
  }>;
};

export type Proxy = {
  id: string;
  name: string;
  protocol: "http" | "https" | "socks5";
  host: string;
  port: number;
  username: string | null;
  password_configured: boolean;
  country: string | null;
  notes: string | null;
  is_active: boolean;
  status: "unknown" | "online" | "offline";
  last_error: string | null;
  last_check: string | null;
  latency_ms: number | null;
  public_ip: string | null;
  cooldown_until: string | null;
  consecutive_failures: number;
  accounts_using: number;
  created_at: string;
  updated_at: string;
};

export type ProxyTestResult = {
  proxy_id: string;
  status: "online" | "offline";
  public_ip: string | null;
  latency_ms: number | null;
  checked_at: string;
  error: string | null;
};

export type ProxyImportResult = {
  created: number;
  rejected: number;
  proxies: Proxy[];
  errors: Array<{ line: number; error: string }>;
};

export type Media = {
  id: string;
  display_name: string;
  original_name: string;
  mime_type: string;
  media_kind: "image" | "video";
  size_bytes: number;
  duration_ms: number | null;
  width: number | null;
  height: number | null;
  status: string;
  created_at: string;
};

export type CookieStoryPreset = {
  id: string;
  media_id: string;
  media_name: string;
  media_kind: "image" | "video";
  mime_type: string;
  size_bytes: number;
  width: number | null;
  height: number | null;
  duration_ms: number | null;
  preview_url: string | null;
  link_url: string;
  link_title: string | null;
  updated_at: string;
};

export type CookieStoryDelivery = {
  preset_id: string;
  preset_version: string;
  media_id: string;
  media_url: string;
  media_name: string;
  media_kind: "image" | "video";
  mime_type: string;
  size_bytes: number;
  width: number;
  height: number;
  duration_ms: number | null;
  link_url: string;
  link_title: string | null;
  expires_at: string;
};

export type Campaign = {
  id: string;
  name: string;
  description?: string | null;
  caption?: string | null;
  hashtags?: string[];
  publication_type: string;
  media_strategy: string;
  posts_per_hour: number;
  duration_hours: number;
  schedule_distribution?: "even" | "burst" | "cooldown";
  post_cooldown_minutes?: number;
  schedule_mode?: string;
  starts_at: string | null;
  timezone: string;
  cover_mode?: string;
  proxy_mode?: "none" | "fixed" | "rotate_per_post" | "rotate_every_n_posts";
  proxy_id?: string | null;
  proxy_rotation_every?: number;
  allow_media_reuse?: boolean;
  state: string;
  current_version?: number;
  planned_count: number;
  succeeded_count: number;
  failed_count: number;
  created_at: string;
  updated_at?: string;
};

export type CampaignJobAttempt = {
  id: string;
  attempt_number: number;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  request_operation: string;
  response_status: number | null;
  external_trace_id: string | null;
  sanitized_response: Record<string, unknown> | null;
  error_class: string | null;
  retryable: boolean;
  proxy_id: string | null;
};

export type CampaignJob = {
  id: string;
  state: string;
  priority: number;
  plan_position: number;
  rotation_slot: number;
  scheduled_at: string;
  attempt_count: number;
  next_attempt_at: string | null;
  lease_expires_at: string | null;
  published_at: string | null;
  external_container_id: string | null;
  external_media_id: string | null;
  last_error_class: string | null;
  last_error_message: string | null;
  account_id: string;
  account_username: string;
  media_id: string;
  media_name: string;
  proxy_id: string | null;
  proxy_name: string | null;
  attempts: CampaignJobAttempt[];
};

export type CampaignEvent = {
  id: string;
  job_id: string | null;
  event_type: string;
  status: string;
  message: string | null;
  details: Record<string, unknown>;
  occurred_at: string;
  duration_ms: number | null;
  account_username: string | null;
  media_name: string | null;
};

export type CampaignDetail = Campaign & {
  account_ids: string[];
  media_ids: string[];
  accounts: Array<{
    id: string;
    position: number;
    username: string;
    display_name: string | null;
    profile_picture_url: string | null;
    status: string;
    token_expires_at: string | null;
    published_count: number;
    last_published_at: string | null;
    job_counts: Record<string, number>;
  }>;
  media: Array<{
    id: string;
    position: number;
    display_name: string;
    media_kind: string;
    mime_type: string;
    size_bytes: number;
    duration_ms: number | null;
    width: number | null;
    height: number | null;
    status: string;
    failure_reason: string | null;
  }>;
  queue: {
    total: number;
    active: number;
    finished: number;
    progress_percent: number;
    counts: Record<string, number>;
  };
  jobs: CampaignJob[];
  jobs_truncated: boolean;
  events: CampaignEvent[];
  events_truncated: boolean;
  scheduler: {
    status: string;
    last_success_at: string | null;
    last_error: string | null;
    metadata: Record<string, unknown>;
  } | null;
  max_attempts: number;
};
