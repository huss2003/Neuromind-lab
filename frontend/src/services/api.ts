import { supabase } from './supabase';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
export const SESSION_EXPIRED_EVENT = 'neuromind:session-expired';

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public requestId = '') {
    super(message);
  }
}

async function request(path: string, init: RequestInit, token: string | undefined): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(`${API_BASE}/api/v1${path}`, { ...init, headers });
}

export async function apiFetch<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const { data } = await supabase.auth.getSession();
  let res: Response;
  try {
    res = await request(path, init, data.session?.access_token);
    if (res.status === 401 && data.session) {
      // The token may simply have expired: try one refresh, then give up and send the learner to sign in.
      const refreshed = await supabase.auth.refreshSession();
      if (refreshed.data.session) res = await request(path, init, refreshed.data.session.access_token);
      if (res.status === 401) window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', 'Cannot reach the server. Check your connection and try again.');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const e = body?.error;
    throw new ApiError(res.status, e?.code ?? 'UNKNOWN', e?.message ?? 'Request failed', e?.request_id ?? '');
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const errorMessage = (e: unknown): string =>
  e instanceof ApiError ? (e.requestId ? `${e.message} (ref ${e.requestId.slice(0, 8)})` : e.message) : 'Something went wrong. Please try again.';
