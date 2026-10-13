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
import { SignIn } from './pages/SignIn';

const TeacherDashboard = lazy(() => import('./pages/TeacherDashboard').then((m) => ({ default: m.TeacherDashboard })));
const TeacherLearner = lazy(() => import('./pages/TeacherLearner').then((m) => ({ default: m.TeacherLearner })));
const TeacherSubmission = lazy(() => import('./pages/TeacherSubmission').then((m) => ({ default: m.TeacherSubmission })));

export function App() {
  return (
    <Suspense fallback={<Loading />}>
    <Routes>
      <Route path="/sign-in" element={<SignIn />} />
      <Route element={<AppShell />}>
        <Route element={<RequireAuth />}>
          <Route path="/" element={<Home />} />
          <Route path="/courses/:courseId" element={<CourseOverview />} />
          <Route path="/lectures/:lectureId" element={<LecturePage />} />
          <Route path="/progress" element={<MyProgress />} />
          <Route path="/profile" element={<Profile />} />
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
