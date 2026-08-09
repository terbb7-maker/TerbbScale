create index if not exists jobs_owner_published_media_idx
  on public.jobs (owner_id, published_at)
  include (external_media_id)
  where state = 'succeeded'
    and published_at is not null
    and external_media_id is not null;
