-- Trigger function must not be callable via /rest/v1/rpc
revoke execute on function public.handle_new_user() from public, anon, authenticated;
