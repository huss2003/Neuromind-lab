import { Link } from 'react-router-dom';
import { BrandMark, BrandName } from '../components/Brand';
import { RichText } from '../components/RichText';
import { PRIVACY, TERMS } from '../content/legal';

/** Public pages: reachable without signing in (the sign-in screen links to them). */
export function Legal({ kind }: { kind: 'privacy' | 'terms' }) {
  const privacy = kind === 'privacy';
  return (
    <main className="page narrow legal">
      <p><Link className="brand legal-brand" to="/"><BrandMark size={28} /><BrandName /></Link></p>
      <h1>{privacy ? 'Privacy notice' : 'Terms of use'}</h1>
      <div className="notice notice-warning"><p>Draft for review by the course owner. It describes how the service works today.</p></div>
      <RichText text={privacy ? PRIVACY : TERMS} headingLevel={2} />
      <p className="muted">See also: <Link to={privacy ? '/terms' : '/privacy'}>{privacy ? 'Terms of use' : 'Privacy notice'}</Link></p>
    </main>
  );
}
