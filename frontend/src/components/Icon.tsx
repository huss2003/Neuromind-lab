const PATHS: Record<string, string> = {
  play: 'M8 5v14l11-7z',
  check: 'M5 13l4 4L19 7',
  lock: 'M6 11h12v9H6zM8 11V8a4 4 0 118 0v3',
  code: 'M9 8l-5 4 5 4M15 8l5 4-5 4M13 5l-2 14',
  quiz: 'M12 17h.01M9.5 9a2.5 2.5 0 115 0c0 1.5-2.5 2-2.5 4M4 4h16v16H4z',
  home: 'M4 11l8-7 8 7v9h-5v-6H9v6H4z',
  user: 'M12 12a4 4 0 100-8 4 4 0 000 8zM5 20a7 7 0 0114 0',
  logout: 'M10 5H5v14h5M14 8l4 4-4 4M18 12H9',
  chart: 'M5 20V10M12 20V4M19 20v-7',
  alert: 'M12 8v5M12 17h.01M10.3 4.2L3 18a1.5 1.5 0 001.3 2.2h15.4A1.5 1.5 0 0021 18L13.7 4.2a1.5 1.5 0 00-3.4 0z',
  info: 'M12 11v6M12 7.5h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  bulb: 'M9 18h6M10 21h4M12 3a6 6 0 00-3 11c.7.6 1 1.3 1 2h4c0-.7.3-1.4 1-2a6 6 0 00-3-11z',
  refresh: 'M4 12a8 8 0 0114-5l2 2M20 4v5h-5M20 12a8 8 0 01-14 5l-2-2M4 20v-5h5',
  flag: 'M5 21V4h11l-2 4 2 4H5',
  book: 'M5 4h11a3 3 0 013 3v13H8a3 3 0 01-3-3zM5 17a3 3 0 013-3h11',
  video: 'M4 6h11v12H4zM15 10l5-3v10l-5-3',
  trophy: 'M8 4h8v6a4 4 0 01-8 0zM5 5h3M16 5h3M12 14v4M8 20h8',
  reset: 'M4 4v6h6M4.5 15a8 8 0 100-6',
};

export function Icon({ name, size = 20 }: { name: keyof typeof PATHS | string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d={PATHS[name] ?? PATHS.info} />
    </svg>
  );
}
