import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { errorMessage } from '../../services/api';
import { importPack, validatePack, type PackReport } from '../../services/adminApi';

class FileProblem extends Error {}
const explain = (e: unknown) => (e instanceof FileProblem ? e.message : errorMessage(e));

type Parsed = { pack: unknown; tests: unknown } | null;

async function readJson(file: File | undefined, label: string): Promise<unknown> {
  if (!file) throw new FileProblem(`Choose the ${label} file first.`);
  try { return JSON.parse(await file.text()); } catch { throw new FileProblem(`The ${label} file is not valid JSON.`); }
}

export function PackImport() {
  const qc = useQueryClient();
  const [packFile, setPackFile] = useState<File>();
  const [testsFile, setTestsFile] = useState<File>();
  const [report, setReport] = useState<PackReport>();
  const [parsed, setParsed] = useState<Parsed>(null);
  const [publish, setPublish] = useState(false);
  const [replace, setReplace] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: 'error' | 'success'; text: string }>();

  const reset = () => { setReport(undefined); setParsed(null); setMessage(undefined); };

  async function check() {
    setBusy(true); reset();
    try {
      const pack = await readJson(packFile, 'lecture pack');
      const tests = await readJson(testsFile, 'hidden tests');
      setReport(await validatePack(pack, tests));
      setParsed({ pack, tests });
    } catch (e) { setMessage({ kind: 'error', text: explain(e) }); } finally { setBusy(false); }
  }

  async function doImport() {
    if (!parsed) return;
    setBusy(true); setMessage(undefined);
    try {
      const r = await importPack(parsed.pack, parsed.tests, { publish, replace_published: replace });
      setMessage({ kind: 'success', text: `Lecture ${r.lecture_number} ${r.created ? 'created' : 'updated'} as ${r.status}.` });
      void qc.invalidateQueries({ queryKey: ['a-courses'] });
    } catch (e) { setMessage({ kind: 'error', text: explain(e) }); } finally { setBusy(false); }
  }

  return (
    <section className="card" aria-labelledby="pack-import-h">
      <h2 id="pack-import-h" style={{ marginTop: 0 }}>Import a lecture</h2>
      <p className="muted">Upload a lecture pack and its hidden test file. Nothing is saved until you press Import, and imports are drafts unless you choose to publish. The hidden tests are stored on the server only and are never shown again.</p>
      <form onSubmit={(e) => { e.preventDefault(); void check(); }}>
        <label htmlFor="pack-file">Lecture pack (JSON)</label>
        <input id="pack-file" type="file" accept="application/json,.json" onChange={(e) => { setPackFile(e.target.files?.[0]); reset(); }} />
        <label htmlFor="tests-file">Hidden tests (JSON)</label>
        <input id="tests-file" type="file" accept="application/json,.json" onChange={(e) => { setTestsFile(e.target.files?.[0]); reset(); }} />
        <p><button type="submit" className="btn" disabled={busy}>{busy ? 'Working…' : 'Check pack'}</button></p>
      </form>
      <div role="status" aria-live="polite">
        {message && <div className={`notice ${message.kind === 'error' ? 'notice-danger' : 'notice-success'}`}><p>{message.text}</p></div>}
        {report && report.valid && report.summary && (
          <div className="notice notice-success"><p>Valid: lecture {report.summary.lecture_number}, “{report.summary.title}” — {report.summary.segments} sections, {report.summary.checkpoints} questions, {report.summary.lab_tests} lab tests.</p></div>
        )}
        {report && !report.valid && (
          <div className="notice notice-danger">
            <p>This pack cannot be imported yet:</p>
            <ul>
              {report.problems.map((p) => <li key={p}>{p}</li>)}
              {report.missing_tests.map((k) => <li key={k}>Hidden test definition missing: {k}</li>)}
            </ul>
          </div>
        )}
      </div>
      {report?.valid && (
        <fieldset style={{ border: 0, padding: 0 }}>
          <legend className="visually-hidden">Import options</legend>
          <p><label><input type="checkbox" checked={publish} onChange={(e) => setPublish(e.target.checked)} /> Publish straight away (learners can see it)</label></p>
          <p><label><input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} /> Allow replacing a lecture that is already published</label></p>
          <p><button type="button" className="btn btn-primary" onClick={() => void doImport()} disabled={busy}>{publish ? 'Import and publish' : 'Import as draft'}</button></p>
        </fieldset>
      )}
    </section>
  );
}
