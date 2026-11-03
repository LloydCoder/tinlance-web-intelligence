-- Tighten the intake API role to the exact operations used by the
-- public submission endpoint. The baseline intentionally reflects the
-- original live catalog; this forward migration narrows its privileges.
revoke all on table public.early_access_requests from service_role;
grant insert on table public.early_access_requests to service_role;
grant select (id, created_at) on table public.early_access_requests to service_role;
grant update (notification_status, confirmation_status, updated_at)
  on table public.early_access_requests to service_role;
