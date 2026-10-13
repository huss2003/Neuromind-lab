import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { LectureStatus } from '../components/LectureStatus';
import { EmptyState, ErrorMessage, Loading } from '../components/States';
import { errorMessage } from '../services/api';
import { getCourse, getCourses, getMyProgress } from '../services/lectureApi';

export function MyProgress() {
  const courses = useQuery({ queryKey: ['courses'], queryFn: getCourses });
  const first = courses.data?.[0];
  const course = useQuery({ queryKey: ['course', first?.id], queryFn: () => getCourse(first!.id), enabled: !!first });
  const progress = useQuery({ queryKey: ['progress'], queryFn: getMyProgress });
  if (courses.isPending || progress.isPending || !progress.data) return <main className="page"><Loading /></main>;
  const err = courses.error ?? progress.error ?? course.error;
  if (err) return <main className="page"><ErrorMessage message={errorMessage(err)} onRetry={() => { void courses.refetch(); void progress.refetch(); }} /></main>;
  const sessions = new Map(progress.data.sessions.map((s) => [s.lecture_id, s]));
  const lectures = course.data?.lectures ?? [];
  return (
    <main className="page">
      <h1>My progress</h1>
      {lectures.length === 0 ? <EmptyState title="Nothing to show yet">Start a lecture and your progress will appear here.</EmptyState> : (
        <div className="table-wrap">
          <table>
            <caption>Lecture progress</caption>
            <thead><tr><th scope="col">Lecture</th><th scope="col">Status</th><th scope="col">Completed</th><th scope="col"><span className="visually-hidden">Open</span></th></tr></thead>
            <tbody>
              {lectures.map((l) => {
                const s = sessions.get(l.id);
                return (
                  <tr key={l.id}>
                    <th scope="row">Lecture {l.lecture_number}: {l.title}</th>
                    <td><LectureStatus status={s?.status} /></td>
                    <td>{s?.completed_at ? new Date(s.completed_at).toLocaleDateString() : '—'}</td>
                    <td><Link to={`/lectures/${l.id}`}>Open</Link></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
