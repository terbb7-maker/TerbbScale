create table public.proxies (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  name text not null,
  protocol text not null,
  host text not null,
  port integer not null,
  username text,
  password_ciphertext text,
  country text,
  notes text,
  is_active boolean not null default true,
  status text not null default 'unknown',
  last_error text,
  last_check timestamptz,
  latency_ms integer,
  public_ip text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint proxies_protocol_check check (protocol in ('http', 'https', 'socks5')),
  constraint proxies_port_check check (port between 1 and 65535),
  constraint proxies_status_check check (status in ('unknown', 'online', 'offline')),
  constraint proxies_name_not_blank check (length(btrim(name)) > 0),
  constraint proxies_host_not_blank check (length(btrim(host)) > 0),
  constraint proxies_latency_nonnegative check (latency_ms is null or latency_ms >= 0)
);
create index proxies_owner_created_idx on public.proxies (owner_id, created_at desc);
create index proxies_active_health_idx on public.proxies (is_active, last_check) where is_active;

create table public.account_proxies (
  account_id uuid primary key references public.accounts(id) on delete cascade,
  proxy_id uuid not null references public.proxies(id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index account_proxies_proxy_id_idx on public.account_proxies (proxy_id);

alter table public.campaigns
  add column proxy_mode text not null default 'none',
  add column proxy_id uuid references public.proxies(id) on delete restrict,
  add constraint campaigns_proxy_mode_check check (proxy_mode in ('none', 'account', 'specific')),
  add constraint campaigns_proxy_selection_check check (
    (proxy_mode = 'specific' and proxy_id is not null)
    or (proxy_mode in ('none', 'account') and proxy_id is null)
  );
create index campaigns_owner_proxy_idx on public.campaigns (owner_id, proxy_mode) where proxy_mode <> 'none';

create trigger set_proxies_updated_at before update on public.proxies
for each row execute function public.set_updated_at();
create trigger set_account_proxies_updated_at before update on public.account_proxies
for each row execute function public.set_updated_at();

alter table public.proxies enable row level security;
alter table public.account_proxies enable row level security;
create policy proxies_own_rows on public.proxies for all to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);
create policy account_proxies_own_rows on public.account_proxies for all to authenticated
  using (
    exists (
      select 1 from public.accounts
      where accounts.id = account_proxies.account_id
        and accounts.owner_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1 from public.accounts
      where accounts.id = account_proxies.account_id
        and accounts.owner_id = (select auth.uid())
    )
    and exists (
      select 1 from public.proxies
      where proxies.id = account_proxies.proxy_id
        and proxies.owner_id = (select auth.uid())
    )
  );
