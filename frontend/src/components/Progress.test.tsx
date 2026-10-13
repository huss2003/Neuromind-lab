import { render, screen } from '@testing-library/react';
import { ProgressBar, ProgressRing } from './Progress';

describe('progress components', () => {
  it('ProgressBar exposes value as text and ARIA, not only as a bar', () => {
    render(<ProgressBar label="Knowledge checks" done={2} total={3} />);
    const bar = screen.getByRole('progressbar', { name: 'Knowledge checks' });
    expect(bar).toHaveAttribute('aria-valuenow', '2');
    expect(bar).toHaveAttribute('aria-valuetext', '2 of 3');
    expect(screen.getByText('2 of 3')).toBeInTheDocument();
  });
  it('handles an empty total without dividing by zero', () => {
    render(<ProgressBar label="Labs" done={0} total={0} />);
    expect(screen.getByRole('progressbar', { name: 'Labs' })).toHaveAttribute('aria-valuetext', '0 of 0');
  });
  it('ProgressRing has an accessible summary', () => {
    render(<ProgressRing done={1} total={4} label="lectures completed" />);
    expect(screen.getByLabelText('lectures completed: 1 of 4')).toBeInTheDocument();
  });
});
