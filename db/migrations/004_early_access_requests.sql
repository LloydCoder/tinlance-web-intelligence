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
