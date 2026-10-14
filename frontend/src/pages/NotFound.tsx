import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <main className="page narrow">
      <h1>Page not found</h1>
      <p>The page you're looking for doesn't exist or has moved.</p>
      <Link className="btn btn-primary" to="/">Back to dashboard</Link>
    </main>
  );
}
