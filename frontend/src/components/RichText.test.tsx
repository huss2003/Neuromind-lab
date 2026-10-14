import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { RichText } from './RichText';

describe('RichText', () => {
  it('renders headings, paragraphs, lists, code blocks and inline formatting', () => {
    render(<RichText text={'## Title\n\nSome **bold** and `code` and *soft* text.\n\n- one\n- two\n\n```\nprint(1)\n```'} />);
    expect(screen.getByRole('heading', { name: 'Title' })).toBeInTheDocument();
    expect(screen.getByText('bold').tagName).toBe('STRONG');
    expect(screen.getAllByText('code')[0].tagName).toBe('CODE');
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getByText('print(1)')).toBeInTheDocument();
  });

  it('never turns lesson text into HTML', () => {
    const { container } = render(<RichText text={'<img src=x onerror=alert(1)> and <script>alert(1)</script>'} />);
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('script')).toBeNull();
    expect(container.textContent).toContain('<img src=x');
  });

  it('keeps wrapped lines in one paragraph', () => {
    render(<RichText text={'first line\nsecond line'} />);
    expect(screen.getAllByText('first line second line')).toHaveLength(1);
  });
});
