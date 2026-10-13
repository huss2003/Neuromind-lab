import { Link, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth/AuthProvider';
import { RequireAuth } from './auth/RequireAuth';
import { LecturePage } from './features/lecture/LecturePage';
import { Home } from './pages/Home';
import { NotFound } from './pages/NotFound';
import { SignIn } from './pages/SignIn';
import { TeacherResults } from './pages/TeacherResults';

export function App() {
  const { session, role, signOut } = useAuth();
  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>
      <header className="app-header">
        <nav aria-label="Main">
          <Link to="/" className="brand">NeuroMind Lab</Link>
          {(role === 'teacher' || role === 'admin') && <Link to="/teacher">Results</Link>}
        </nav>
        {session && <span>{session.user.email} <button className="btn btn-tertiary" onClick={() => void signOut()}>Sign out</button></span>}
      </header>
      <div id="main">
        <Routes>
          <Route path="/sign-in" element={<SignIn />} />
          <Route element={<RequireAuth />}>
            <Route path="/" element={<Home />} />
            <Route path="/lectures/:lectureId" element={<LecturePage />} />
          </Route>
          <Route element={<RequireAuth roles={['teacher', 'admin']} />}>
            <Route path="/teacher" element={<TeacherResults />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </div>
    </>
  );
}
