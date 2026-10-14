import { useQueryClient } from '@tanstack/react-query';
import type { Session } from '@supabase/supabase-js';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { SESSION_EXPIRED_EVENT, apiFetch } from '../services/api';
import { supabase } from '../services/supabase';

export type Role = 'learner' | 'teacher' | 'admin';
export interface Profile { id: string; role: Role; email: string; display_name: string }
interface AuthValue {
  loading: boolean;
  session: Session | null;
  profile: Profile | null;
  role: Role | null; // from the server (/me): used only to show/hide UI; the API enforces access
  expired: boolean;
  signOut: () => Promise<void>;
}
const Ctx = createContext<AuthValue>({ loading: true, session: null, profile: null, role: null, expired: false, signOut: async () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [expired, setExpired] = useState(false);

  // Clear every trace of the previous user (cached server data and profile) on any sign-out.
  const clearUserState = useCallback(() => {
    setProfile(null);
    queryClient.clear();
  }, [queryClient]);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    clearUserState();
  }, [clearUserState]);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      if (!data.session) setLoading(false);
    });
    const { data } = supabase.auth.onAuthStateChange((event, s) => {
      setSession(s);
      if (event === 'SIGNED_IN') setExpired(false);
      if (!s) { clearUserState(); setLoading(false); }
    });
    return () => data.subscription.unsubscribe();
  }, [clearUserState]);

  useEffect(() => {
    const onExpired = () => { setExpired(true); void signOut(); };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, [signOut]);

  const token = session?.access_token;
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    apiFetch<Profile>('/me')
      .then((me) => !cancelled && setProfile(me))
      .catch(() => !cancelled && setProfile((p) => p ?? null))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [token]);

  const value = useMemo<AuthValue>(
    () => ({ loading, session, profile, role: profile?.role ?? null, expired, signOut }),
    [loading, session, profile, expired, signOut],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
