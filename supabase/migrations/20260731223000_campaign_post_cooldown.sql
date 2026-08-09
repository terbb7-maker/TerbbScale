alter table public.campaigns
  add column schedule_distribution text not null default 'even',
  add column post_cooldown_minutes integer not null default 1,
  add constraint campaigns_schedule_distribution_check check (schedule_distribution in ('even','burst','cooldown')),
  add constraint campaigns_post_cooldown_minutes_check check (post_cooldown_minutes between 1 and 60);
