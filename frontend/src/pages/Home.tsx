import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Badge } from '../components/Badge';
import { ErrorMessage, Loading } from '../components/States';
import { errorMessage } from '../services/api';
import { getCourse, getCourses, getMyProgress } from '../services/lectureApi';

export function Home() {
  const courses = useQuery({ queryKey: ['courses'], queryFn: getCourses });
  const first = courses.data?.[0];
  const course = useQuery({ queryKey: ['course', first?.id], queryFn: () => getCourse(first!.id), enabled: !!first });
  const progress = useQuery({ queryKey: ['progress'], queryFn: getMyProgress });

  if (courses.isPending) return <Loading label="Loading your courses…" />;
  if (courses.isError) return <main><ErrorMessage message={errorMessage(courses.error)} /><button className="btn btn-secondary" onClick={() => void courses.refetch()}>Retry</button></main>;
  if (!first) return <main><h1>Welcome</h1><p>No courses are published yet.</p></main>;

  const status = new Map(progress.data?.sessions.map((s) => [s.lecture_id, s.status]) ?? []);
  const lectures = course.data?.lectures ?? [];
  const done = lectures.filter((l) => status.get(l.id) === 'completed').length;

  return (
    <main>
      <h1>{first.title}</h1>
      <p>{first.description}</p>
      <p><strong>Progress:</strong> {done} / {lectures.length} lectures completed in this course</p>
      {course.isPending && <Loading label="Loading lectures…" />}
      {course.isError && <ErrorMessage message={errorMessage(course.error)} />}
      {lectures.length === 0 && course.isSuccess && <p>No lectures are published yet.</p>}
      <ul className="lecture-list">
        {lectures.map((l) => {
          const st = status.get(l.id);
          return (
            <li key={l.id} className="card">
              <h2>Lecture {l.lecture_number}: {l.title}</h2>
              <p>{l.summary}</p>
              <p>
                {st === 'completed' ? <Badge kind="success">Completed</Badge> : st === 'in_progress' ? <Badge kind="info">In progress</Badge> : <Badge kind="neutral">Not started</Badge>}
                {l.duration_seconds ? ` · ${Math.round(l.duration_seconds / 60)} min` : ''}
              </p>
              <Link className="btn btn-primary" to={`/lectures/${l.id}`}>{st === 'completed' ? 'Review lecture' : st === 'in_progress' ? 'Resume lecture' : 'Start lecture'}</Link>
            </li>
          );
        })}
      </ul>
    </main>
  );
}
