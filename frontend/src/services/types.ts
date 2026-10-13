import { z } from 'zod';

export const optionSchema = z.object({ id: z.string(), text: z.string() });
export const segmentSchema = z.object({
  id: z.string(),
  order: z.number(),
  type: z.enum(['video', 'checkpoint', 'exercise', 'exit_check']),
  title: z.string(),
  required: z.boolean(),
  media: z.object({ provider: z.string().nullable(), url: z.string().nullable() }).nullable().optional(),
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
  next_action: z.object({ type: z.string(), exercise_id: z.string().nullable().optional() }),
});
export const manifestSchema = z.object({
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
export const sessionSchema = z.object({
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
export const submissionSchema = z.object({
  submission_id: z.string(),
  submission_number: z.number(),
  status: z.enum(['queued', 'running', 'passed', 'failed', 'timeout', 'error']),
  score: z.number().nullable(),
  passed_tests: z.number(),
  total_tests: z.number(),
  execution_ms: z.number().nullable(),
  feedback: z.array(z.object({ kind: z.string(), message: z.string() })),
  infrastructure_error: z.boolean(),
  created_at: z.string(),
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
});

export type Segment = z.infer<typeof segmentSchema>;
export type Manifest = z.infer<typeof manifestSchema>;
export type Session = z.infer<typeof sessionSchema>;
export type CheckpointResult = z.infer<typeof checkpointResultSchema>;
export type Submission = z.infer<typeof submissionSchema>;
export type Exercise = z.infer<typeof exerciseSchema>;
export const FINAL_STATUSES: Submission['status'][] = ['passed', 'failed', 'timeout', 'error'];
