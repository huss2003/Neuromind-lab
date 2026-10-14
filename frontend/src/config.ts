/** Feature switches. All are public build-time values (no secrets). Sign-up and social sign-in are off unless the deployment turns them on,
 *  because they also need matching settings in the Supabase dashboard (email confirmation, provider keys). */
export const SIGNUP_ENABLED = import.meta.env.VITE_ENABLE_SIGNUP === 'true';
export const OAUTH_PROVIDERS: string[] = (import.meta.env.VITE_OAUTH_PROVIDERS ?? '').split(',').map((p: string) => p.trim()).filter(Boolean);
