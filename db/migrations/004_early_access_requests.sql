-- Tinlyt public early-access intake. Apply only to the database intentionally selected for Tinlyt.
-- Public browser roles receive no table privileges. The serverless endpoint uses a server-only secret key.
create table if not exists public.early_access_requests (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 2 and 120),
  email text not null check (char_length(email) between 3 and 254),
  email_hash text not null check (email_hash ~ '^[a-f0-9]{64}$'),
  company text,
  role text,
  use_case text not null check (char_length(use_case) between 1 and 80),
  description text check (description is null or char_length(description) <= 2000),
  consent_at timestamptz not null,
  marketing_opt_in boolean not null default false,
  source text not null default 'tinlyt-public-website',
  status text not null default 'new'
    check (status in ('new', 'reviewing', 'approved', 'waitlisted', 'declined', 'invited')),
  notification_status text not null default 'pending'
    check (notification_status in ('pending', 'sent', 'failed')),
  confirmation_status text not null default 'pending'
    check (confirmation_status in ('pending', 'sent', 'failed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create unique index if not exists early_access_requests_email_hash_uidx
  on public.early_access_requests (email_hash);
create index if not exists early_access_requests_status_created_idx
  on public.early_access_requests (status, created_at desc);
alter table public.early_access_requests enable row level security;
revoke all on table public.early_access_requests from anon, authenticated, public;
grant all on table public.early_access_requests to service_role;
comment on table public.early_access_requests is
  'Private Tinlyt early-access intake; accessible only to privileged server-side processing and administrators.';


-- Store only salted hashes for a small durable anti-abuse rate-limit window.
create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
grant usage on schema private to service_role;
create table if not exists private.early_access_rate_limits (
  key_hash text primary key check (key_hash ~ '^[a-f0-9]{64}$'),
  window_started_at timestamptz not null,
  request_count integer not null check (request_count >= 1),
  updated_at timestamptz not null default now()
);
alter table private.early_access_rate_limits enable row level security;
revoke all on table private.early_access_rate_limits from public, anon, authenticated;
grant all on table private.early_access_rate_limits to service_role;

create or replace function public.consume_early_access_rate_limit(
  p_key_hash text,
  p_limit integer default 5,
  p_window_seconds integer default 900
) returns boolean
language plpgsql
security definer
set search_path = ''
as $function$
declare
  allowed boolean;
  current_time timestamptz := clock_timestamp();
begin
  if p_key_hash !~ '^[a-f0-9]{64}$' or p_limit < 1 or p_limit > 20
     or p_window_seconds < 60 or p_window_seconds > 3600 then
    return false;
  end if;
  insert into private.early_access_rate_limits as current_limit
    (key_hash, window_started_at, request_count, updated_at)
  values (p_key_hash, current_time, 1, current_time)
  on conflict (key_hash) do update
    set window_started_at = case
          when current_limit.window_started_at <= current_time - make_interval(secs => p_window_seconds)
          then current_time else current_limit.window_started_at end,
        request_count = case
          when current_limit.window_started_at <= current_time - make_interval(secs => p_window_seconds)
          then 1 else current_limit.request_count + 1 end,
        updated_at = current_time
  returning request_count <= p_limit into allowed;
  return allowed;
end;
$function$;

revoke all on function public.consume_early_access_rate_limit(text, integer, integer) from public, anon, authenticated;
grant execute on function public.consume_early_access_rate_limit(text, integer, integer) to service_role;
