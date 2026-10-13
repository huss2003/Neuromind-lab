import type { BadgeKind } from './Badge';
import type { Submission } from '../services/types';

/** Learner-facing vocabulary from the flow spec §9.2. Platform faults are never presented as the learner's mistake. */
export const STATUS_LABEL: Record<Submission['status'], [BadgeKind, string]> = {
  queued: ['info', 'Queued'],
  running: ['info', 'Running'],
  passed: ['success', 'Passed'],
  failed: ['warning', 'Needs work'],
  runtime_error: ['warning', 'Runtime error'],
  timeout: ['warning', 'Time limit'],
  error: ['danger', 'System error — not your fault'],
  expired: ['danger', 'Expired — not your fault'],
  cancelled: ['neutral', 'Cancelled'],
};

export const STATUS_HELP: Partial<Record<Submission['status'], string>> = {
  failed: 'Your code ran, but some requirements are not met yet. Use the guidance below, then try again.',
  runtime_error: 'Your program stopped with an error. The message below shows where. Fix it and submit again.',
  timeout: 'Your program ran for too long and was stopped. Check for a loop that never ends or work that can be simplified.',
  error: 'This was a problem with the grading system, not your code. This attempt was not judged and your best score is unchanged. Please try again.',
  expired: 'Grading took too long and was stopped, not because of your code. Your best score is unchanged. Please submit again.',
  cancelled: 'This submission was cancelled before it finished. You can submit again.',
};
