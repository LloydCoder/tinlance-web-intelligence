-- Tinlyt public early-access intake. Apply only to the database intentionally selected for Tinlyt.
-- Browser roles receive no table/function privileges. Only server-side service_role can access this intake.
create table if not exists public.early_access_requests (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 2 and 120),
  email text not null check (char_length(email) between 3 and 254),
  company text,
  role text,
  use_case text not null check (use_case in (
    'web-research', 'competitive-intelligence', 'due-diligence',
    'investigations', 'data-extraction', 'agent-integration', 'other'
  )),
  description text check (description is null or char_length(description) <= 2000),
  consent_at timestamptz not null,
  privacy_notice_version text not null,
  marketing_opt_in boolean not null default false,
  marketing_opt_in_at timestamptz,
  source text not null default 'tinlyt-public-website',
  status text not null default 'new'
    check (status in ('new', 'reviewing', 'approved', 'waitlisted', 'declined', 'invited')),
  notification_status text not null default 'pending'
    check (notification_status in ('pending', 'sent', 'failed')),
  confirmation_status text not null default 'pending'
    check (confirmation_status in ('pending', 'sent', 'failed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint early_access_marketing_consent_consistent check (
    (marketing_opt_in and marketing_opt_in_at is not null)
    or (not marketing_opt_in and marketing_opt_in_at is null)
  )
);

create unique index if not exists early_access_requests_email_lower_uidx
  on public.early_access_requests (lower(email));
create index if not exists early_access_requests_status_created_idx
  on public.early_access_requests (status, created_at desc);

alter table public.early_access_requests enable row level security;
revoke all on table public.early_access_requests from public, anon, authenticated;
revoke all on table public.early_access_requests from service_role;
grant insert on table public.early_access_requests to service_role;
grant select (id, created_at) on table public.early_access_requests to service_role;
grant update (notification_status, confirmation_status, updated_at)
  on table public.early_access_requests to service_role;

comment on table public.early_access_requests is
  'Tinlyt early-access intake. Browser roles have no privileges; server-side service_role only.';

-- The dedicated tinlyt_private schema is not exposed through the Supabase Data API by default.
create schema if not exists tinlyt_private;
revoke all on schema tinlyt_private from public, anon, authenticated;
grant usage on schema tinlyt_private to service_role;

create table if not exists tinlyt_private.early_access_rate_limits (
  key_hash text primary key check (key_hash ~ '^[a-f0-9]{64}$'),
  window_started_at timestamptz not null,
  request_count integer not null check (request_count >= 1),
  updated_at timestamptz not null default now()
);
create index if not exists early_access_rate_limits_updated_idx
  on tinlyt_private.early_access_rate_limits (updated_at);
alter table tinlyt_private.early_access_rate_limits enable row level security;
revoke all on table tinlyt_private.early_access_rate_limits from public, anon, authenticated;
grant select, insert, update, delete on table tinlyt_private.early_access_rate_limits to service_role;

-- SECURITY INVOKER is intentional: the service_role RPC caller has the explicit table grants.
-- EXECUTE is revoked from PUBLIC and browser roles; never expose this RPC to anonymous clients.
create or replace function public.consume_early_access_rate_limit(
  p_key_hash text,
  p_limit integer default 5,
  p_window_seconds integer default 900
) returns boolean
language plpgsql
security invoker
set search_path = ''
as $function$
declare
  allowed boolean;
  current_time timestamptz := pg_catalog.clock_timestamp();
begin
  if p_key_hash !~ '^[a-f0-9]{64}$' or p_limit < 1 or p_limit > 20
     or p_window_seconds < 60 or p_window_seconds > 3600 then
    return false;
  end if;

  delete from tinlyt_private.early_access_rate_limits
   where updated_at < current_time - interval '24 hours';

  insert into tinlyt_private.early_access_rate_limits as current_limit
    (key_hash, window_started_at, request_count, updated_at)
  values (p_key_hash, current_time, 1, current_time)
  on conflict (key_hash) do update
    set window_started_at = case
          when current_limit.window_started_at <= current_time - pg_catalog.make_interval(secs => p_window_seconds)
          then current_time else current_limit.window_started_at end,
        request_count = case
          when current_limit.window_started_at <= current_time - pg_catalog.make_interval(secs => p_window_seconds)
          then 1 else current_limit.request_count + 1 end,
        updated_at = current_time
  returning request_count <= p_limit into allowed;

  return allowed;
end;
$function$;

revoke all on function public.consume_early_access_rate_limit(text, integer, integer) from public, anon, authenticated;
grant execute on function public.consume_early_access_rate_limit(text, integer, integer) to service_role;
