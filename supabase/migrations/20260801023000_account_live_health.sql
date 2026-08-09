alter table public.accounts
  add column if not exists health_status text not null default 'unknown',
  add column if not exists health_confidence text not null default 'unknown',
  add column if not exists health_source text,
  add column if not exists health_checked_at timestamptz,
  add column if not exists health_last_success_at timestamptz,
  add column if not exists health_next_check_at timestamptz not null default now(),
  add column if not exists health_consecutive_failures integer not null default 0,
  add column if not exists health_error_code text,
  add column if not exists health_error_subcode text,
  add column if not exists health_message text,
  add column if not exists health_action_required text;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'accounts_health_status_check'
      and conrelid = 'public.accounts'::regclass
  ) then
    alter table public.accounts add constraint accounts_health_status_check check (
      health_status in (
        'unknown', 'checking', 'operational', 'reauth_required',
        'action_required', 'permission_required', 'temporarily_restricted',
        'possibly_suspended', 'provider_unavailable'
      )
    );
  end if;

  if not exists (
    select 1 from pg_constraint
    where conname = 'accounts_health_confidence_check'
      and conrelid = 'public.accounts'::regclass
  ) then
    alter table public.accounts add constraint accounts_health_confidence_check check (
      health_confidence in ('unknown', 'inferred', 'confirmed')
    );
  end if;

  if not exists (
    select 1 from pg_constraint
    where conname = 'accounts_health_failures_nonnegative'
      and conrelid = 'public.accounts'::regclass
  ) then
    alter table public.accounts add constraint accounts_health_failures_nonnegative check (
      health_consecutive_failures >= 0
    );
  end if;
end;
$$;

create index if not exists accounts_health_due_idx
  on public.accounts (health_next_check_at, id)
  where removed_at is null;

create index if not exists accounts_owner_health_idx
  on public.accounts (owner_id, health_status)
  where removed_at is null;

create index if not exists account_health_owner_checked_idx
  on public.account_health_checks (owner_id, checked_at desc);
