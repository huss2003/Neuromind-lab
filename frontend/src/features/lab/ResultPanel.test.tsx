import { render, screen } from '@testing-library/react';
import type { Submission } from '../../services/types';
import { ResultPanel } from './ExerciseLab';

const base: Submission = {
  submission_id: 's', submission_number: 2, status: 'failed', score: 50, raw_score: 60, max_score: 100, pass_threshold: 80, hints_used: 1, hint_penalty: 10,
  criteria: [{ label: 'Prints something', hidden: false, passed: true }, { label: 'Hidden check 1', hidden: true, passed: false, remediation: 'Print the variable.' }],
  remediation: [{ criterion: 'Hidden check 1', text: 'Print the variable.' }],
  passed_tests: 1, total_tests: 2, execution_ms: 5, feedback: [{ kind: 'failure', message: 'Some checks are not passed yet.' }], infrastructure_error: false, created_at: '2026-10-13T00:00:00Z',
};

describe('ResultPanel', () => {
  it('shows score, pass mark, hint adjustment, text-labelled criteria and remediation', () => {
    render(<ResultPanel sub={base} passMark={80} />);
    expect(screen.getByText('Needs retry')).toBeInTheDocument();
    expect(screen.getByText(/Score: 50%/)).toBeInTheDocument();
    expect(screen.getByText(/Raw score 60% − 10 points for 1 hint/)).toBeInTheDocument();
    expect(screen.getByText('Passed:')).toBeInTheDocument();
    expect(screen.getByText('Not passed:')).toBeInTheDocument();
    expect(screen.getByText('How to fix it')).toBeInTheDocument();
    expect(screen.getAllByText('Print the variable.').length).toBeGreaterThan(0);
  });
  it('treats an infrastructure error as the platform’s problem, with no score or failure language', () => {
    render(<ResultPanel sub={{ ...base, status: 'error', infrastructure_error: true, score: null, criteria: [], remediation: [] }} passMark={80} />);
    expect(screen.getByText('Grader unavailable')).toBeInTheDocument();
    expect(screen.getByText(/not your code/)).toBeInTheDocument();
    expect(screen.queryByText(/Score:/)).toBeNull();
    expect(screen.queryByText('Needs retry')).toBeNull();
  });
  it('shows Passed with no remediation block', () => {
    render(<ResultPanel sub={{ ...base, status: 'passed', score: 100, raw_score: 100, hints_used: 0, hint_penalty: 0, criteria: [{ label: 'x', hidden: false, passed: true }], remediation: [], passed_tests: 2 }} passMark={80} />);
    expect(screen.getByText('Passed')).toBeInTheDocument();
    expect(screen.queryByText('How to fix it')).toBeNull();
  });
});
