import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import type { Segment } from '../services/types';
import { McqCheckpoint } from './McqCheckpoint';

const segment: Segment = {
  id: 's', order: 2, type: 'checkpoint', title: 'Knowledge check 1', required: true, next_action: { type: 'next_segment' },
  checkpoint: { id: 'cp', type: 'mcq', required: true, question: { id: 'q', prompt: 'Which prints text?', options: [{ id: 'a', text: 'echo' }, { id: 'b', text: 'print' }] } },
};
const noop = () => {};

describe('McqCheckpoint', () => {
  it('disables submit until an option is chosen, then submits the chosen option id', async () => {
    const onSubmit = vi.fn();
    render(<McqCheckpoint segment={segment} submitting={false} isExitCheck={false} onSubmit={onSubmit} onContinue={noop} onRetry={noop} />);
    const submit = screen.getByRole('button', { name: 'Submit answer' });
    expect(submit).toBeDisabled();
    await userEvent.click(screen.getByLabelText('print'));
    expect(submit).toBeEnabled();
    await userEvent.click(submit);
    expect(onSubmit).toHaveBeenCalledWith('b');
  });

  it('is keyboard operable and options are in a labelled group', async () => {
    render(<McqCheckpoint segment={segment} submitting={false} isExitCheck={false} onSubmit={noop} onContinue={noop} onRetry={noop} />);
    expect(screen.getByRole('group', { name: 'Which prints text?' })).toBeInTheDocument();
    await userEvent.tab();
    await userEvent.keyboard('{ArrowDown}');
    expect(screen.getAllByRole('radio').some((r) => (r as HTMLInputElement).checked)).toBe(true);
  });

  it('shows text (not colour only) result and explanation, and Continue only when the server completed the checkpoint', () => {
    const { rerender } = render(<McqCheckpoint segment={segment} submitting={false} isExitCheck={false} onSubmit={noop} onContinue={noop} onRetry={noop}
      result={{ attempt_id: 'a', is_correct: false, score: 0, explanation: 'Use print()', checkpoint_completed: false }} />);
    expect(screen.getByText(/Not quite/)).toBeInTheDocument();
    expect(screen.getByText('Use print()')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /continue/i })).toBeNull();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
    rerender(<McqCheckpoint segment={segment} submitting={false} isExitCheck={false} onSubmit={noop} onContinue={noop} onRetry={noop}
      result={{ attempt_id: 'a', is_correct: true, score: 1, explanation: 'Yes', checkpoint_completed: true }} />);
    expect(screen.getByText(/Correct/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Continue lesson' })).toBeInTheDocument();
  });

  it('does not render any answer key field', () => {
    const { container } = render(<McqCheckpoint segment={segment} submitting={false} isExitCheck={false} onSubmit={noop} onContinue={noop} onRetry={noop} />);
    expect(container.innerHTML.toLowerCase()).not.toContain('correct_option');
  });
});
