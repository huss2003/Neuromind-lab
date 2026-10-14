import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { Badge } from '../../components/Badge';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { EmptyState, ErrorMessage, Loading } from '../../components/States';
import { useAuth } from '../../auth/AuthProvider';
import { errorMessage } from '../../services/api';
import { createAdminUser, listAdminUsers, setUserActive, setUserRole, type AdminUser } from '../../services/adminApi';
import { getCourses } from '../../services/lectureApi';

const PAGE = 15;
const when = (iso?: string | null) => (iso ? new Date(iso).toLocaleDateString([], { dateStyle: 'medium' }) : 'never');

export function AdminUsers() {
  const { profile } = useAuth();
  const qc = useQueryClient();
  const [term, setTerm] = useState('');
  const [text, setText] = useState('');
  const [role, setRole] = useState('any');
  const [status, setStatus] = useState('any');
  const [offset, setOffset] = useState(0);
  const [confirm, setConfirm] = useState<AdminUser | null>(null);
  const [notice, setNotice] = useState('');
  const users = useQuery({ queryKey: ['a-users', term, role, status, offset], queryFn: () => listAdminUsers({ q: term, role, status, limit: PAGE, offset }) });
  const courses = useQuery({ queryKey: ['courses'], queryFn: getCourses });
  const refresh = () => void qc.invalidateQueries({ queryKey: ['a-users'] });

  const toggle = useMutation({ mutationFn: (u: AdminUser) => setUserActive(u.id, u.deactivated), onSuccess: (_d, u) => { setNotice(`${u.display_name} was ${u.deactivated ? 'reactivated' : 'deactivated'}.`); setConfirm(null); refresh(); }, onError: (e) => { setNotice(errorMessage(e)); setConfirm(null); } });
  const changeRole = useMutation({ mutationFn: (v: { u: AdminUser; role: string }) => setUserRole(v.u.id, v.role), onSuccess: (_d, v) => { setNotice(`${v.u.display_name} is now ${v.role === 'admin' ? 'an administrator' : `a ${v.role}`}.`); refresh(); }, onError: (e) => setNotice(errorMessage(e)) });

  const [f, setF] = useState({ email: '', display_name: '', role: 'learner', password: '', course_id: '' });
  const create = useMutation({
    mutationFn: () => createAdminUser({ ...f, course_id: f.course_id || undefined }),
    onSuccess: () => { setNotice(`Account created for ${f.display_name}. Share the starting password privately and ask them to change it.`); setF({ email: '', display_name: '', role: 'learner', password: '', course_id: '' }); refresh(); },
    onError: (e) => setNotice(errorMessage(e)),
  });
  const submit = (e: FormEvent) => { e.preventDefault(); setNotice(''); create.mutate(); };
  const total = users.data?.total ?? 0;

  return (
    <section aria-label="Users">
      {notice && <div role="status" className="notice notice-info"><p>{notice}</p></div>}
      <h2>People</h2>
      <form role="search" className="actions" onSubmit={(e) => { e.preventDefault(); setOffset(0); setTerm(text.trim()); }}>
        <label htmlFor="user-search" className="visually-hidden">Search by name or email</label>
        <input id="user-search" type="search" value={text} onChange={(e) => setText(e.target.value)} placeholder="Search by name or email" style={{ maxWidth: 280 }} />
        <label htmlFor="user-role" className="visually-hidden">Role</label>
        <select id="user-role" value={role} onChange={(e) => { setOffset(0); setRole(e.target.value); }} style={{ maxWidth: 160 }}>
          <option value="any">Any role</option><option value="learner">Learners</option><option value="teacher">Teachers</option><option value="admin">Administrators</option>
        </select>
        <label htmlFor="user-status" className="visually-hidden">Account status</label>
        <select id="user-status" value={status} onChange={(e) => { setOffset(0); setStatus(e.target.value); }} style={{ maxWidth: 160 }}>
          <option value="any">Any status</option><option value="active">Active</option><option value="deactivated">Deactivated</option>
        </select>
        <button className="btn btn-secondary" type="submit">Search</button>
      </form>
      {users.isPending && <Loading label="Loading people…" />}
      {users.isError && <ErrorMessage message={errorMessage(users.error)} onRetry={() => void users.refetch()} />}
      {users.data && users.data.users.length === 0 && <EmptyState title="No one matches">Try a different search or filter.</EmptyState>}
      {users.data && users.data.users.length > 0 && (
        <>
          <div className="table-wrap">
            <table>
              <caption>People ({total})</caption>
              <thead><tr><th scope="col">Name</th><th scope="col">Email</th><th scope="col">Role</th><th scope="col">Status</th><th scope="col">Last sign-in</th><th scope="col"><span className="visually-hidden">Actions</span></th></tr></thead>
              <tbody>
                {users.data.users.map((u) => {
                  const self = u.id === profile?.id;
                  return (
                    <tr key={u.id}>
                      <th scope="row">{u.display_name || '—'}{self && <span className="muted"> (you)</span>}</th>
                      <td>{u.email}</td>
                      <td>
                        <label htmlFor={`role-${u.id}`} className="visually-hidden">Role for {u.display_name}</label>
                        <select id={`role-${u.id}`} value={u.role} disabled={self || changeRole.isPending} onChange={(e) => changeRole.mutate({ u, role: e.target.value })} style={{ minHeight: 38, padding: '4px 8px' }}>
                          <option value="learner">Learner</option><option value="teacher">Teacher</option><option value="admin">Administrator</option>
                        </select>
                      </td>
                      <td>{u.deactivated ? <Badge kind="danger">Deactivated</Badge> : <Badge kind="success">Active</Badge>}</td>
                      <td>{when(u.last_sign_in_at)}</td>
                      <td>{!self && <button className={`btn ${u.deactivated ? 'btn-secondary' : 'btn-tertiary'}`} onClick={() => (u.deactivated ? toggle.mutate(u) : setConfirm(u))}>{u.deactivated ? 'Reactivate' : 'Deactivate'}<span className="visually-hidden"> {u.display_name}</span></button>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <nav className="actions" aria-label="Pagination">
            <button className="btn btn-secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</button>
            <span className="muted" style={{ alignSelf: 'center' }}>Showing {offset + 1}–{Math.min(offset + PAGE, total)} of {total}</span>
            <button className="btn btn-secondary" disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>Next</button>
          </nav>
        </>
      )}

      <h2 style={{ marginTop: 32 }}>Add a person</h2>
      <form className="card" onSubmit={submit} aria-label="Add a person">
        <label htmlFor="nu-name">Full name</label>
        <input id="nu-name" type="text" required maxLength={80} value={f.display_name} onChange={(e) => setF({ ...f, display_name: e.target.value })} />
        <label htmlFor="nu-email">Email address</label>
        <input id="nu-email" type="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} autoComplete="off" />
        <label htmlFor="nu-role">Role</label>
        <select id="nu-role" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>
          <option value="learner">Learner</option><option value="teacher">Teacher</option><option value="admin">Administrator</option>
        </select>
        {f.role === 'learner' && (
          <>
            <label htmlFor="nu-course">Enrol in a course (optional)</label>
            <select id="nu-course" value={f.course_id} onChange={(e) => setF({ ...f, course_id: e.target.value })}>
              <option value="">Not now</option>
              {courses.data?.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
          </>
        )}
        <label htmlFor="nu-pass">Starting password</label>
        <input id="nu-pass" type="password" required minLength={12} maxLength={128} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} autoComplete="new-password" aria-describedby="nu-pass-h" />
        <p id="nu-pass-h" className="field-hint">At least 12 characters. Give it to the person privately; ask them to change it after signing in.</p>
        <button className="btn btn-primary" type="submit" disabled={create.isPending}>{create.isPending ? 'Creating…' : 'Create account'}</button>
      </form>

      <ConfirmDialog open={!!confirm} title={`Deactivate ${confirm?.display_name ?? ''}?`} confirmLabel="Deactivate" destructive onCancel={() => setConfirm(null)} onConfirm={() => confirm && toggle.mutate(confirm)}>
        <p>They will be signed out of new requests within about a minute and cannot sign in again. Their progress and attempts are kept. You can reactivate the account later.</p>
      </ConfirmDialog>
    </section>
  );
}
