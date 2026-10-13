export function Loading({ label = 'Loading…' }: { label?: string }) {
  return <p role="status" aria-live="polite">{label}</p>;
}

export function ErrorMessage({ message }: { message: string }) {
  return <p role="alert">{message}</p>;
}
