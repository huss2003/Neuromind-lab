/** Logo mark: three nodes joined by a signal path. Decorative; the visible name sits beside it. */
export function BrandMark({ size = 36 }: { size?: number }) {
  return (
    <svg className="brand-mark" width={size} height={size} viewBox="0 0 36 36" aria-hidden="true" focusable="false">
      <rect width="36" height="36" rx="10" fill="#2F54FF" />
      <path d="M9 24 L16 13 L21 21 L28 11" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" opacity=".9" />
      <circle cx="9" cy="24" r="2.8" fill="#fff" />
      <circle cx="16" cy="13" r="2.8" fill="#fff" />
      <circle cx="21" cy="21" r="2.8" fill="#fff" />
      <circle cx="28" cy="11" r="3.4" fill="#FFB020" />
    </svg>
  );
}

export function BrandName() {
  return <span className="brand-name">NeuroMind<span className="brand-sub"> Lab</span></span>;
}
