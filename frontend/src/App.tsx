import { Link, Route, Routes } from 'react-router-dom';
import { Home } from './pages/Home';
import { SignIn } from './pages/SignIn';
import { NotFound } from './pages/NotFound';

export function App() {
  return (
    <>
      <header>
        <nav aria-label="Main"><Link to="/">NeuroMind</Link></nav>
      </header>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/sign-in" element={<SignIn />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </>
  );
}
