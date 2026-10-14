import { Link } from 'react-router-dom';
import { BrandMark, BrandName } from '../components/Brand';
import { RichText } from '../components/RichText';
import { ACCEPTABLE_USE, ACCESSIBILITY, PRIVACY, RETENTION, SECURITY, TERMS } from '../content/legal';

export type PolicyKind = 'privacy' | 'terms' | 'acceptable-use' | 'retention' | 'accessibility' | 'security';

export const POLICIES: { kind: PolicyKind; path: string; title: string; summary: string; text: string }[] = [
  { kind: 'privacy', path: '/privacy', title: 'Privacy notice', summary: 'What we keep about you, why, who sees it and where it is stored.', text: PRIVACY },
  { kind: 'terms', path: '/terms', title: 'Terms of use', summary: 'The basic rules for using the site and how marking works.', text: TERMS },
  { kind: 'acceptable-use', path: '/policies/acceptable-use', title: 'Acceptable use and academic honesty', summary: 'Doing your own work and keeping the grader safe for everyone.', text: ACCEPTABLE_USE },
  { kind: 'retention', path: '/policies/retention', title: 'Data retention', summary: 'How long each kind of information is kept and how to ask for deletion.', text: RETENTION },
  { kind: 'accessibility', path: '/policies/accessibility', title: 'Accessibility statement', summary: 'What has been checked, what has not, and how to report a barrier.', text: ACCESSIBILITY },
  { kind: 'security', path: '/policies/security', title: 'Security and reporting', summary: 'How the service protects your work and how to report a problem.', text: SECURITY },
];

/** Public pages: reachable without signing in (the sign-in screen links to them). */
export function Legal({ kind }: { kind: PolicyKind }) {
  const policy = POLICIES.find((p) => p.kind === kind) ?? POLICIES[0];
  return (
    <main className="page narrow legal">
      <p><Link className="brand legal-brand" to="/"><BrandMark size={28} /><BrandName /></Link></p>
      <p className="muted"><Link to="/policies">All policies</Link></p>
      <h1>{policy.title}</h1>
      <div className="notice notice-warning"><p>Draft for review by the course owner. It describes how the service works today.</p></div>
      <RichText text={policy.text} headingLevel={2} />
      <p className="muted">See also: <Link to="/policies">all policies</Link></p>
    </main>
  );
}

/** One place that lists every policy. */
export function Policies() {
  return (
    <main className="page narrow legal">
      <p><Link className="brand legal-brand" to="/"><BrandMark size={28} /><BrandName /></Link></p>
      <h1>Policies</h1>
      <p className="muted">How NeuroMind Lab treats your information and what we expect from each other. These are drafts that the course owner is still reviewing.</p>
      <ul className="policy-list">
        {POLICIES.map((p) => (
          <li key={p.kind} className="card">
            <h2><Link to={p.path}>{p.title}</Link></h2>
            <p>{p.summary}</p>
          </li>
        ))}
      </ul>
    </main>
  );
}
