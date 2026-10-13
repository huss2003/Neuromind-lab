import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <main>
      <h1>Page not found</h1>
      <p><Link to="/">Back to courses</Link></p>
    </main>
  );
}
