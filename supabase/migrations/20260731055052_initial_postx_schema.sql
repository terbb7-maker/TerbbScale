create extension if not exists pgcrypto with schema extensions;

create table public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  full_name text,
  avatar_url text,
  status text not null default 'pending',
  timezone text not null default 'UTC',
  locale text not null default 'pt-BR',
  approved_at timestamptz,
  suspended_at timestamptz,
  deleted_at timestamptz,
  last_seen_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint users_status_check check (status in ('pending', 'active', 'rejected', 'suspended', 'deleted')),
  constraint users_email_length check (email is null or length(email) <= 320),
  constraint users_full_name_length check (full_name is null or length(full_name) <= 160)
);
create unique index users_email_active_idx on public.users (lower(email)) where deleted_at is null;
create index users_status_created_at_idx on public.users (status, created_at desc);

create table public.roles (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  description text,
  is_system boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.permissions (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.user_roles (
  user_id uuid not null references public.users(id) on delete cascade,
  role_id uuid not null references public.roles(id) on delete cascade,
  granted_by uuid references public.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, role_id)
);
create index user_roles_role_id_idx on public.user_roles (role_id);

create table public.role_permissions (
  role_id uuid not null references public.roles(id) on delete cascade,
  permission_id uuid not null references public.permissions(id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (role_id, permission_id)
);
create index role_permissions_permission_id_idx on public.role_permissions (permission_id);

create table public.approvals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  decided_by uuid references public.users(id) on delete set null,
  decision text not null default 'pending',
  reason text,
  decided_at timestamptz,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint approvals_decision_check check (decision in ('pending', 'approve', 'reject', 'suspend', 'reactivate'))
);
create index approvals_decision_created_at_idx on public.approvals (decision, created_at desc);
create index approvals_user_id_idx on public.approvals (user_id);

create table public.sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  supabase_session_id uuid unique,
  user_agent_hash text,
  ip_prefix text,
  last_seen_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index sessions_user_active_idx on public.sessions (user_id, revoked_at);

create table public.refresh_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  token_hash text not null unique,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  replaced_by_id uuid references public.refresh_tokens(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint refresh_tokens_hash_length check (length(token_hash) = 64)
);
create index refresh_tokens_user_active_idx on public.refresh_tokens (user_id, revoked_at);

create table public.settings (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null unique references public.users(id) on delete cascade,
  instagram_app_id text,
  instagram_app_secret_ciphertext text,
  redirect_uri text,
  scopes text[] not null default array[
    'instagram_business_basic',
    'instagram_business_content_publish'
  ]::text[],
  timezone text not null default 'UTC',
  notifications_enabled boolean not null default true,
  app_verified_at timestamptz,
  app_last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.accounts (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  instagram_user_id text not null,
  display_name text,
  username text not null,
  profile_picture_url text,
  account_type text,
  status text not null default 'connected',
  granted_scopes text[] not null default '{}'::text[],
  token_expires_at timestamptz,
  last_published_at timestamptz,
  published_count integer not null default 0,
  last_error_code text,
  connected_at timestamptz not null,
  removed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint accounts_published_count_nonnegative check (published_count >= 0),
  constraint accounts_status_check check (status in ('connected', 'expired', 'revoked', 'error', 'removed'))
);
create index accounts_owner_status_idx on public.accounts (owner_id, status);
create unique index accounts_owner_instagram_active_idx
  on public.accounts (owner_id, instagram_user_id) where removed_at is null;

create table public.tokens (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  account_id uuid not null references public.accounts(id) on delete cascade,
  token_ciphertext text not null,
  token_type text not null default 'user',
  scopes text[] not null default '{}'::text[],
  issued_at timestamptz,
  expires_at timestamptz,
  refreshed_at timestamptz,
  revoked_at timestamptz,
  refresh_failures integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint tokens_refresh_failures_nonnegative check (refresh_failures >= 0)
);
create index tokens_account_active_idx on public.tokens (account_id, revoked_at);
create index tokens_expiry_active_idx on public.tokens (expires_at) where revoked_at is null;

create table public.oauth_states (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  state_hash text not null unique,
  code_verifier_ciphertext text,
  redirect_after text,
  expires_at timestamptz not null,
  consumed_at timestamptz,
  created_at timestamptz not null default now(),
  constraint oauth_states_hash_length check (length(state_hash) = 64)
);
create index oauth_states_expiry_idx on public.oauth_states (expires_at);

create table public.account_health_checks (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  account_id uuid not null references public.accounts(id) on delete cascade,
  status text not null,
  details jsonb not null default '{}'::jsonb,
  checked_at timestamptz not null
);
create index account_health_account_checked_idx
  on public.account_health_checks (account_id, checked_at desc);

create table public.media (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  original_name text not null,
  display_name text not null,
  storage_bucket text not null,
  storage_key text not null,
  mime_type text not null,
  media_kind text not null,
  size_bytes bigint not null,
  duration_ms bigint,
  width integer,
  height integer,
  content_hash text,
  thumbnail_key text,
  status text not null default 'processing',
  compatibility jsonb not null default '{}'::jsonb,
  failure_reason text,
  uploaded_at timestamptz not null,
  archived_at timestamptz,
  deleted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint media_kind_check check (media_kind in ('image', 'video')),
  constraint media_status_check check (status in ('processing', 'ready', 'invalid', 'archived', 'deleting')),
  constraint media_size_positive check (size_bytes > 0),
  constraint media_dimensions_positive check (
    (width is null or width > 0) and (height is null or height > 0)
  ),
  constraint media_owner_storage_key_unique unique (owner_id, storage_key)
);
create index media_owner_created_idx on public.media (owner_id, created_at desc, id desc);
create index media_owner_kind_status_idx on public.media (owner_id, media_kind, status);
create index media_owner_hash_active_idx on public.media (owner_id, content_hash) where deleted_at is null;

create table public.media_tags (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  name text not null,
  color text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint media_tags_owner_name_unique unique (owner_id, name),
  constraint media_tags_name_length check (length(name) between 1 and 64)
);

create table public.media_tag_links (
  media_id uuid not null references public.media(id) on delete cascade,
  tag_id uuid not null references public.media_tags(id) on delete cascade,
  primary key (media_id, tag_id)
);
create index media_tag_links_tag_id_idx on public.media_tag_links (tag_id);

create table public.media_variants (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  media_id uuid not null references public.media(id) on delete cascade,
  variant_type text not null,
  storage_key text not null,
  mime_type text not null,
  size_bytes bigint not null,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint media_variants_size_positive check (size_bytes > 0)
);
create index media_variants_media_id_idx on public.media_variants (media_id);

create table public.upload_sessions (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  storage_key text not null,
  original_name text not null,
  mime_type text not null,
  expected_size_bytes bigint not null,
  status text not null default 'created',
  expires_at timestamptz not null,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint upload_sessions_status_check check (status in ('created', 'completed', 'expired', 'failed')),
  constraint upload_sessions_size_positive check (expected_size_bytes > 0)
);
create index upload_sessions_owner_status_idx on public.upload_sessions (owner_id, status);

create table public.campaigns (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  name text not null,
  description text,
  caption text,
  hashtags text[] not null default '{}'::text[],
  publication_type text not null,
  media_strategy text not null,
  posts_per_hour integer not null,
  duration_hours integer not null,
  schedule_mode text not null,
  starts_at timestamptz,
  timezone text not null,
  cover_mode text not null default 'automatic',
  custom_cover_media_id uuid references public.media(id) on delete set null,
  allow_media_reuse boolean not null default false,
  state text not null default 'draft',
  current_version integer not null default 0,
  planned_count integer not null default 0,
  succeeded_count integer not null default 0,
  failed_count integer not null default 0,
  paused_at timestamptz,
  completed_at timestamptz,
  cancelled_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint campaigns_publication_type_check check (publication_type in ('feed', 'reel', 'story')),
  constraint campaigns_media_strategy_check check (
    media_strategy in ('same_media', 'sequential', 'random_without_replacement')
  ),
  constraint campaigns_schedule_mode_check check (schedule_mode in ('now', 'scheduled')),
  constraint campaigns_cover_mode_check check (cover_mode in ('automatic', 'custom')),
  constraint campaigns_state_check check (
    state in ('draft', 'scheduled', 'running', 'paused', 'completed', 'completed_with_errors', 'cancelled')
  ),
  constraint campaigns_rates_positive check (
    posts_per_hour between 1 and 1000 and duration_hours between 1 and 168
  ),
  constraint campaigns_counts_nonnegative check (
    current_version >= 0 and planned_count >= 0 and succeeded_count >= 0 and failed_count >= 0
  )
);
create index campaigns_owner_state_created_idx on public.campaigns (owner_id, state, created_at desc);
create index campaigns_state_starts_idx on public.campaigns (state, starts_at);

create table public.campaign_versions (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  version integer not null,
  snapshot jsonb not null,
  random_seed text,
  created_at timestamptz not null,
  constraint campaign_versions_version_positive check (version > 0),
  constraint campaign_versions_campaign_version_unique unique (campaign_id, version)
);
create index campaign_versions_owner_id_idx on public.campaign_versions (owner_id);

create table public.campaign_accounts (
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  account_id uuid not null references public.accounts(id) on delete restrict,
  position integer not null,
  snapshot jsonb not null default '{}'::jsonb,
  primary key (campaign_id, account_id),
  constraint campaign_accounts_position_nonnegative check (position >= 0)
);
create index campaign_accounts_account_id_idx on public.campaign_accounts (account_id);

create table public.campaign_media (
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  media_id uuid not null references public.media(id) on delete restrict,
  position integer not null,
  snapshot jsonb not null default '{}'::jsonb,
  primary key (campaign_id, media_id),
  constraint campaign_media_position_nonnegative check (position >= 0)
);
create index campaign_media_media_id_idx on public.campaign_media (media_id);

create table public.jobs (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  campaign_version_id uuid not null references public.campaign_versions(id) on delete restrict,
  account_id uuid not null references public.accounts(id) on delete restrict,
  media_id uuid not null references public.media(id) on delete restrict,
  scheduled_at timestamptz not null,
  state text not null default 'planned',
  priority integer not null default 100,
  idempotency_key text not null unique,
  attempt_count integer not null default 0,
  next_attempt_at timestamptz,
  lease_owner text,
  lease_expires_at timestamptz,
  external_container_id text,
  external_media_id text,
  published_at timestamptz,
  last_error_class text,
  last_error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint jobs_attempt_count_nonnegative check (attempt_count >= 0),
  constraint jobs_state_check check (
    state in (
      'planned', 'queued', 'publishing', 'retry_scheduled', 'succeeded',
      'failed_permanent', 'dead_letter', 'cancelled'
    )
  )
);
create index jobs_state_scheduled_idx on public.jobs (state, scheduled_at);
create index jobs_account_scheduled_idx on public.jobs (account_id, scheduled_at);
create index jobs_campaign_state_idx on public.jobs (campaign_id, state);
create index jobs_due_idx on public.jobs (scheduled_at, priority)
  where state in ('planned', 'retry_scheduled');

create table public.job_attempts (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  job_id uuid not null references public.jobs(id) on delete cascade,
  attempt_number integer not null,
  started_at timestamptz not null,
  finished_at timestamptz,
  duration_ms bigint,
  request_operation text not null,
  response_status integer,
  external_trace_id text,
  sanitized_response jsonb,
  error_class text,
  retryable boolean not null default false,
  constraint job_attempts_number_positive check (attempt_number > 0),
  constraint job_attempts_job_number_unique unique (job_id, attempt_number)
);
create index job_attempts_owner_started_idx on public.job_attempts (owner_id, started_at desc);

create table public.campaign_logs (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  campaign_id uuid references public.campaigns(id) on delete set null,
  job_id uuid references public.jobs(id) on delete set null,
  account_id uuid references public.accounts(id) on delete set null,
  media_id uuid references public.media(id) on delete set null,
  event_type text not null,
  status text not null,
  message text,
  details jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null,
  duration_ms bigint
);
create index campaign_logs_owner_occurred_idx on public.campaign_logs (owner_id, occurred_at desc);
create index campaign_logs_campaign_occurred_idx on public.campaign_logs (campaign_id, occurred_at desc);
create index campaign_logs_status_occurred_idx on public.campaign_logs (status, occurred_at desc);

create table public.scheduler (
  name text primary key,
  lease_owner text,
  lease_expires_at timestamptz,
  last_started_at timestamptz,
  last_completed_at timestamptz,
  last_success_at timestamptz,
  last_error text,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references public.users(id) on delete set null,
  actor_id uuid references public.users(id) on delete set null,
  action text not null,
  target_type text not null,
  target_id text,
  outcome text not null,
  request_id text,
  ip_prefix text,
  before_json jsonb,
  after_json jsonb,
  metadata_json jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null
);
create index audit_logs_owner_occurred_idx on public.audit_logs (owner_id, occurred_at desc);
create index audit_logs_actor_occurred_idx on public.audit_logs (actor_id, occurred_at desc);

create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  kind text not null,
  title text not null,
  message text not null,
  severity text not null default 'info',
  data jsonb not null default '{}'::jsonb,
  read_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint notifications_severity_check check (severity in ('info', 'success', 'warning', 'error'))
);
create index notifications_owner_read_created_idx
  on public.notifications (owner_id, read_at, created_at desc);

create table public.insight_snapshots (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  account_id uuid not null references public.accounts(id) on delete cascade,
  external_media_id text,
  metric text not null,
  value double precision,
  period text,
  source_version text not null,
  captured_at timestamptz not null,
  raw_metadata jsonb not null default '{}'::jsonb
);
create index insights_owner_metric_captured_idx
  on public.insight_snapshots (owner_id, metric, captured_at desc);
create index insights_media_metric_captured_idx
  on public.insight_snapshots (external_media_id, metric, captured_at desc);

create table public.outbox_events (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references public.users(id) on delete set null,
  topic text not null,
  aggregate_type text not null,
  aggregate_id text not null,
  payload jsonb not null,
  created_at timestamptz not null,
  published_at timestamptz,
  attempts integer not null default 0,
  constraint outbox_attempts_nonnegative check (attempts >= 0)
);
create index outbox_unpublished_idx on public.outbox_events (created_at)
  where published_at is null;

create table public.plans (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  description text,
  price_monthly numeric(12,2) not null default 0,
  limits jsonb not null default '{}'::jsonb,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint plans_price_nonnegative check (price_monthly >= 0)
);

create table public.user_plans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  plan_id uuid not null references public.plans(id) on delete restrict,
  status text not null default 'active',
  starts_at timestamptz not null,
  ends_at timestamptz,
  overrides jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint user_plans_status_check check (status in ('active', 'cancelled', 'expired'))
);
create index user_plans_user_status_idx on public.user_plans (user_id, status);
create unique index user_plans_user_active_idx on public.user_plans (user_id) where status = 'active';

create or replace function public.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'users', 'roles', 'permissions', 'user_roles', 'role_permissions', 'approvals',
    'sessions', 'refresh_tokens', 'settings', 'accounts', 'tokens', 'media',
    'media_tags', 'media_variants', 'upload_sessions', 'campaigns', 'jobs',
    'scheduler', 'notifications', 'plans', 'user_plans'
  ]
  loop
    execute format(
      'create trigger %I before update on public.%I for each row execute function public.set_updated_at()',
      table_name || '_set_updated_at',
      table_name
    );
  end loop;
end;
$$;

create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.users (id, email, full_name, avatar_url, status)
  values (
    new.id,
    new.email,
    new.raw_user_meta_data ->> 'full_name',
    new.raw_user_meta_data ->> 'avatar_url',
    'pending'
  )
  on conflict (id) do update set
    email = excluded.email,
    full_name = coalesce(public.users.full_name, excluded.full_name),
    avatar_url = coalesce(public.users.avatar_url, excluded.avatar_url);

  insert into public.approvals (user_id, decision)
  values (new.id, 'pending');
  return new;
end;
$$;

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_auth_user();

insert into public.permissions (code, description) values
  ('admin:users', 'Gerenciar usuários e aprovações'),
  ('admin:plans', 'Gerenciar planos'),
  ('admin:logs', 'Consultar logs administrativos'),
  ('admin:stats', 'Consultar estatísticas globais');

insert into public.roles (name, description, is_system) values
  ('admin', 'Administrador da plataforma', true),
  ('member', 'Usuário aprovado da plataforma', true);

insert into public.role_permissions (role_id, permission_id)
select role.id, permission.id
from public.roles role
cross join public.permissions permission
where role.name = 'admin';

insert into public.plans (code, name, description, price_monthly, limits) values
  ('starter', 'Starter', 'Plano inicial', 0, '{"accounts":5,"monthly_publications":1000}'::jsonb),
  ('scale', 'Scale', 'Plano para operações em escala', 0, '{"accounts":1000,"monthly_publications":1000000}'::jsonb);

revoke all on all tables in schema public from anon;
revoke all on all sequences in schema public from anon;
grant usage on schema public to authenticated;
grant select on public.roles, public.permissions, public.role_permissions, public.plans to authenticated;

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'users', 'approvals', 'sessions', 'refresh_tokens', 'settings', 'accounts', 'tokens',
    'oauth_states', 'account_health_checks', 'media', 'media_tags', 'media_variants',
    'upload_sessions', 'campaigns', 'campaign_versions', 'jobs', 'job_attempts',
    'campaign_logs', 'audit_logs', 'notifications', 'insight_snapshots', 'outbox_events'
  ]
  loop
    execute format('alter table public.%I enable row level security', table_name);
    if table_name = 'users' then
      execute 'create policy users_own_rows on public.users for select to authenticated using ((select auth.uid()) = id)';
    elsif table_name = 'approvals' then
      execute 'create policy approvals_own_rows on public.approvals for select to authenticated using ((select auth.uid()) = user_id)';
    elsif table_name = 'sessions' or table_name = 'refresh_tokens' then
      execute format(
        'create policy %I on public.%I for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id)',
        table_name || '_own_rows',
        table_name
      );
    else
      execute format(
        'create policy %I on public.%I for all to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id)',
        table_name || '_own_rows',
        table_name
      );
    end if;
  end loop;
end;
$$;

alter table public.roles enable row level security;
alter table public.permissions enable row level security;
alter table public.user_roles enable row level security;
alter table public.role_permissions enable row level security;
alter table public.plans enable row level security;
alter table public.user_plans enable row level security;
alter table public.campaign_accounts enable row level security;
alter table public.campaign_media enable row level security;
alter table public.media_tag_links enable row level security;
alter table public.scheduler enable row level security;

create policy roles_authenticated_read on public.roles for select to authenticated using (true);
create policy permissions_authenticated_read on public.permissions for select to authenticated using (true);
create policy user_roles_own_read on public.user_roles for select to authenticated
  using ((select auth.uid()) = user_id);
create policy role_permissions_authenticated_read on public.role_permissions
  for select to authenticated using (true);
create policy plans_authenticated_read on public.plans for select to authenticated using (active);
create policy user_plans_own_read on public.user_plans for select to authenticated
  using ((select auth.uid()) = user_id);
create policy campaign_accounts_own_rows on public.campaign_accounts for all to authenticated
  using (
    exists (
      select 1 from public.campaigns
      where campaigns.id = campaign_accounts.campaign_id
        and campaigns.owner_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1 from public.campaigns
      where campaigns.id = campaign_accounts.campaign_id
        and campaigns.owner_id = (select auth.uid())
    )
  );
create policy campaign_media_own_rows on public.campaign_media for all to authenticated
  using (
    exists (
      select 1 from public.campaigns
      where campaigns.id = campaign_media.campaign_id
        and campaigns.owner_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1 from public.campaigns
      where campaigns.id = campaign_media.campaign_id
        and campaigns.owner_id = (select auth.uid())
    )
  );
create policy media_tag_links_own_rows on public.media_tag_links for all to authenticated
  using (
    exists (
      select 1 from public.media
      where media.id = media_tag_links.media_id
        and media.owner_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1 from public.media
      where media.id = media_tag_links.media_id
        and media.owner_id = (select auth.uid())
    )
  );

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'postx-media',
  'postx-media',
  false,
  1073741824,
  array['image/jpeg', 'image/png', 'image/webp', 'video/mp4', 'video/quicktime']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

create policy postx_storage_select_own
on storage.objects for select to authenticated
using (
  bucket_id = 'postx-media'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);
create policy postx_storage_insert_own
on storage.objects for insert to authenticated
with check (
  bucket_id = 'postx-media'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);
create policy postx_storage_update_own
on storage.objects for update to authenticated
using (
  bucket_id = 'postx-media'
  and (storage.foldername(name))[1] = (select auth.uid())::text
)
with check (
  bucket_id = 'postx-media'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);
create policy postx_storage_delete_own
on storage.objects for delete to authenticated
using (
  bucket_id = 'postx-media'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);
