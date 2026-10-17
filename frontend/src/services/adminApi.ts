import { z } from 'zod';
import { apiFetch, publicFetch } from './api';

const json = (body: unknown) => ({ body: JSON.stringify(body) });
const q = (params: Record<string, string | number | boolean | undefined | null>) => {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '' && v !== false) p.set(k, String(v)); });
  const s = p.toString();
  return s ? `?${s}` : '';
};

// ---------- administrator ----------
export const adminUser = z.object({ id: z.string(), email: z.string(), display_name: z.string(), role: z.enum(['learner', 'teacher', 'admin']), deactivated: z.boolean(), last_sign_in_at: z.string().nullable().optional(), created_at: z.string().nullable().optional(), email_confirmed: z.boolean().optional() });
export type AdminUser = z.infer<typeof adminUser>;
const usersPage = z.object({ users: z.array(adminUser), total: z.number(), limit: z.number(), offset: z.number() });
export const listAdminUsers = async (p: { q?: string; role?: string; status?: string; limit: number; offset: number }) =>
  usersPage.parse(await apiFetch(`/admin/users${q({ ...p, role: p.role === 'any' ? '' : p.role, status: p.status === 'any' ? '' : p.status })}`));
export const createAdminUser = (b: { email: string; display_name: string; role: string; password: string; course_id?: string }) =>
  apiFetch<{ id: string }>('/admin/users', { method: 'POST', ...json(b) });
export const setUserActive = (id: string, active: boolean) => apiFetch(`/admin/users/${id}/${active ? 'reactivate' : 'deactivate'}`, { method: 'POST' });
export const setUserRole = (id: string, role: string) => apiFetch(`/admin/users/${id}/role`, { method: 'PATCH', ...json({ role }) });

const timing = z.object({ p50: z.number().nullable(), p95: z.number().nullable(), max: z.number().nullable() });
const grading = z.object({ sample: z.number(), by_status: z.record(z.string(), z.number()), queue_wait_seconds: timing, execution_seconds: timing, end_to_end_seconds: timing });
const queueStats = z.object({ queued: z.number(), running: z.number(), oldest_queued_seconds: z.number().nullable() });
const overviewSchema = z.object({
  users: z.object({ learners: z.number(), teachers: z.number(), admins: z.number(), deactivated: z.number() }),
  content: z.object({ courses_published: z.number(), lectures_published: z.number(), lectures_total: z.number() }),
  queue: queueStats, grading_24h: grading, dead_letters: z.number(), open_issues: z.number(),
  health: z.object({ api: z.boolean(), database: z.boolean(), checked_at: z.string() }),
});
export type AdminOverview = z.infer<typeof overviewSchema>;
export const getAdminOverview = async () => overviewSchema.parse(await apiFetch('/admin/overview'));

const queueSchema = z.object({ queue: queueStats, grading_24h: grading, dead_letters: z.array(z.object({ submission_id: z.string(), exercise_id: z.string(), created_at: z.string(), claim_count: z.number().nullable().optional() })), procedure: z.string() });
export const getAdminQueue = async () => queueSchema.parse(await apiFetch('/admin/queue'));
export const requeueSubmission = (id: string) => apiFetch(`/admin/submissions/${id}/requeue`, { method: 'POST' });

const auditEvent = z.object({ id: z.string(), actor_id: z.string().nullable(), event_type: z.string(), resource_type: z.string(), resource_id: z.string().nullable(), request_id: z.string().nullable(), metadata: z.record(z.string(), z.unknown()), created_at: z.string() });
export const listAudit = async (p: { event_type?: string; limit: number; offset: number }) =>
  z.object({ events: z.array(auditEvent), total: z.number() }).parse(await apiFetch(`/admin/audit${q(p)}`));

const exerciseRow = z.object({ lab_kind: z.string().default('code'), scoring: z.string().default('score'), id: z.string(), title: z.string(), status: z.string(), test_suite_version: z.number().nullable().optional(), pass_threshold: z.number().nullable().optional(), max_attempts: z.number().nullable().optional() });
const lectureRow = z.object({ id: z.string(), lecture_number: z.number(), title: z.string(), status: z.enum(['draft', 'published', 'archived']), content_version: z.number().nullable().optional(), exercises: z.array(exerciseRow) });
const courseRow = z.object({ id: z.string(), title: z.string(), status: z.string(), learners_enrolled: z.number(), lectures: z.array(lectureRow) });
export const getAdminCourses = async () => z.object({ courses: z.array(courseRow), note: z.string() }).parse(await apiFetch('/admin/courses'));
const exerciseTests = z.object({ id: z.string(), title: z.string(), lab_kind: z.string().default('code'), scoring: z.string().default('score'), packages: z.array(z.string()).default([]), hints: z.array(z.string()).default([]), hints_max: z.number().default(3),
  tests: z.array(z.object({ test_order: z.number(), hidden: z.boolean(), label: z.string().nullable(), definition: z.record(z.string(), z.unknown()), points: z.number(), remediation: z.string().nullable(), objective: z.string().nullable() })),
  questions: z.array(z.object({ question_order: z.number(), prompt: z.string(), options: z.array(z.object({ id: z.string(), text: z.string() })), correct_option_id: z.string(), explanation: z.string().nullable() })) });
export type ExerciseTests = z.infer<typeof exerciseTests>;
export const getExerciseTests = async (id: string) => exerciseTests.parse(await apiFetch(`/admin/exercises/${id}/tests`));
export const setLectureStatus = (id: string, status: string) => apiFetch(`/admin/lectures/${id}/status`, { method: 'PATCH', ...json({ status }) });

const packReport = z.object({ valid: z.boolean(), problems: z.array(z.string()), missing_tests: z.array(z.string()),
  summary: z.object({ lecture_number: z.number(), title: z.string(), segments: z.number(), checkpoints: z.number(), lab_tests: z.number() }).optional() });
export type PackReport = z.infer<typeof packReport>;
export const validatePack = async (pack: unknown, tests: unknown) =>
  packReport.parse(await apiFetch('/admin/content/packs/validate', { method: 'POST', ...json({ pack, tests }) }));
const packResult = z.object({ lecture_id: z.string(), lecture_number: z.number(), status: z.string(), created: z.boolean() });
export const importPack = async (pack: unknown, tests: unknown, opts: { publish: boolean; replace_published: boolean }) =>
  packResult.parse(await apiFetch('/admin/content/packs/import', { method: 'POST', ...json({ pack, tests, ...opts }) }));

const person = z.object({ id: z.string(), display_name: z.string() });
const cohortRow = z.object({ id: z.string(), course_id: z.string(), name: z.string(), learners: z.array(person), teachers: z.array(person) });
export type AdminCohort = z.infer<typeof cohortRow>;
export const listCohorts = async () => z.object({ cohorts: z.array(cohortRow) }).parse(await apiFetch('/admin/cohorts')).cohorts;
export const createCohort = (course_id: string, name: string) => apiFetch<{ id: string }>('/admin/cohorts', { method: 'POST', ...json({ course_id, name }) });
export const archiveCohort = (id: string) => apiFetch(`/admin/cohorts/${id}`, { method: 'DELETE' });
export const cohortMember = (cohort: string, kind: 'members' | 'teachers', id: string, add: boolean) =>
  apiFetch(`/admin/cohorts/${cohort}/${kind}/${id}`, { method: add ? 'PUT' : 'DELETE' });

const issueRow = z.object({ id: z.string(), reference: z.string(), category: z.string(), message: z.string(), page: z.string().nullable().optional(), status: z.enum(['open', 'triaged', 'resolved', 'dismissed']), admin_note: z.string().nullable().optional(), created_at: z.string(), reporter: z.string() });
export type IssueRow = z.infer<typeof issueRow>;
export const listIssues = async (status: string, limit: number, offset: number) =>
  z.object({ issues: z.array(issueRow), total: z.number() }).parse(await apiFetch(`/admin/issues${q({ status, limit, offset })}`));
export const updateIssue = (id: string, status: string, admin_note?: string) => apiFetch(`/admin/issues/${id}`, { method: 'PATCH', ...json({ status, admin_note }) });
export const getAdminSettings = async () => z.object({ settings: z.array(z.object({ label: z.string(), value: z.string(), note: z.string() })) }).parse(await apiFetch('/admin/settings'));

// ---------- learner extras ----------
const certificate = z.object({ id: z.string(), serial: z.string(), course: z.string(), issued_at: z.string(), completed_lectures: z.number(), holder: z.string() });
export type Certificate = z.infer<typeof certificate>;
export const getCertificates = async () => z.object({ certificates: z.array(certificate) }).parse(await apiFetch('/me/certificates')).certificates;
export const verifyCertificate = async (serial: string) =>
  z.object({ valid: z.boolean(), serial: z.string().optional(), course: z.string().optional(), issued_at: z.string().optional(), holder: z.string().optional() })
    .parse(await publicFetch(`/certificates/verify/${encodeURIComponent(serial)}`));

const portfolioItem = z.object({ id: z.string(), title: z.string(), note: z.string(), created_at: z.string(), exercise: z.string().nullable().optional(), score: z.number().nullable(), submission_id: z.string(), source_code: z.string() });
export type PortfolioItem = z.infer<typeof portfolioItem>;
export const getPortfolio = async () => z.object({ items: z.array(portfolioItem) }).parse(await apiFetch('/me/portfolio')).items;
export const addPortfolio = (submission_id: string, title: string, note: string) => apiFetch<{ id: string; already_added: boolean }>('/me/portfolio', { method: 'POST', ...json({ submission_id, title, note }) });
export const removePortfolio = (id: string) => apiFetch(`/me/portfolio/${id}`, { method: 'DELETE' });

const announcement = z.object({ id: z.string(), title: z.string(), body: z.string(), created_at: z.string(), from: z.string() });
export const getAnnouncements = async () => z.object({ announcements: z.array(announcement) }).parse(await apiFetch('/me/announcements')).announcements;
export const reportIssue = (category: string, message: string, page?: string) => apiFetch<{ id: string; reference: string }>('/me/issues', { method: 'POST', ...json({ category, message, page }) });

// ---------- teacher tools ----------
const myAnnouncement = z.object({ id: z.string(), title: z.string(), body: z.string(), scope: z.string(), course_id: z.string(), created_at: z.string() });
export const listMyAnnouncements = async () => z.object({ announcements: z.array(myAnnouncement) }).parse(await apiFetch('/teacher/announcements')).announcements;
export const createAnnouncement = (course_id: string, title: string, body: string, scope: 'assigned' | 'course') =>
  apiFetch('/teacher/announcements', { method: 'POST', ...json({ course_id, title, body, scope }) });
export const archiveAnnouncement = (id: string) => apiFetch(`/teacher/announcements/${id}`, { method: 'DELETE' });
const teacherCohort = z.object({ id: z.string(), name: z.string(), course_id: z.string(), learners: z.number(), lectures_completed: z.number(), in_progress: z.number(), needs_support: z.number() });
export const getTeacherCohorts = async () => z.object({ cohorts: z.array(teacherCohort) }).parse(await apiFetch('/teacher/cohorts')).cohorts;
const reportRow = z.object({ learner: z.string(), lectures_completed: z.number(), lectures_in_progress: z.number(), exercises_passed: z.number(), attempts: z.number(), average_best_score: z.number().nullable(), needs_support: z.boolean(), last_active: z.string().nullable() });
export type ReportRow = z.infer<typeof reportRow>;
export const getProgressReport = async (cohort?: string) => z.object({ rows: z.array(reportRow) }).parse(await apiFetch(`/teacher/reports/progress${q({ cohort_id: cohort })}`)).rows;
export const progressReportCsvPath = (cohort?: string) => `/teacher/reports/progress${q({ format: 'csv', cohort_id: cohort })}`;
