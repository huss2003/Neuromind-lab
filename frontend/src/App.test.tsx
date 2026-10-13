import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { App } from './App';

describe('App shell', () => {
  it('renders home', () => {
    render(<MemoryRouter><App /></MemoryRouter>);
    expect(screen.getByRole('heading', { name: /neuromind/i })).toBeInTheDocument();
  });
  it('renders not found for unknown routes', () => {
    render(<MemoryRouter initialEntries={['/nope']}><App /></MemoryRouter>);
    expect(screen.getByRole('heading', { name: /page not found/i })).toBeInTheDocument();
  });
});
