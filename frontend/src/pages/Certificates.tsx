import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { BrandMark, BrandName } from '../components/Brand';
import { EmptyState, ErrorMessage, Loading } from '../components/States';
import { errorMessage } from '../services/api';
import { getCertificates, verifyCertificate, type Certificate } from '../services/adminApi';

const date = (iso: string) => new Date(iso).toLocaleDateString([], { dateStyle: 'long' });

function CertificateCard({ c }: { c: Certificate }) {
  const link = `${window.location.origin}/verify/${c.serial}`;
  return (
    <article className="certificate" aria-label={`Certificate for ${c.course}`}>
      <div className="certificate-inner">
        <p className="certificate-brand"><BrandMark size={32} /> <BrandName /></p>
        <p className="certificate-kicker">Certificate of completion</p>
        <h2 className="certificate-name">{c.holder}</h2>
        <p>has completed all {c.completed_lectures} lecture{c.completed_lectures === 1 ? '' : 's'} of</p>
        <p className="certificate-course">{c.course}</p>
        <p className="muted">Issued {date(c.issued_at)} · Serial {c.serial}</p>
        <p className="certificate-verify">Anyone can check this certificate at {link}</p>
      </div>
      <div className="actions no-print"><button className="btn btn-primary" onClick={() => window.print()}>Print or save as PDF</button></div>
    </article>
  );
}

export function Certificates() {
  const q = useQuery({ queryKey: ['certificates'], queryFn: getCertificates });
  return (
    <main className="page narrow">
      <h1>Certificates</h1>
      <p className="muted no-print">A certificate is issued by the server when you complete every lecture in a course. It cannot be created or changed from your browser.</p>
      {q.isPending && <Loading label="Loading your certificates…" />}
      {q.isError && <ErrorMessage message={errorMessage(q.error)} onRetry={() => void q.refetch()} />}
      {q.data?.length === 0 && <EmptyState title="No certificate yet">Complete every lecture in your course and your certificate appears here. <Link to="/progress">See your progress</Link>.</EmptyState>}
      {q.data?.map((c) => <CertificateCard key={c.id} c={c} />)}
    </main>
  );
}

/** Public page: anyone with a serial can check it is genuine. Shows only the course, the date and a shortened name. */
export function VerifyCertificate() {
  const [serial, setSerial] = useState(window.location.pathname.split('/')[2] ?? '');
  const [submitted, setSubmitted] = useState(serial);
  const q = useQuery({ queryKey: ['verify', submitted], queryFn: () => verifyCertificate(submitted), enabled: submitted.length > 0, retry: false });
  return (
    <main className="page narrow legal">
      <p><Link className="brand legal-brand" to="/"><BrandMark size={28} /><BrandName /></Link></p>
      <h1>Check a certificate</h1>
      <form onSubmit={(e) => { e.preventDefault(); setSubmitted(serial.trim().toUpperCase()); }}>
        <label htmlFor="serial">Certificate serial</label>
        <input id="serial" type="text" value={serial} onChange={(e) => setSerial(e.target.value)} placeholder="NM-2026-1A2B3C4D" autoComplete="off" spellCheck={false} />
        <button className="btn btn-primary" type="submit" style={{ marginTop: 12 }}>Check</button>
      </form>
      <div aria-live="polite">
        {q.isFetching && <Loading label="Checking…" />}
        {q.isError && <ErrorMessage message={errorMessage(q.error)} />}
        {q.data?.valid && (
          <div role="status" className="notice notice-success">
            <strong>This certificate is genuine.</strong>
            <p>{q.data.holder} completed {q.data.course} on {q.data.issued_at ? date(q.data.issued_at) : '—'}.</p>
          </div>
        )}
        {q.data && !q.data.valid && <div role="status" className="notice notice-warning"><strong>No certificate was found for that serial.</strong><p>Check the characters and try again.</p></div>}
      </div>
    </main>
  );
}
