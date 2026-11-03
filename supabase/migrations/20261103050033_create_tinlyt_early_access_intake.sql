-- Reconstructed from the live Tinlyt-Early-Access project catalog on 2026-11-03.
-- This migration is the source-of-truth representation of the already-applied
-- migration 20261103050033_create_tinlyt_early_access_intake.
-- The tables intentionally have RLS enabled with no client-facing policies:
-- access is restricted to the server-side service_role.

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
grant usage on schema private to service_role;

create table public.early_access_requests (
  id uuid primary key default gen_random_uuid(),
  name text not null constraint early_access_requests_name_check
    check (char_length(name) >= 2 and char_length(name) <= 120),
  email text not null constraint early_access_requests_email_check
    check (char_length(email) >= 3 and char_length(email) <= 254),
  company text,
  role text,
  use_case text not null constraint early_access_requests_use_case_check
    check (use_case = any (array[
      'web-research',
      'competitive-intelligence',
      'due-diligence',
      'investigations',
      'data-extraction',
      'agent-integration',
      'other'
    ])),
  description text,
  consent_at timestamptz not null,
  privacy_notice_version text not null,
  marketing_opt_in boolean not null default false,
  marketing_opt_in_at timestamptz,
  source text not null default 'tinlyt-public-website',
  status text not null default 'new'
    constraint early_access_requests_status_check
    check (status = any (array['new', 'reviewing', 'accepted', 'rejected', 'withdrawn'])),
  notification_status text not null default 'pending'
    constraint early_access_requests_notification_status_check
    check (notification_status = any (array['pending', 'sent', 'failed'])),
  confirmation_status text not null default 'pending'
    constraint early_access_requests_confirmation_status_check
    check (confirmation_status = any (array['pending', 'sent', 'failed'])),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint early_access_marketing_consent_consistent check (
    (marketing_opt_in = false and marketing_opt_in_at is null)
    or
    (marketing_opt_in = true and marketing_opt_in_at is not null)
  )
);

comment on table public.early_access_requests is
  'Tinlyt public early-access requests. Contains personal data; server-only access through service_role.';

create unique index early_access_requests_email_lower_uidx
  on public.early_access_requests (lower(email));
create index early_access_requests_created_at_idx
  on public.early_access_requests (created_at desc);
create index early_access_requests_status_created_at_idx
  on public.early_access_requests (status, created_at desc);

alter table public.early_access_requests enable row level security;
revoke all on table public.early_access_requests from anon, authenticated;
grant all privileges on table public.early_access_requests to service_role;

create table private.early_access_rate_limits (
  key_hash text primary key
    constraint early_access_rate_limits_key_hash_check
    check (key_hash ~ '^[0-9a-f]{64}$'),
  window_started_at timestamptz not null,
  request_count integer not null
    constraint early_access_rate_limits_request_count_check
    check (request_count >= 1),
  updated_at timestamptz not null default now()
);

comment on table private.early_access_rate_limits is
  'Private HMAC-keyed rate-limit counters for Tinlyt early-access intake; never expose through the Data API.';

alter table private.early_access_rate_limits enable row level security;
revoke all on table private.early_access_rate_limits from anon, authenticated;
grant insert, select, update on table private.early_access_rate_limits to service_role;

create or replace function public.consume_early_access_rate_limit(
  p_key_hash text,
  p_limit integer,
  p_window_seconds integer
)
returns boolean
language plpgsql
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
