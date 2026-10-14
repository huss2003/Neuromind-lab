import { Suspense, lazy } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Loading } from './components/States';
import { RequireAuth } from './auth/RequireAuth';
import { RouteA11y } from './components/RouteA11y';
import { AppShell } from './components/AppShell';
import { LecturePage } from './features/lecture/LecturePage';
import { CourseOverview } from './pages/CourseOverview';
import { Home } from './pages/Home';
import { MyProgress } from './pages/MyProgress';
import { NotFound } from './pages/NotFound';
import { Profile } from './pages/Profile';
import { AttemptHistory } from './pages/AttemptHistory';
import { Help } from './pages/Help';
import { Legal, POLICIES, Policies } from './pages/Legal';
import { Recover } from './pages/Recover';
import { SignIn } from './pages/SignIn';
import { Welcome } from './pages/Welcome';
import { SignUp } from './pages/SignUp';
import { Certificates, VerifyCertificate } from './pages/Certificates';
import { Portfolio } from './pages/Portfolio';
import { TeacherReport } from './pages/TeacherTools';
import { AdminLayout } from './pages/admin/AdminLayout';
import { AdminOverview } from './pages/admin/AdminOverview';
import { AdminUsers } from './pages/admin/AdminUsers';
import { AdminCohorts } from './pages/admin/AdminCohorts';
import { AdminContent } from './pages/admin/AdminContent';
import { AdminQueue } from './pages/admin/AdminQueue';
import { AdminAudit } from './pages/admin/AdminAudit';
import { AdminIssues } from './pages/admin/AdminIssues';
import { AdminSettings } from './pages/admin/AdminSettings';

const TeacherDashboard = lazy(() => import('./pages/TeacherDashboard').then((m) => ({ default: m.TeacherDashboard })));
const TeacherLearner = lazy(() => import('./pages/TeacherLearner').then((m) => ({ default: m.TeacherLearner })));
const TeacherSubmission = lazy(() => import('./pages/TeacherSubmission').then((m) => ({ default: m.TeacherSubmission })));

export function App() {
  return (
    <Suspense fallback={<Loading />}>
    <RouteA11y />
    <Routes>
      <Route path="/sign-in" element={<SignIn />} />
      <Route path="/recover" element={<Recover />} />
      <Route path="/sign-up" element={<SignUp />} />
      <Route path="/verify" element={<VerifyCertificate />} />
      <Route path="/verify/:serial" element={<VerifyCertificate />} />
      <Route path="/policies" element={<Policies />} />
      {POLICIES.map((p) => <Route key={p.kind} path={p.path} element={<Legal kind={p.kind} />} />)}
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
          <Route path="/certificates" element={<Certificates />} />
          <Route path="/portfolio" element={<Portfolio />} />
        </Route>
        <Route element={<RequireAuth roles={['teacher', 'admin']} />}>
          <Route path="/teacher" element={<TeacherDashboard />} />
          <Route path="/teacher/learners/:learnerId" element={<TeacherLearner />} />
          <Route path="/teacher/submissions/:submissionId" element={<TeacherSubmission />} />
          <Route path="/teacher/report" element={<TeacherReport />} />
        </Route>
        <Route element={<RequireAuth roles={['admin']} />}>
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminOverview />} />
            <Route path="users" element={<AdminUsers />} />
            <Route path="cohorts" element={<AdminCohorts />} />
            <Route path="content" element={<AdminContent />} />
            <Route path="queue" element={<AdminQueue />} />
            <Route path="audit" element={<AdminAudit />} />
            <Route path="issues" element={<AdminIssues />} />
            <Route path="settings" element={<AdminSettings />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
    </Suspense>
  );
}
