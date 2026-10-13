import { Fragment, type ReactNode } from 'react';

/** Renders the small, safe markup used in lesson text: ## headings, paragraphs, - lists, ``` code, **bold**, *italic*, `code`.
 *  Everything is built as React elements (never as HTML strings), so lesson text cannot inject markup. */
function inline(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith('`')) out.push(<code key={i++}>{tok.slice(1, -1)}</code>);
    else if (tok.startsWith('**')) out.push(<strong key={i++}>{tok.slice(2, -2)}</strong>);
    else out.push(<em key={i++}>{tok.slice(1, -1)}</em>);
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function RichText({ text, headingLevel = 3 }: { text: string; headingLevel?: 2 | 3 | 4 }) {
  const blocks: ReactNode[] = [];
  const lines = text.replace(/\r\n/g, '\n').split('\n');
  const H = `h${headingLevel}` as 'h2' | 'h3' | 'h4';
  let i = 0;
  let key = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.trim() === '') { i++; continue; }
    if (line.startsWith('```')) {
      const code: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith('```')) code.push(lines[i++]);
      i++;
      blocks.push(<pre key={key++} className="code" tabIndex={0}><code>{code.join('\n')}</code></pre>);
    } else if (line.startsWith('## ')) {
      blocks.push(<H key={key++} className="rt-h">{inline(line.slice(3))}</H>);
      i++;
    } else if (line.startsWith('- ')) {
      const items: string[] = [];
      while (i < lines.length && lines[i].startsWith('- ')) items.push(lines[i++].slice(2));
      blocks.push(<ul key={key++}>{items.map((t, n) => <li key={n}>{inline(t)}</li>)}</ul>);
    } else {
      const para: string[] = [];
      while (i < lines.length && lines[i].trim() !== '' && !/^(```|## |- )/.test(lines[i])) para.push(lines[i++]);
      blocks.push(<p key={key++}>{inline(para.join(' '))}</p>);
    }
  }
  return <div className="richtext">{blocks.map((b, n) => <Fragment key={n}>{b}</Fragment>)}</div>;
}
