import { Component, type ErrorInfo, type ReactNode } from 'react';

/** Last line of defence: a rendering bug shows a calm recovery screen instead of a blank page. No stack trace is shown. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error('ui_error', error.name, info.componentStack?.split('\n')[1]?.trim()); }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="page narrow" style={{ paddingTop: '12vh' }}>
        <div role="alert" className="card">
          <h1>Something went wrong on this page</h1>
          <p>Your work is saved. Reload the page to continue. If it keeps happening, tell your teacher which page you were on.</p>
          <div className="actions">
            <button className="btn btn-primary" onClick={() => window.location.reload()}>Reload page</button>
            <a className="btn btn-secondary" href="/">Go to dashboard</a>
          </div>
        </div>
      </main>
    );
  }
}
