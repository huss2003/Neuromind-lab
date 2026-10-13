export type BadgeKind = 'neutral' | 'info' | 'success' | 'warning' | 'danger';
/** Status is always conveyed with text + symbol, never colour alone. */
const SYMBOL: Record<BadgeKind, string> = { neutral: '○', info: '▶', success: '✓', warning: '!', danger: '✕' };
export function Badge({ kind, children }: { kind: BadgeKind; children: string }) {
  return <span className={`badge badge-${kind}`}><span aria-hidden="true">{SYMBOL[kind]} </span>{children}</span>;
}
