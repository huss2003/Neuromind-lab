import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { EmptyState, ErrorMessage, Loading } from '../../components/States';
import { errorMessage } from '../../services/api';
import { archiveCohort, cohortMember, createCohort, listAdminUsers, listCohorts, type AdminCohort } from '../../services/adminApi';
import { getCourses } from '../../services/lectureApi';

function CohortCard({ c, learners, teachers, onChange, onArchive }: { c: AdminCohort; learners: { id: string; name: string }[]; teachers: { id: string; name: string }[]; onChange: (msg: string) => void; onArchive: () => void }) {
  const [learner, setLearner] = useState('');
  const [teacher, setTeacher] = useState('');
  const act = useMutation({
    mutationFn: (v: { kind: 'members' | 'teachers'; id: string; add: boolean; name: string }) => cohortMember(c.id, v.kind, v.id, v.add),
    onSuccess: (_d, v) => onChange(`${v.name} was ${v.add ? 'added to' : 'removed from'} ${c.name}.`),
    onError: (e) => onChange(errorMessage(e)),
  });
  const inCohort = new Set([...c.learners, ...c.teachers].map((p) => p.id));
  return (
    <section className="card" aria-labelledby={`co-${c.id}`}>
      <div className="actions" style={{ justifyContent: 'space-between' }}>
        <h3 id={`co-${c.id}`} style={{ margin: 0 }}>{c.name}</h3>
        <button className="btn btn-tertiary" onClick={onArchive}>Archive<span className="visually-hidden"> {c.name}</span></button>
      </div>
      <h4>Teachers ({c.teachers.length})</h4>
      {c.teachers.length === 0 && <p className="muted">No teacher yet. Learners in this cohort are not visible to any teacher.</p>}
      <ul>{c.teachers.map((t) => <li key={t.id}>{t.display_name} <button className="btn btn-tertiary" onClick={() => act.mutate({ kind: 'teachers', id: t.id, add: false, name: t.display_name })}>Remove<span className="visually-hidden"> {t.display_name} from {c.name}</span></button></li>)}</ul>
      <form className="actions" onSubmit={(e: FormEvent) => { e.preventDefault(); const p = teachers.find((x) => x.id === teacher); if (p) { act.mutate({ kind: 'teachers', id: p.id, add: true, name: p.name }); setTeacher(''); } }}>
        <label htmlFor={`t-${c.id}`} className="visually-hidden">Add a teacher to {c.name}</label>
        <select id={`t-${c.id}`} value={teacher} onChange={(e) => setTeacher(e.target.value)} style={{ maxWidth: 260 }}>
          <option value="">Add a teacher…</option>
          {teachers.filter((t) => !inCohort.has(t.id)).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <button className="btn btn-secondary" type="submit" disabled={!teacher}>Add teacher</button>
      </form>
      <h4>Learners ({c.learners.length})</h4>
      {c.learners.length === 0 && <p className="muted">No learners yet.</p>}
      <ul>{c.learners.map((l) => <li key={l.id}>{l.display_name} <button className="btn btn-tertiary" onClick={() => act.mutate({ kind: 'members', id: l.id, add: false, name: l.display_name })}>Remove<span className="visually-hidden"> {l.display_name} from {c.name}</span></button></li>)}</ul>
      <form className="actions" onSubmit={(e: FormEvent) => { e.preventDefault(); const p = learners.find((x) => x.id === learner); if (p) { act.mutate({ kind: 'members', id: p.id, add: true, name: p.name }); setLearner(''); } }}>
        <label htmlFor={`l-${c.id}`} className="visually-hidden">Add a learner to {c.name}</label>
        <select id={`l-${c.id}`} value={learner} onChange={(e) => setLearner(e.target.value)} style={{ maxWidth: 260 }}>
          <option value="">Add a learner…</option>
          {learners.filter((l) => !inCohort.has(l.id)).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
        <button className="btn btn-secondary" type="submit" disabled={!learner}>Add learner</button>
      </form>
    </section>
  );
}

export function AdminCohorts() {
  const qc = useQueryClient();
  const cohorts = useQuery({ queryKey: ['a-cohorts'], queryFn: listCohorts });
  const courses = useQuery({ queryKey: ['courses'], queryFn: getCourses });
  const learners = useQuery({ queryKey: ['a-users', 'cohort-learners'], queryFn: () => listAdminUsers({ role: 'learner', status: 'active', limit: 100, offset: 0 }) });
  const teachers = useQuery({ queryKey: ['a-users', 'cohort-teachers'], queryFn: () => listAdminUsers({ role: 'teacher', status: 'active', limit: 100, offset: 0 }) });
  const [name, setName] = useState('');
  const [course, setCourse] = useState('');
  const [notice, setNotice] = useState('');
  const [archiving, setArchiving] = useState<AdminCohort | null>(null);
  const refresh = () => void qc.invalidateQueries({ queryKey: ['a-cohorts'] });
  const create = useMutation({ mutationFn: () => createCohort(course || courses.data?.[0]?.id || '', name.trim()), onSuccess: () => { setNotice(`Cohort “${name.trim()}” created.`); setName(''); refresh(); }, onError: (e) => setNotice(errorMessage(e)) });
  const archive = useMutation({ mutationFn: (id: string) => archiveCohort(id), onSuccess: () => { setNotice('Cohort archived. Teacher access that came only from it was removed.'); setArchiving(null); refresh(); }, onError: (e) => { setNotice(errorMessage(e)); setArchiving(null); } });

  return (
    <section aria-label="Cohorts">
      <p className="muted">A cohort is a named group of learners with one or more teachers. Adding a learner enrols them in the cohort's course and lets the cohort's teachers see their progress. Removing them takes that access away again.</p>
      {notice && <div role="status" className="notice notice-info"><p>{notice}</p></div>}
      <form className="card" onSubmit={(e) => { e.preventDefault(); setNotice(''); create.mutate(); }} aria-label="Create a cohort">
        <h2 style={{ marginTop: 0 }}>New cohort</h2>
        <label htmlFor="co-name">Name</label>
        <input id="co-name" type="text" required maxLength={80} value={name} onChange={(e) => setName(e.target.value)} placeholder="For example: Autumn evening group" />
        {courses.data && courses.data.length > 1 && (
          <><label htmlFor="co-course">Course</label>
            <select id="co-course" value={course} onChange={(e) => setCourse(e.target.value)}>{courses.data.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}</select></>
        )}
        <button className="btn btn-primary" type="submit" disabled={create.isPending || !name.trim()}>Create cohort</button>
      </form>
      {cohorts.isPending && <Loading label="Loading cohorts…" />}
      {cohorts.isError && <ErrorMessage message={errorMessage(cohorts.error)} onRetry={() => void cohorts.refetch()} />}
      {cohorts.data?.length === 0 && <EmptyState title="No cohorts yet">Create one above, then add teachers and learners.</EmptyState>}
      {cohorts.data?.map((c) => (
        <CohortCard key={c.id} c={c} onChange={(m) => { setNotice(m); refresh(); }} onArchive={() => setArchiving(c)}
          learners={(learners.data?.users ?? []).map((u) => ({ id: u.id, name: u.display_name || u.email }))}
          teachers={(teachers.data?.users ?? []).map((u) => ({ id: u.id, name: u.display_name || u.email }))} />
      ))}
      <ConfirmDialog open={!!archiving} title={`Archive ${archiving?.name ?? ''}?`} confirmLabel="Archive" destructive onCancel={() => setArchiving(null)} onConfirm={() => archiving && archive.mutate(archiving.id)}>
        <p>The cohort disappears from lists. Learners stay enrolled; teachers keep access only if another cohort still links them.</p>
      </ConfirmDialog>
    </section>
  );
}
