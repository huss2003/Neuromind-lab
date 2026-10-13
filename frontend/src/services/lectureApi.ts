import { z } from 'zod';
import { apiFetch } from './api';
import {
  checkpointResultSchema, exerciseSchema, manifestSchema, sessionSchema, submissionSchema,
  type CheckpointResult, type Exercise, type Manifest, type Session, type Submission,
} from './types';

const courseSchema = z.object({ id: z.string(), slug: z.string(), title: z.string(), description: z.string() });
const lectureRow = z.object({ id: z.string(), module_id: z.string().nullable().optional(), lecture_number: z.number(), title: z.string(), summary: z.string(), duration_seconds: z.number().nullable() });
const moduleRow = z.object({ id: z.string(), module_number: z.number(), title: z.string(), description: z.string(), lectures: z.array(lectureRow) });
const courseDetail = courseSchema.extend({ lectures: z.array(lectureRow), modules: z.array(moduleRow) });
const progressSchema = z.object({ sessions: z.array(z.object({ lecture_id: z.string(), status: z.string(), current_segment_id: z.string().nullable(), completed_at: z.string().nullable() })) });

export type CourseDetail = z.infer<typeof courseDetail>;
export type LectureRow = z.infer<typeof lectureRow>;
export type ProgressList = z.infer<typeof progressSchema>;

const json = (body: unknown) => ({ body: JSON.stringify(body) });

export const getCourses = async () => z.object({ courses: z.array(courseSchema) }).parse(await apiFetch('/courses')).courses;
export const getCourse = async (id: string): Promise<CourseDetail> => courseDetail.parse(await apiFetch(`/courses/${id}`));
export const getMyProgress = async (): Promise<ProgressList> => progressSchema.parse(await apiFetch('/me/progress'));
export const getManifest = async (id: string): Promise<Manifest> => manifestSchema.parse(await apiFetch(`/lectures/${id}`));
export const getSession = async (id: string): Promise<Session> => sessionSchema.parse(await apiFetch(`/lectures/${id}/session`));

export const saveSession = async (id: string, segmentId: string, position: number, version: number): Promise<Session> =>
  sessionSchema.parse(await apiFetch(`/lectures/${id}/session`, { method: 'PATCH', ...json({ current_segment_id: segmentId, playback_position_seconds: Math.floor(position), state_version: version }) }));

export const completeLecture = async (id: string): Promise<Session> =>
  sessionSchema.parse(await apiFetch(`/lectures/${id}/complete`, { method: 'POST', ...json({}) }));

export const submitAnswer = async (checkpointId: string, questionId: string, optionId: string, key: string): Promise<CheckpointResult> =>
  checkpointResultSchema.parse(await apiFetch(`/checkpoints/${checkpointId}/attempts`, {
    method: 'POST', headers: { 'Idempotency-Key': key }, ...json({ question_id: questionId, selected_option_id: optionId }),
  }));

export const getExercise = async (id: string): Promise<Exercise> => exerciseSchema.parse(await apiFetch(`/exercises/${id}`));

export const submitCode = async (exerciseId: string, code: string, key: string): Promise<{ submission_id: string }> =>
  z.object({ submission_id: z.string() }).parse(await apiFetch(`/exercises/${exerciseId}/submissions`, {
    method: 'POST', headers: { 'Idempotency-Key': key }, ...json({ source_code: code }),
  }));

export const getSubmission = async (id: string): Promise<Submission> => submissionSchema.parse(await apiFetch(`/submissions/${id}`));
export const listSubmissions = async (exerciseId: string): Promise<{ submissions: Submission[]; best_score: number | null }> =>
  z.object({ submissions: z.array(submissionSchema), best_score: z.number().nullable() }).parse(await apiFetch(`/exercises/${exerciseId}/submissions`));

export const revealHint = async (exerciseId: string, index: number) =>
  z.object({ hint_index: z.number(), text: z.string(), hints_revealed: z.number(), hints_total: z.number(), penalty_percent: z.number() })
    .parse(await apiFetch(`/exercises/${exerciseId}/hints`, { method: 'POST', ...json({ hint_index: index }) }));

export const saveDraft = async (exerciseId: string, code: string): Promise<void> => {
  await apiFetch(`/exercises/${exerciseId}/draft`, { method: 'PUT', ...json({ source_code: code }) });
};

export const getMyFeedback = async () =>
  z.object({ feedback: z.array(z.object({ id: z.string(), body: z.string(), created_at: z.string() })) }).parse(await apiFetch('/me/feedback')).feedback;

// ---- teacher ----
const teacherLearner = z.object({ id: z.string(), display_name: z.string() });
export type TeacherLearner = z.infer<typeof teacherLearner>;
export const getTeacherSummary = async () =>
  z.object({ assigned_learners: z.number(), lectures_completed: z.number(), lectures_in_progress: z.number(), submissions_passed: z.number(), submissions_needing_retry: z.number(), infrastructure_failures: z.number() })
    .parse(await apiFetch('/teacher/summary'));
export const listLearners = async (q: string, limit: number, offset: number) =>
  z.object({ learners: z.array(teacherLearner), total: z.number(), limit: z.number(), offset: z.number() })
    .parse(await apiFetch(`/teacher/learners?limit=${limit}&offset=${offset}${q ? `&q=${encodeURIComponent(q)}` : ''}`));

const resultsSchema = z.object({
  learner: teacherLearner,
  sessions: z.array(z.object({ lecture_id: z.string(), lecture: z.string().nullable().optional(), status: z.string(), completed_at: z.string().nullable(), last_seen_at: z.string() })),
  checkpoint_attempts: z.array(z.object({ checkpoint_id: z.string(), checkpoint: z.string().nullable().optional(), is_correct: z.boolean(), score: z.number(), submitted_at: z.string() })),
  submissions: z.array(z.object({
    submission_id: z.string(), exercise_id: z.string(), exercise: z.string().nullable().optional(), number: z.number(), status: z.string(),
    score: z.number().nullable(), raw_score: z.number().nullable().optional(), hints_used: z.number(), passed_tests: z.number(), total_tests: z.number(),
    infrastructure_failure: z.boolean(), created_at: z.string(),
  })),
  best_scores: z.array(z.object({ exercise_id: z.string(), exercise: z.string().nullable().optional(), best_score: z.number().nullable() })),
  feedback: z.array(z.object({ id: z.string(), body: z.string(), published: z.boolean(), created_at: z.string(), submission_id: z.string().nullable().optional() })),
});
export type LearnerResults = z.infer<typeof resultsSchema>;
export const getLearnerResults = async (id: string): Promise<LearnerResults> => resultsSchema.parse(await apiFetch(`/teacher/learners/${id}/results`));

const detailSchema = z.object({
  submission_id: z.string(), exercise: z.string().nullable().optional(), number: z.number(), status: z.string(), score: z.number().nullable(),
  raw_score: z.number().nullable().optional(), max_score: z.number(), pass_threshold: z.number().nullable(), hints_used: z.number(), hint_penalty: z.number(),
  source_code: z.string(), criteria: z.array(z.object({ label: z.string(), hidden: z.boolean(), passed: z.boolean() })),
  feedback_messages: z.array(z.object({ kind: z.string(), message: z.string() })), execution_ms: z.number().nullable(), created_at: z.string(),
  infrastructure_failure: z.boolean(),
  evidence: z.object({ grader_version: z.string().nullable(), test_suite_version: z.number().nullable(), content_version: z.number().nullable(), correlation_id: z.string().nullable(), started_at: z.string().nullable(), finished_at: z.string().nullable() }),
});
export type SubmissionDetail = z.infer<typeof detailSchema>;
export const getSubmissionDetail = async (id: string): Promise<SubmissionDetail> => detailSchema.parse(await apiFetch(`/teacher/submissions/${id}`));
export const addFeedback = async (learnerId: string, body: string, publish: boolean, submissionId?: string) =>
  apiFetch(`/teacher/learners/${learnerId}/feedback`, { method: 'POST', ...json({ body, publish, submission_id: submissionId ?? null }) });
