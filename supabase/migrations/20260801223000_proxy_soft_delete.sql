alter table public.proxies
  add column if not exists removed_at timestamptz;

create index if not exists proxies_owner_active_idx
  on public.proxies (owner_id, created_at desc)
  where removed_at is null;
