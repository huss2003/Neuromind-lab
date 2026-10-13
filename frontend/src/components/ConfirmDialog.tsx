import { useEffect, useRef, type ReactNode } from 'react';

interface Props { open: boolean; title: string; children: ReactNode; confirmLabel: string; onConfirm: () => void; onCancel: () => void; destructive?: boolean }

/** Native <dialog>: focus is trapped and returned by the browser; Escape cancels. */
export function ConfirmDialog({ open, title, children, confirmLabel, onConfirm, onCancel, destructive }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      if (d.showModal) d.showModal();
      else d.setAttribute('open', '');
    }
    if (!open && d.open) {
      if (d.close) d.close();
      else d.removeAttribute('open');
    }
  }, [open]);
  return (
    <dialog ref={ref} className="dialog" aria-labelledby="dlg-title" onCancel={(e) => { e.preventDefault(); onCancel(); }}>
      <h2 id="dlg-title">{title}</h2>
      <div>{children}</div>
      <div className="actions">
        <button className="btn btn-secondary" onClick={onCancel} autoFocus>Cancel</button>
        <button className={`btn ${destructive ? 'btn-danger' : 'btn-primary'}`} onClick={onConfirm}>{confirmLabel}</button>
      </div>
    </dialog>
  );
}
