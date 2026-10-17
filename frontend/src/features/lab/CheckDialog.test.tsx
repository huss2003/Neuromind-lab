import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { CheckDialog, type CheckOutcome } from './CheckDialog';
import type { Submission } from '../../services/types';

const noop = vi.fn();
const errored = { status: 'error', feedback: [{ kind: 'infrastructure', message: 'This exercise has a test configuration problem. Please tell your teacher.' }], criteria: [], remediation: [] } as unknown as Submission;
const props = { open: true, hintsLeft: 3, redoAvailable: false, showFix: false, onDismiss: noop, onShowHint: noop, onBulbHint: noop, onRedo: noop };

describe('CheckDialog when the official checker fails', () => {
  it('keeps the browser verdict visible: failed checks are listed', () => {
    const outcome: CheckOutcome = { phase: 'official', official: errored, quick: { status: 'failed', stdout: '', error: null, criteria: [{ test_order: 1, label: 'name holds your name', passed: false }, { test_order: 2, label: 'Prints something', passed: true }] } };
    render(<CheckDialog {...props} outcome={outcome} />);
    expect(screen.getByRole('heading', { name: 'The checker had a problem' })).toBeInTheDocument();
    expect(screen.getByTestId('quick-summary')).toHaveTextContent('Not passed: name holds your name');
    expect(screen.getByTestId('quick-summary')).not.toHaveTextContent('Prints something');
  });

  it('says when the visible checks passed in the browser, and that nothing is recorded yet', () => {
    const outcome: CheckOutcome = { phase: 'official', official: errored, quick: { status: 'passed', stdout: 'hi', error: null, criteria: [{ test_order: 1, label: 'Prints something', passed: true }] } };
    render(<CheckDialog {...props} outcome={outcome} />);
    expect(screen.getByTestId('quick-summary')).toHaveTextContent('visible checks passed in your browser');
    expect(screen.getByTestId('quick-summary')).toHaveTextContent('not recorded');
    expect(screen.queryByRole('button', { name: 'Show hint' })).not.toBeInTheDocument();
  });

  it('shows nothing extra when the browser runtime was unavailable', () => {
    const outcome: CheckOutcome = { phase: 'official', official: errored, quick: { status: 'unavailable', stdout: '', error: null, criteria: [] } };
    render(<CheckDialog {...props} outcome={outcome} />);
    expect(screen.queryByTestId('quick-summary')).not.toBeInTheDocument();
  });
});
