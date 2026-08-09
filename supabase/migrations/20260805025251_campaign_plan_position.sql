alter table public.jobs
  add column if not exists plan_position bigint;

with ranked_jobs as (
  select
    id,
    row_number() over (
      partition by campaign_version_id
      order by scheduled_at, rotation_slot, created_at, id
    ) - 1 as plan_position
  from public.jobs
)
update public.jobs as jobs
set plan_position = ranked_jobs.plan_position
from ranked_jobs
where jobs.id = ranked_jobs.id
  and jobs.plan_position is null;

alter table public.jobs
  alter column plan_position set not null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'jobs_plan_position_nonnegative'
      and conrelid = 'public.jobs'::regclass
  ) then
    alter table public.jobs
      add constraint jobs_plan_position_nonnegative
      check (plan_position >= 0) not valid;
  end if;
end
$$;

alter table public.jobs
  validate constraint jobs_plan_position_nonnegative;

create unique index if not exists uq_jobs_campaign_version_plan_position
  on public.jobs (campaign_version_id, plan_position);

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'uq_jobs_campaign_version_plan_position'
      and conrelid = 'public.jobs'::regclass
  ) then
    alter table public.jobs
      add constraint uq_jobs_campaign_version_plan_position
      unique using index uq_jobs_campaign_version_plan_position;
  end if;
end
$$;
