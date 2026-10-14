import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthProvider';

/** S03 — static orientation; account data comes from the server profile. */
export function Welcome() {
  const { profile } = useAuth();
  return (
    <main className="page narrow">
      <h1>Welcome{profile?.display_name ? `, ${profile.display_name}` : ''}</h1>
      <section className="card" aria-labelledby="how-h">
        <h2 id="how-h">How the lab works</h2>
        <ol>
          <li><strong>Watch</strong> a short video section.</li>
          <li><strong>Check</strong> your understanding with a question. You get an explanation either way.</li>
          <li><strong>Practise</strong> in the editor. Run practice is private and unlimited.</li>
          <li><strong>Submit for grading</strong> when you are ready. That is an official attempt and it keeps your best score.</li>
          <li><strong>Review</strong> targeted help if something is not met yet, then try again.</li>
        </ol>
      </section>
      <section className="card" aria-labelledby="req-h">
        <h2 id="req-h">What you need</h2>
        <ul>
          <li>A current version of Chrome, Edge, Firefox or Safari with JavaScript on.</li>
          <li>A connection that can load video. Practice runs on your device once the Python runtime has loaded.</li>
          <li>If the code editor doesn’t load, use <em>Use simple text editor</em> in the lab.</li>
        </ul>
      </section>
      <section className="card" aria-labelledby="rules-h">
        <h2 id="rules-h">Acceptable use and privacy</h2>
        <ul>
          <li>Do your own work in graded attempts. Don’t share hidden tests or other people’s answers.</li>
          <li>Your teacher can see your progress, attempts and the code you submit.</li>
          <li>Don’t put passwords or secrets in code or messages.</li>
        </ul>
        <p className="muted">Retention periods for stored code and notes are still to be confirmed by the course owner.</p>
      </section>
      <div className="actions"><Link className="btn btn-primary" to="/">Start learning</Link></div>
    </main>
  );
}
