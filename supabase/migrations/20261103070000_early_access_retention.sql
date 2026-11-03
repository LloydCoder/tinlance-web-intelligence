-- Enforce the published early-access retention schedule.
-- Applicant records expire 12 months after submission. Pseudonymous rate-limit
-- counters expire after 24 hours without an update. The maintenance function
-- is private and callable only by the database owner / scheduled job.

create extension if not exists pg_cron;

create or replace function private.purge_early_access_data()
returns void
language plpgsql
security definer
set search_path = ''
as $function$
begin
  delete from public.early_access_requests
  where created_at < now() - interval '12 months';

  delete from private.early_access_rate_limits
  where updated_at < now() - interval '24 hours';
end;
$function$;

revoke all on function private.purge_early_access_data()
  from public, anon, authenticated, service_role;

select cron.schedule(
  'tinlyt-early-access-retention',
  '30 2 * * *',
  'select private.purge_early_access_data();'
);
