import type { Session } from '@supabase/supabase-js';
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { apiFetch } from '../services/api';
import { supabase } from '../services/supabase';

export type Role = 'learner' | 'teacher' | 'admin';
interface AuthValue {
  loading: boolean;
  session: Session | null;
  role: Role | null; // from the server (/me), used only to show/hide UI; the API enforces access
  signOut: () => Promise<void>;
}
const Ctx = createContext<AuthValue>({ loading: true, session: null, role: null, signOut: async () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [role, setRole] = useState<Role | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      if (!data.session) setLoading(false);
    });
    const { data } = supabase.auth.onAuthStateChange((_e, s) => {
      setSession(s);
      if (!s) { setRole(null); setLoading(false); }
    });
    return () => data.subscription.unsubscribe();
  }, []);

  const token = session?.access_token;
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    apiFetch<{ role: Role }>('/me')
      .then((me) => !cancelled && setRole(me.role))
      .catch(() => !cancelled && setRole('learner'))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [token]);

  const value = useMemo<AuthValue>(() => ({ loading, session, role, signOut: async () => { await supabase.auth.signOut(); } }), [loading, session, role]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
