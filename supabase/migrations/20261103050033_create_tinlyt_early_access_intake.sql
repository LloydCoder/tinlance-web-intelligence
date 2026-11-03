-- Validated by replay against the original October migration chain.
-- Upgrade the original Tinlyt early-access intake schema to the live
-- 2026-11-03 shape. The earlier 20261022072400 migration already creates
-- public.early_access_requests and tinlyt_private.early_access_rate_limits.
-- This migration is intentionally additive/transformational; do not recreate
-- the public intake table.
--
-- Live catalog reconciliation: RLS enabled with no client-facing policies;
-- service_role-only table access; private rate-limit storage; updated lifecycle
-- states; atomic bounded rate limiting.

alter table public.early_access_requests
  drop constraint if exists early_access_requests_status_check;
alter table public.early_access_requests
  drop constraint if exists early_access_requests_description_check;

update public.early_access_requests
set status = case status
  when 'approved' then 'accepted'
  when 'waitlisted' then 'reviewing'
  when 'declined' then 'rejected'
  when 'invited' then 'accepted'
  else status
end
where status in ('approved', 'waitlisted', 'declined', 'invited');

alter table public.early_access_requests
  add constraint early_access_requests_status_check
  check (status = any (array['new', 'reviewing', 'accepted', 'rejected', 'withdrawn']));

drop index if exists public.early_access_requests_status_created_idx;
create index if not exists early_access_requests_created_at_idx
  on public.early_access_requests (created_at desc);
create index if not exists early_access_requests_status_created_at_idx
  on public.early_access_requests (status, created_at desc);

comment on table public.early_access_requests is
  'Tinlyt public early-access requests. Contains personal data; server-only access through service_role.';

alter table public.early_access_requests enable row level security;
revoke all on table public.early_access_requests from public, anon, authenticated, service_role;
grant all privileges on table public.early_access_requests to service_role;

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
grant usage on schema private to service_role;

do $migration$
begin
  if to_regclass('private.early_access_rate_limits') is not null
     and to_regclass('tinlyt_private.early_access_rate_limits') is not null then
    raise exception 'Both private and tinlyt_private rate-limit tables exist; refusing ambiguous migration';
  elsif to_regclass('private.early_access_rate_limits') is null
     and to_regclass('tinlyt_private.early_access_rate_limits') is not null then
    alter table tinlyt_private.early_access_rate_limits set schema private;
  end if;
end;
$migration$;

create table if not exists private.early_access_rate_limits (
  key_hash text primary key
    constraint early_access_rate_limits_key_hash_check
    check (key_hash ~ '^[0-9a-f]{64}$'),
  window_started_at timestamptz not null,
  request_count integer not null
    constraint early_access_rate_limits_request_count_check
    check (request_count >= 1),
  updated_at timestamptz not null default now()
);

drop index if exists private.early_access_rate_limits_updated_idx;
comment on table private.early_access_rate_limits is
  'Private HMAC-keyed rate-limit counters for Tinlyt early-access intake; never expose through the Data API.';

alter table private.early_access_rate_limits enable row level security;
revoke all on table private.early_access_rate_limits from public, anon, authenticated, service_role;
grant insert, select, update on table private.early_access_rate_limits to service_role;

-- PostgreSQL does not allow CREATE OR REPLACE to remove existing argument defaults.
-- Drop and recreate this externally-called function with the explicit required arguments.
drop function if exists public.consume_early_access_rate_limit(text, integer, integer);

create function public.consume_early_access_rate_limit(
  p_key_hash text,
  p_limit integer,
  p_window_seconds integer
)
returns boolean
language plpgsql
security invoker
set search_path = ''
as $function$
declare
  v_allowed boolean;
begin
  if p_key_hash is null or p_key_hash !~ '^[0-9a-f]{64}$'
     or p_limit is null or p_limit < 1 or p_limit > 1000
     or p_window_seconds is null or p_window_seconds < 60 or p_window_seconds > 86400 then
    raise exception 'Invalid rate-limit parameters' using errcode = '22023';
  end if;

  insert into private.early_access_rate_limits as limits (
    key_hash, window_started_at, request_count, updated_at
  )
  values (p_key_hash, now(), 1, now())
  on conflict (key_hash) do update
  set
    request_count = case
      when limits.window_started_at <= now() - make_interval(secs => p_window_seconds) then 1
      else limits.request_count + 1
    end,
    window_started_at = case
      when limits.window_started_at <= now() - make_interval(secs => p_window_seconds) then now()
      else limits.window_started_at
    end,
    updated_at = now()
  returning request_count <= p_limit into v_allowed;

  return v_allowed;
end;
$function$;

revoke all on function public.consume_early_access_rate_limit(text, integer, integer)
  from public, anon, authenticated;
grant execute on function public.consume_early_access_rate_limit(text, integer, integer)
  to service_role;
