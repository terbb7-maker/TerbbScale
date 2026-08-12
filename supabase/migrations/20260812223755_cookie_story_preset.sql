create table public.cookie_story_presets (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  media_id uuid not null references public.media(id) on delete cascade,
  link_url text not null,
  link_title text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint cookie_story_presets_owner_id_key unique (owner_id),
  constraint cookie_story_presets_link_title_length check (
    link_title is null or char_length(link_title) between 1 and 80
  ),
  constraint cookie_story_presets_https_link check (
    link_url ~ '^https://[^[:space:]]+$'
  )
);

create index cookie_story_presets_media_id_idx
  on public.cookie_story_presets (media_id);

create trigger cookie_story_presets_set_updated_at
before update on public.cookie_story_presets
for each row execute function public.set_updated_at();

alter table public.cookie_story_presets enable row level security;

create policy cookie_story_presets_own_rows
on public.cookie_story_presets
for all
to authenticated
using ((select auth.uid()) = owner_id)
with check ((select auth.uid()) = owner_id);

revoke all on public.cookie_story_presets from anon, authenticated;
