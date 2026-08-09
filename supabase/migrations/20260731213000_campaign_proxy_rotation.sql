alter table public.campaigns
  drop constraint campaigns_proxy_mode_check,
  drop constraint campaigns_proxy_selection_check,
  add column proxy_rotation_every integer not null default 1,
  add constraint campaigns_proxy_mode_check check (proxy_mode in ('none','account','specific','fixed','rotate_per_post','rotate_every_n_posts')),
  add constraint campaigns_proxy_rotation_every_check check (proxy_rotation_every between 1 and 1000),
  add constraint campaigns_proxy_selection_check check (
    (proxy_mode in ('specific','fixed') and proxy_id is not null)
    or (proxy_mode in ('none','account','rotate_per_post','rotate_every_n_posts') and proxy_id is null)
  );

create table public.campaign_proxies (
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  proxy_id uuid not null references public.proxies(id) on delete restrict,
  priority integer not null,
  primary key (campaign_id, proxy_id),
  constraint campaign_proxies_priority_check check (priority between 1 and 1000000)
);
create index campaign_proxies_proxy_id_idx on public.campaign_proxies(proxy_id);

create table public.campaign_proxy_assignments (
  campaign_version_id uuid not null references public.campaign_versions(id) on delete cascade,
  rotation_slot integer not null,
  proxy_id uuid not null references public.proxies(id) on delete restrict,
  selected_at timestamptz not null default now(),
  primary key (campaign_version_id, rotation_slot),
  constraint campaign_proxy_assignments_slot_check check (rotation_slot >= 0)
);
create index campaign_proxy_assignments_proxy_id_idx on public.campaign_proxy_assignments(proxy_id);

alter table public.jobs add column rotation_slot integer not null default 0,
  add constraint jobs_rotation_slot_check check (rotation_slot >= 0);
create index jobs_campaign_version_rotation_slot_idx on public.jobs(campaign_version_id, rotation_slot);

alter table public.campaign_proxies enable row level security;
alter table public.campaign_proxy_assignments enable row level security;
create policy campaign_proxies_own_rows on public.campaign_proxies for all to authenticated
  using (exists (select 1 from public.campaigns where campaigns.id = campaign_proxies.campaign_id and campaigns.owner_id = (select auth.uid())))
  with check (exists (select 1 from public.campaigns where campaigns.id = campaign_proxies.campaign_id and campaigns.owner_id = (select auth.uid())) and exists (select 1 from public.proxies where proxies.id = campaign_proxies.proxy_id and proxies.owner_id = (select auth.uid())));
create policy campaign_proxy_assignments_own_rows on public.campaign_proxy_assignments for select to authenticated
  using (exists (select 1 from public.campaign_versions join public.campaigns on campaigns.id = campaign_versions.campaign_id where campaign_versions.id = campaign_proxy_assignments.campaign_version_id and campaigns.owner_id = (select auth.uid())));
