import { Badge } from './Badge';

/** Course-map states are decided by the server (§5): locked, available, in progress, completed, needs attention. */
export function LectureStatus({ status }: { status?: string }) {
  if (status === 'completed') return <Badge kind="success">Completed</Badge>;
  if (status === 'needs_attention') return <Badge kind="warning">Needs attention</Badge>;
  if (status === 'in_progress') return <Badge kind="info">In progress</Badge>;
  if (status === 'locked') return <Badge kind="neutral">Locked</Badge>;
  return <Badge kind="neutral">Available</Badge>;
}

export const lectureAction = (status?: string) =>
  status === 'completed' ? 'Review lecture' : status === 'in_progress' || status === 'needs_attention' ? 'Resume lecture' : 'Start lecture';
