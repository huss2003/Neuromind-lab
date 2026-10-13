import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { EmptyState, ErrorMessage, Loading } from '../components/States';
import { ProgressRing } from '../components/Progress';
import { useAuth } from '../auth/AuthProvider';
import { errorMessage } from '../services/api';
import { getCourse, getCourses, getMyFeedback, getMyProgress } from '../services/lectureApi';

export function Home() {
  const { profile, session } = useAuth();
  const courses = useQuery({ queryKey: ['courses'], queryFn: getCourses });
  const progress = useQuery({ queryKey: ['progress'], queryFn: getMyProgress });
  const feedback = useQuery({ queryKey: ['feedback'], queryFn: getMyFeedback });
  const first = courses.data?.[0];
  const course = useQuery({ queryKey: ['course', first?.id], queryFn: () => getCourse(first!.id), enabled: !!first });

  if (courses.isPending) return <main className="page"><Loading label="Loading your courses…" /></main>;
  if (courses.isError) return <main className="page"><ErrorMessage message={errorMessage(courses.error)} onRetry={() => void courses.refetch()} /></main>;
  if (!first) return <main className="page"><h1>Welcome</h1><EmptyState title="No courses yet">Your teacher hasn't published any course. Check back soon.</EmptyState></main>;

  const status = new Map(progress.data?.sessions.map((s) => [s.lecture_id, s.status]) ?? []);
  const lectures = course.data?.lectures ?? [];
  const done = lectures.filter((l) => status.get(l.id) === 'completed').length;
  const next = lectures.find((l) => status.get(l.id) === 'in_progress') ?? lectures.find((l) => status.get(l.id) !== 'completed');
  const resuming = next && status.get(next.id) === 'in_progress';
  const name = (profile?.display_name || session?.user.email || '').split('@')[0];

  return (
    <main className="page">
      <section className="hero" aria-labelledby="hero-title">
        <div>
          <p style={{ opacity: .85 }}>Welcome back{name ? `, ${name}` : ''}</p>
          <h1 id="hero-title">{next ? `${resuming ? 'Continue' : 'Start'}: Lecture ${next.lecture_number}` : 'You are all caught up'}</h1>
          {next && <p>{next.title}</p>}
        </div>
        {next ? <Link className="btn btn-primary" to={`/lectures/${next.id}`}>{resuming ? 'Resume lecture' : 'Start lecture'}</Link> : <Link className="btn btn-primary" to={`/courses/${first.id}`}>Review course</Link>}
      </section>

      <div className="grid grid-2">
        <section className="card" aria-labelledby="course-title">
          <h2 id="course-title">{first.title}</h2>
          <p className="muted">{first.description}</p>
          {course.isPending ? <Loading label="Loading lectures…" /> : <ProgressRing done={done} total={lectures.length} label="lectures completed" />}
          {course.isError && <ErrorMessage message={errorMessage(course.error)} />}
          <div className="actions"><Link className="btn btn-secondary" to={`/courses/${first.id}`}>Open course</Link></div>
        </section>
        <section className="card" aria-labelledby="fb-title">
          <h2 id="fb-title">Notes from your teacher</h2>
          {feedback.isPending && <Loading />}
          {feedback.data?.length === 0 && <p className="muted">No notes yet. When your teacher shares feedback, it will appear here.</p>}
          <ul style={{ paddingLeft: 18 }}>{feedback.data?.slice(0, 3).map((f) => <li key={f.id}>{f.body}</li>)}</ul>
        </section>
      </div>
    </main>
  );
}
