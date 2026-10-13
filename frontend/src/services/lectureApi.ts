import { z } from 'zod';
import { apiFetch } from './api';
import {
  checkpointResultSchema, exerciseSchema, manifestSchema, sessionSchema, submissionSchema,
  type CheckpointResult, type Exercise, type Manifest, type Session, type Submission,
} from './types';

const courseSchema = z.object({ id: z.string(), slug: z.string(), title: z.string(), description: z.string() });
const lectureRow = z.object({ id: z.string(), lecture_number: z.number(), title: z.string(), summary: z.string(), duration_seconds: z.number().nullable() });
const courseDetail = courseSchema.extend({ lectures: z.array(lectureRow) });
const progressSchema = z.object({ sessions: z.array(z.object({ lecture_id: z.string(), status: z.string(), current_segment_id: z.string().nullable(), completed_at: z.string().nullable() })) });

export type CourseDetail = z.infer<typeof courseDetail>;
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
export const listSubmissions = async (exerciseId: string): Promise<Submission[]> =>
  z.object({ submissions: z.array(submissionSchema) }).parse(await apiFetch(`/exercises/${exerciseId}/submissions`)).submissions;

const teacherLearner = z.object({ id: z.string(), display_name: z.string() });
export const listLearners = async () => z.object({ learners: z.array(teacherLearner) }).parse(await apiFetch('/teacher/learners')).learners;
const resultsSchema = z.object({
  learner: teacherLearner,
  sessions: z.array(z.object({ lecture_id: z.string(), status: z.string(), completed_at: z.string().nullable(), last_seen_at: z.string() })),
  checkpoint_attempts: z.array(z.object({ checkpoint_id: z.string(), is_correct: z.boolean(), score: z.number(), submitted_at: z.string() })),
  submissions: z.array(z.object({ submission_id: z.string(), exercise_id: z.string(), number: z.number(), status: z.string(), score: z.number().nullable(), passed_tests: z.number(), total_tests: z.number(), created_at: z.string() })),
});
export type LearnerResults = z.infer<typeof resultsSchema>;
export const getLearnerResults = async (id: string): Promise<LearnerResults> => resultsSchema.parse(await apiFetch(`/teacher/learners/${id}/results`));
