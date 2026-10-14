import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import type { Segment, Submission } from '../../services/types';
import { ResultPanel } from './ExerciseLab';

const base: Submission = {
  submission_id: 's', submission_number: 2, status: 'failed', score: 50, raw_score: 60, max_score: 100, pass_threshold: 80, hints_used: 1, hint_penalty: 10,
  criteria: [{ label: 'Prints something', hidden: false, passed: true }, { label: 'Hidden check 1', hidden: true, passed: false, remediation: 'Print the variable.' }],
  remediation: [{ criterion: 'Hidden check 1', text: 'Print the variable.', objective: 'Print output', review_segment_id: 'seg-5', review_title: 'Practical demonstration' }],
  passed_tests: 1, total_tests: 2, execution_ms: 5, feedback: [{ kind: 'failure', message: 'Some checks are not passed yet.' }], infrastructure_error: false, created_at: '2026-10-13T00:00:00Z',
};
const section: Segment = { id: 'seg-5', order: 5, type: 'video', title: 'Practical demonstration', required: true, media: { provider: null, url: 'http://x/v.mp4' }, next_action: { type: 'next_segment' } };

describe('ResultPanel', () => {
  it('shows score, pass mark, hint adjustment, text-labelled criteria and objective-mapped remediation', () => {
    render(<ResultPanel sub={base} passMark={80} />);
    expect(screen.getByText('Needs work')).toBeInTheDocument();
    expect(screen.getByText(/Score: 50%/)).toBeInTheDocument();
    expect(screen.getByText(/Raw score 60% − 10 points for 1 hint/)).toBeInTheDocument();
    expect(screen.getByText('Passed:')).toBeInTheDocument();
    expect(screen.getByText('Not passed:')).toBeInTheDocument();
    expect(screen.getByText('How to fix it')).toBeInTheDocument();
    expect(screen.getByText('Print output:')).toBeInTheDocument();
    expect(screen.getByText(/your code is kept/i)).toBeInTheDocument();
  });

  it('offers to replay the mapped section and to reveal a hint, without leaving the task', async () => {
    const onReview = vi.fn(); const onShowHint = vi.fn();
    render(<ResultPanel sub={base} passMark={80} sections={[section]} onReview={onReview} onShowHint={onShowHint} />);
    await userEvent.click(screen.getByRole('button', { name: /Review “Practical demonstration”/ }));
    expect(onReview).toHaveBeenCalledWith(section);
    await userEvent.click(screen.getByRole('button', { name: 'show a hint' }));
    expect(onShowHint).toHaveBeenCalled();
  });

  it.each([
    ['error', 'System error — not your fault', /problem with the grading system, not your code/],
    ['expired', 'Expired — not your fault', /not because of your code/],
  ] as const)('treats %s as the platform’s problem: no score, no failure language', (status, label, help) => {
    render(<ResultPanel sub={{ ...base, status, infrastructure_error: true, score: null, criteria: [], remediation: [] }} passMark={80} />);
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(screen.getByText(help)).toBeInTheDocument();
    expect(screen.queryByText(/Score:/)).toBeNull();
    expect(screen.queryByText('Needs work')).toBeNull();
    expect(screen.getByText(/best score is unchanged/)).toBeInTheDocument();
  });

  it('describes a runtime error and a time limit as the learner’s program, with guidance', () => {
    const { rerender } = render(<ResultPanel sub={{ ...base, status: 'runtime_error', score: 0, remediation: [], criteria: [] }} passMark={80} />);
    expect(screen.getByText('Runtime error')).toBeInTheDocument();
    expect(screen.getByText(/stopped with an error/)).toBeInTheDocument();
    rerender(<ResultPanel sub={{ ...base, status: 'timeout', score: 0, remediation: [], criteria: [] }} passMark={80} />);
    expect(screen.getByText('Time limit')).toBeInTheDocument();
    expect(screen.getByText(/loop that never ends/)).toBeInTheDocument();
  });

  it('shows Passed with no remediation block', () => {
    render(<ResultPanel sub={{ ...base, status: 'passed', score: 100, raw_score: 100, hints_used: 0, hint_penalty: 0, criteria: [{ label: 'x', hidden: false, passed: true }], remediation: [], passed_tests: 2 }} passMark={80} />);
    expect(screen.getByText('Passed')).toBeInTheDocument();
    expect(screen.queryByText('How to fix it')).toBeNull();
  });
});
