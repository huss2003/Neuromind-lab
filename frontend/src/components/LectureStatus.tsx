import { Badge } from './Badge';

export function LectureStatus({ status }: { status?: string }) {
  if (status === 'completed') return <Badge kind="success">Completed</Badge>;
  if (status === 'in_progress') return <Badge kind="info">In progress</Badge>;
  return <Badge kind="neutral">Not started</Badge>;
}

export const lectureAction = (status?: string) => (status === 'completed' ? 'Review lecture' : status === 'in_progress' ? 'Resume lecture' : 'Start lecture');
