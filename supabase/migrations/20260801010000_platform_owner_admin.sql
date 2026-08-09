-- A plataforma possui exatamente um proprietário. Esta conta mantém acesso total
-- independentemente de associações de papéis e não pode ser desativada pela API.
alter table public.users
  add column if not exists is_platform_owner boolean not null default false;

create unique index if not exists users_single_platform_owner_idx
  on public.users ((is_platform_owner))
  where is_platform_owner;

do $$
declare
  owner_user_id uuid;
  admin_role_id uuid;
begin
  select id into owner_user_id
  from public.users
  where lower(email) = lower('terbb7@gmail.com')
    and deleted_at is null;

  if owner_user_id is null then
    raise exception 'Platform owner account was not found';
  end if;

  update public.users
  set is_platform_owner = true,
      status = 'active',
      approved_at = coalesce(approved_at, now()),
      suspended_at = null
  where id = owner_user_id;

  select id into admin_role_id from public.roles where name = 'admin';
  if admin_role_id is null then
    raise exception 'Admin role was not found';
  end if;

  insert into public.user_roles (user_id, role_id, granted_by)
  values (owner_user_id, admin_role_id, owner_user_id)
  on conflict (user_id, role_id) do nothing;
end;
$$;

-- Esta função é acionada somente pelo gatilho de criação do Supabase Auth.
-- Ela não deve ficar exposta como RPC pública.
revoke execute on function public.handle_new_auth_user() from public, anon, authenticated;
