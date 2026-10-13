import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import { App } from './App';

vi.mock('./auth/AuthProvider', () => ({ useAuth: () => ({ loading: false, session: null, role: null, signOut: async () => {} }) }));

const wrap = (path: string) =>
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></QueryClientProvider>);

describe('App shell', () => {
  it('sends signed-out users from protected pages to sign-in', () => {
    wrap('/');
    expect(screen.getByRole('heading', { name: /sign in/i })).toBeInTheDocument();
  });
  it('protects the teacher page from signed-out users', () => {
    wrap('/teacher');
    expect(screen.getByRole('heading', { name: /sign in/i })).toBeInTheDocument();
  });
  it('renders not found for unknown routes', () => {
    wrap('/nope');
    expect(screen.getByRole('heading', { name: /page not found/i })).toBeInTheDocument();
  });
});
