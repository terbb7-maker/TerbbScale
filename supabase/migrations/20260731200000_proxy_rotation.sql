-- Multiple proxies may be assigned to each account. The legacy one-proxy
-- association remains as the first member of the new pool.
alter table public.accounts
  add column proxy_rotation_mode text not null default 'fixed',
  add column proxy_rotation_every integer not null default 1,
  add column proxy_rotation_counter integer not null default 0,
  add column proxy_rotation_current_proxy_id uuid references public.proxies(id) on delete set null,
  add constraint accounts_proxy_rotation_mode_check
    check (proxy_rotation_mode in ('fixed', 'per_post', 'every_n_posts')),
  add constraint accounts_proxy_rotation_every_check
    check (proxy_rotation_every between 1 and 1000),
  add constraint accounts_proxy_rotation_counter_check
    check (proxy_rotation_counter >= 0);

alter table public.proxies
  add column cooldown_until timestamptz,
  add column consecutive_failures integer not null default 0,
  add constraint proxies_consecutive_failures_check check (consecutive_failures >= 0);

alter table public.account_proxies
  drop constraint account_proxies_pkey,
  add column priority integer not null default 100,
  add column is_active boolean not null default true,
  add column last_selected_at timestamptz,
  add constraint account_proxies_priority_check check (priority between 1 and 1000000),
  add primary key (account_id, proxy_id);

create index account_proxies_rotation_idx
  on public.account_proxies (account_id, priority, last_selected_at)
  where is_active;

alter table public.jobs
  add column proxy_id uuid references public.proxies(id) on delete set null;
alter table public.job_attempts
  add column proxy_id uuid references public.proxies(id) on delete set null;
create index jobs_proxy_id_idx on public.jobs (proxy_id) where proxy_id is not null;
create index job_attempts_proxy_id_idx on public.job_attempts (proxy_id) where proxy_id is not null;
