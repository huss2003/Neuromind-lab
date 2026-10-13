import { Suspense, lazy } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Loading } from './components/States';
import { RequireAuth } from './auth/RequireAuth';
import { AppShell } from './components/AppShell';
import { LecturePage } from './features/lecture/LecturePage';
import { CourseOverview } from './pages/CourseOverview';
import { Home } from './pages/Home';
import { MyProgress } from './pages/MyProgress';
import { NotFound } from './pages/NotFound';
import { Profile } from './pages/Profile';
import { AttemptHistory } from './pages/AttemptHistory';
import { Help } from './pages/Help';
import { Recover } from './pages/Recover';
import { SignIn } from './pages/SignIn';
import { Welcome } from './pages/Welcome';

const TeacherDashboard = lazy(() => import('./pages/TeacherDashboard').then((m) => ({ default: m.TeacherDashboard })));
const TeacherLearner = lazy(() => import('./pages/TeacherLearner').then((m) => ({ default: m.TeacherLearner })));
const TeacherSubmission = lazy(() => import('./pages/TeacherSubmission').then((m) => ({ default: m.TeacherSubmission })));

export function App() {
  return (
    <Suspense fallback={<Loading />}>
    <Routes>
      <Route path="/sign-in" element={<SignIn />} />
      <Route path="/recover" element={<Recover />} />
      <Route element={<AppShell />}>
        <Route element={<RequireAuth />}>
          <Route path="/" element={<Home />} />
          <Route path="/courses/:courseId" element={<CourseOverview />} />
          <Route path="/lectures/:lectureId" element={<LecturePage />} />
          <Route path="/progress" element={<MyProgress />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/help" element={<Help />} />
          <Route path="/welcome" element={<Welcome />} />
          <Route path="/exercises/:exerciseId/attempts" element={<AttemptHistory />} />
        </Route>
        <Route element={<RequireAuth roles={['teacher', 'admin']} />}>
          <Route path="/teacher" element={<TeacherDashboard />} />
          <Route path="/teacher/learners/:learnerId" element={<TeacherLearner />} />
          <Route path="/teacher/submissions/:submissionId" element={<TeacherSubmission />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
    </Suspense>
  );
}
