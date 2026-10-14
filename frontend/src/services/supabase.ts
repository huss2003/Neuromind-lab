import { createClient } from '@supabase/supabase-js';

// Only public (anon/publishable) values belong in VITE_* variables.
const url = import.meta.env.VITE_SUPABASE_URL ?? 'http://localhost:54321';
const key = import.meta.env.VITE_SUPABASE_ANON_KEY ?? 'missing-anon-key';

export const supabase = createClient(url, key);
