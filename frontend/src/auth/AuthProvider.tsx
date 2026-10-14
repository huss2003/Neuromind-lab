import { useQueryClient } from '@tanstack/react-query';
import type { Session } from '@supabase/supabase-js';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { ApiError, SESSION_EXPIRED_EVENT, apiFetch } from '../services/api';
import { supabase } from '../services/supabase';

export type Role = 'learner' | 'teacher' | 'admin';
export interface Profile { id: string; role: Role; email: string; display_name: string }
interface AuthValue {
  loading: boolean;
  session: Session | null;
  profile: Profile | null;
  role: Role | null; // from the server (/me): used only to show/hide UI; the API enforces access
  expired: boolean;
  deactivated: boolean; // the server refused this account because an administrator deactivated it
  needsMfa: boolean; // the account has two-step verification and this session has not completed it
  refreshAssurance: () => Promise<void>;
  signOut: () => Promise<void>;
}
const Ctx = createContext<AuthValue>({ loading: true, session: null, profile: null, role: null, expired: false, deactivated: false, needsMfa: false, refreshAssurance: async () => {}, signOut: async () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [expired, setExpired] = useState(false);
  const [deactivated, setDeactivated] = useState(false);
  const [needsMfa, setNeedsMfa] = useState(false);

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
      if (event === 'SIGNED_IN') { setExpired(false); setDeactivated(false); }
      // The initial "no session" notice on page load must not wipe the query cache: it would orphan queries already running on public pages.
      if (!s) { if (event !== 'INITIAL_SESSION') clearUserState(); setLoading(false); }
    });
    return () => data.subscription.unsubscribe();
  }, [clearUserState]);

  useEffect(() => {
    const onExpired = () => { setExpired(true); void signOut(); };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, [signOut]);

  const refreshAssurance = useCallback(async () => {
    const { data } = await supabase.auth.mfa.getAuthenticatorAssuranceLevel();
    setNeedsMfa(!!data && data.nextLevel === 'aal2' && data.currentLevel !== 'aal2');
  }, []);

  useEffect(() => {
    if (!session) { setNeedsMfa(false); return; }
    void supabase.auth.mfa.getAuthenticatorAssuranceLevel().then(({ data }) => setNeedsMfa(!!data && data.nextLevel === 'aal2' && data.currentLevel !== 'aal2'));
  }, [session]);

  const token = session?.access_token;
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    apiFetch<Profile>('/me')
      .then((me) => !cancelled && setProfile(me))
      .catch((e) => {
        if (cancelled) return;
        if (e instanceof ApiError && e.code === 'ACCOUNT_DEACTIVATED') { setDeactivated(true); void signOut(); }
        else setProfile((p) => p ?? null);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [token, signOut]);

  const value = useMemo<AuthValue>(
    () => ({ loading, session, profile, role: profile?.role ?? null, expired, deactivated, needsMfa, refreshAssurance, signOut }),
    [loading, session, profile, expired, deactivated, needsMfa, refreshAssurance, signOut],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
