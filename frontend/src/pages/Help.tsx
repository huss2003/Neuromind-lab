import { Link } from 'react-router-dom';

const FAQ: [string, string][] = [
  ['Is my work saved?', 'Your code is saved to your account a moment after you stop typing. The editor shows “All changes saved” only once the server has confirmed it. If you see “Not saved yet”, keep the page open or copy your code.'],
  ['What is the difference between Run and Submit for grading?', 'Run practice runs in your browser, is private and does not count. Submit for grading creates an official attempt that is checked by the grader and can update your best score.'],
  ['How many attempts do I get?', 'You can practise as often as you like. Only your best valid score counts, and a new attempt never lowers it. Platform problems are never counted against you.'],
  ['What does “System error — not your fault” mean?', 'The grader could not finish because of a platform problem. The attempt was not marked incorrect and your best score is unchanged. Submit again.'],
  ['How is lecture completion decided?', 'The server decides. A lecture is complete when you have finished every required section, passed the checkpoints and the exit check, and reached the pass mark on the lab. Playing a video alone never completes a lecture.'],
  ['Why is a lecture locked?', 'Some lectures need an earlier lecture to be completed first. The course map names the prerequisite.'],
];

/** S18 / T16 — guidance and FAQ. */
export function Help() {
  return (
    <main className="page narrow">
      <h1>Help</h1>
      <section className="card" aria-labelledby="faq-h">
        <h2 id="faq-h">Common questions</h2>
        {FAQ.map(([q, a]) => (
          <details key={q} className="faq">
            <summary>{q}</summary>
            <p>{a}</p>
          </details>
        ))}
      </section>
      <section className="card" aria-labelledby="report-h">
        <h2 id="report-h">Report a problem</h2>
        <div className="notice notice-warning">
          <strong>Never share passwords, keys or other secrets</strong> in a message, a screenshot or your code.
        </div>
        <p>
          An in-app problem report form is not available yet. Until it is, tell your teacher: include the lecture
          number, what you expected, what happened and, if it was a grading attempt, the attempt number shown in your
          attempt history.
        </p>
      </section>
      <p><Link to="/welcome">Read the lab walkthrough again</Link> · <Link to="/privacy">Privacy notice</Link> · <Link to="/terms">Terms of use</Link></p>
    </main>
  );
}
