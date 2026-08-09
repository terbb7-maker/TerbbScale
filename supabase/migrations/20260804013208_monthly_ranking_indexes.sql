create index if not exists jobs_published_owner_ranking_idx
  on public.jobs (published_at, owner_id)
  include (external_media_id)
  where state = 'succeeded'
    and published_at is not null;

create index if not exists insights_owner_media_metric_captured_idx
  on public.insight_snapshots (
    owner_id,
    external_media_id,
    metric,
    captured_at,
    id
  )
  include (value)
  where external_media_id is not null
    and metric in ('views', 'reach', 'likes', 'comments', 'shares', 'saved');
