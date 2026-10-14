import { z } from 'zod';

export const optionSchema = z.object({ id: z.string(), text: z.string() });
export const segmentSchema = z.object({
  id: z.string(),
  order: z.number(),
  type: z.enum(['intro', 'video', 'reading', 'example', 'checkpoint', 'exercise', 'reflection', 'exit_check']),
  title: z.string(),
  required: z.boolean(),
  media: z
    .object({ provider: z.string().nullable(), url: z.string().nullable(), captions_url: z.string().nullable().optional(), transcript: z.string().nullable().optional() })
    .nullable()
    .optional(),
  checkpoint: z
    .object({
      id: z.string(),
      type: z.string(),
      required: z.boolean(),
      question: z.object({ id: z.string(), prompt: z.string(), options: z.array(optionSchema) }),
    })
    .nullable()
    .optional(),
  exercise_id: z.string().nullable().optional(),
  body: z.string().nullable().optional(),
  next_action: z.object({ type: z.string(), exercise_id: z.string().nullable().optional() }),
});
export const manifestSchema = z.object({
  estimated_minutes: z.number().nullable().optional(),
  prerequisites: z.array(z.object({ id: z.string(), title: z.string() })).default([]),
  completion_criteria: z.array(z.string()).default([]),
  attempt_policy: z.string().default(''),
  id: z.string(),
  lecture_number: z.number(),
  title: z.string(),
  summary: z.string(),
  learning_objectives: z.array(z.string()),
  duration_seconds: z.number().nullable(),
  content_version: z.number(),
  segments: z.array(segmentSchema),
});
export const checkpointResultSchema = z.object({
  attempt_id: z.string(),
  is_correct: z.boolean(),
  score: z.number(),
  explanation: z.string(),
  checkpoint_completed: z.boolean(),
});
const counter = z.object({ done: z.number(), total: z.number() });
export const progressSchema = z.object({
  media: counter,
  checkpoints: counter,
  labs: counter,
  mastery: z.object({ best_exercise_score: z.number().nullable(), pass_mark: z.number().nullable(), lecture_completed: z.boolean() }),
});
export const sessionSchema = z.object({
  lecture_state: z.string().optional(),
  progress: progressSchema,
  lecture_id: z.string(),
  current_segment_id: z.string().nullable(),
  playback_position_seconds: z.number(),
  status: z.enum(['not_started', 'in_progress', 'completed']),
  completed_checkpoint_ids: z.array(z.string()),
  completed_exercise_ids: z.array(z.string()),
  checkpoint_results: z.record(z.string(), checkpointResultSchema),
  max_reachable_order: z.number(),
  state_version: z.number(),
});
export const criterionSchema = z.object({ label: z.string(), hidden: z.boolean(), passed: z.boolean(), remediation: z.string().nullable().optional() });
export const submissionSchema = z.object({
  submission_id: z.string(),
  submission_number: z.number(),
  status: z.enum(['queued', 'running', 'passed', 'failed', 'runtime_error', 'timeout', 'error', 'expired', 'cancelled']),
  score: z.number().nullable(),
  raw_score: z.number().nullable().optional(),
  max_score: z.number().optional(),
  pass_threshold: z.number().nullable().optional(),
  hints_used: z.number().optional(),
  hint_penalty: z.number().optional(),
  criteria: z.array(criterionSchema).optional(),
  remediation: z.array(z.object({ criterion: z.string(), text: z.string(), objective: z.string().nullable().optional(), review_segment_id: z.string().nullable().optional(), review_title: z.string().nullable().optional() })).optional(),
  passed_tests: z.number(),
  total_tests: z.number(),
  execution_ms: z.number().nullable(),
  feedback: z.array(z.object({ kind: z.string(), message: z.string() })),
  infrastructure_error: z.boolean(),
  created_at: z.string(),
  content_version: z.number().nullable().optional(),
  test_suite_version: z.number().nullable().optional(),
});
export const exerciseSchema = z.object({
  id: z.string(),
  title: z.string(),
  instructions: z.string(),
  language: z.string(),
  starter_code: z.string(),
  practice_mode: z.string(),
  pass_threshold: z.number(),
  max_attempts: z.number().nullable(),
  objective: z.string().default(''),
  constraints: z.string().default(''),
  visible_examples: z.array(z.object({ description: z.string().optional(), code: z.string(), expected_output: z.string().optional() })).default([]),
  success_criteria: z.array(z.string()).default([]),
  hints_policy: z.string().default(''),
  runtime: z.string().default(''),
  content_version: z.number().nullable().optional(),
  draft_stale: z.boolean().optional(),
  hints_total: z.number(),
  hint_penalty_percent: z.number(),
  hints_revealed: z.array(z.string()),
  best_score: z.number().nullable(),
  attempts_used: z.number(),
  draft: z.string().nullable(),
  unlocked: z.boolean(),
});

export type Criterion = z.infer<typeof criterionSchema>;
export type Progress = z.infer<typeof progressSchema>;
export type Segment = z.infer<typeof segmentSchema>;
export type Manifest = z.infer<typeof manifestSchema>;
export type Session = z.infer<typeof sessionSchema>;
export type CheckpointResult = z.infer<typeof checkpointResultSchema>;
export type Submission = z.infer<typeof submissionSchema>;
export type Exercise = z.infer<typeof exerciseSchema>;
export const FINAL_STATUSES: Submission['status'][] = ['passed', 'failed', 'runtime_error', 'timeout', 'error', 'expired', 'cancelled'];
/** Statuses where the platform (not the learner) is at fault: no score penalty, retry freely. */
export const PLATFORM_FAULT: Submission['status'][] = ['error', 'expired', 'cancelled'];
