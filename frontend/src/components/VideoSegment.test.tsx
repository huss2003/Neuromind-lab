import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import type { Segment } from '../services/types';
import { VideoSegment } from './VideoSegment';

const segment: Segment = { id: 'v', order: 1, type: 'video', title: 'Intro', required: true, media: { provider: null, url: 'http://x/v.mp4' }, next_action: { type: 'next_segment' } };

describe('VideoSegment', () => {
  beforeEach(() => { HTMLMediaElement.prototype.play = vi.fn().mockRejectedValue(new Error('blocked')); });

  it('shows an explicit Play control when autoplay is blocked', async () => {
    render(<VideoSegment segment={segment} startAt={0} onPlay={vi.fn()} onPause={vi.fn()} onEnded={vi.fn()} onError={vi.fn()} onPosition={vi.fn()} />);
    expect(await screen.findByRole('button', { name: 'Play video' })).toBeInTheDocument();
  });

  it('reports ended / error from the media element and offers a manual continue fallback', async () => {
    const onEnded = vi.fn(); const onError = vi.fn();
    const { container } = render(<VideoSegment segment={segment} startAt={0} onPlay={vi.fn()} onPause={vi.fn()} onEnded={onEnded} onError={onError} onPosition={vi.fn()} />);
    const video = container.querySelector('video')!;
    fireEvent.ended(video);
    fireEvent.error(video);
    expect(onEnded).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledTimes(1);
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(onEnded).toHaveBeenCalledTimes(2);
  });
});
