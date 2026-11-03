begin;
select plan(31);

select has_table('public', 'early_access_requests', 'early-access table exists');
select ok(
  (select relrowsecurity from pg_class where oid = 'public.early_access_requests'::regclass),
  'RLS is enabled on the exposed intake table'
);

select ok(not has_table_privilege('anon', 'public.early_access_requests', 'SELECT'), 'anon cannot select requests');
select ok(not has_table_privilege('anon', 'public.early_access_requests', 'INSERT'), 'anon cannot insert requests');
select ok(not has_table_privilege('anon', 'public.early_access_requests', 'UPDATE'), 'anon cannot update requests');
select ok(not has_table_privilege('anon', 'public.early_access_requests', 'DELETE'), 'anon cannot delete requests');
select ok(not has_table_privilege('authenticated', 'public.early_access_requests', 'SELECT'), 'authenticated cannot select requests');
select ok(not has_table_privilege('authenticated', 'public.early_access_requests', 'INSERT'), 'authenticated cannot insert requests');
select ok(not has_table_privilege('authenticated', 'public.early_access_requests', 'UPDATE'), 'authenticated cannot update requests');
select ok(not has_table_privilege('authenticated', 'public.early_access_requests', 'DELETE'), 'authenticated cannot delete requests');

select ok(not has_schema_privilege('anon', 'private', 'USAGE'), 'anon cannot use the private schema');
select ok(not has_schema_privilege('authenticated', 'private', 'USAGE'), 'authenticated cannot use the private schema');
select ok(not has_function_privilege('anon', 'public.consume_early_access_rate_limit(text,integer,integer)', 'EXECUTE'), 'anon cannot execute rate-limit RPC');
select ok(not has_function_privilege('authenticated', 'public.consume_early_access_rate_limit(text,integer,integer)', 'EXECUTE'), 'authenticated cannot execute rate-limit RPC');
select ok(has_function_privilege('service_role', 'public.consume_early_access_rate_limit(text,integer,integer)', 'EXECUTE'), 'server role can execute rate-limit RPC');
select ok(has_table_privilege('service_role', 'public.early_access_requests', 'INSERT'), 'server role can insert requests');
select ok(has_column_privilege('service_role', 'public.early_access_requests', 'id', 'SELECT'), 'server role can read generated request IDs');
select ok(has_column_privilege('service_role', 'public.early_access_requests', 'created_at', 'SELECT'), 'server role can read creation timestamps');
select ok(not has_column_privilege('service_role', 'public.early_access_requests', 'email', 'SELECT'), 'server role cannot read stored email through broad table select');
select ok(has_column_privilege('service_role', 'public.early_access_requests', 'notification_status', 'UPDATE'), 'server role can update notification status');
select ok(not has_column_privilege('service_role', 'public.early_access_requests', 'status', 'UPDATE'), 'request endpoint cannot change review status');
select ok(not has_table_privilege('service_role', 'public.early_access_requests', 'DELETE'), 'request endpoint cannot delete leads');

select ok(public.consume_early_access_rate_limit(repeat('a', 64), 2, 900), 'first request within limit is allowed');
select ok(public.consume_early_access_rate_limit(repeat('a', 64), 2, 900), 'second request within limit is allowed');
select ok(not public.consume_early_access_rate_limit(repeat('a', 64), 2, 900), 'request beyond the limit is denied');


select ok(exists (select 1 from pg_extension where extname = 'pg_cron'), 'pg_cron is enabled');
select ok(exists (select 1 from cron.job where jobname = 'tinlyt-early-access-retention'), 'daily retention job is scheduled');
select ok(not has_function_privilege('anon', 'private.purge_early_access_data()', 'EXECUTE'), 'anon cannot execute retention function');

insert into public.early_access_requests
  (name, email, use_case, consent_at, privacy_notice_version, marketing_opt_in, source, created_at)
values
  ('Expired Test Request', 'expired-retention@example.test', 'other', now(), 'test', false, 'test', now() - interval '13 months'),
  ('Recent Test Request', 'recent-retention@example.test', 'other', now(), 'test', false, 'test', now());

insert into private.early_access_rate_limits
  (key_hash, window_started_at, request_count, updated_at)
values
  (repeat('b', 64), now() - interval '25 hours', 1, now() - interval '25 hours');

select private.purge_early_access_data();
select ok(not exists (select 1 from public.early_access_requests where email = 'expired-retention@example.test'), 'requests older than 12 months are deleted');
select ok(exists (select 1 from public.early_access_requests where email = 'recent-retention@example.test'), 'requests within 12 months are retained');
select ok(not exists (select 1 from private.early_access_rate_limits where key_hash = repeat('b', 64)), 'rate-limit hashes older than 24 hours are deleted');

select * from finish();
rollback;
