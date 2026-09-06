import { Component, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };
  private readonly child: ReactNode;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.child = props.children;
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="error-page">
          <section className="error-panel" role="alert">
            <p className="eyebrow">Application error</p>
            <h1>Purchase pattern analysis could not be displayed</h1>
            <p>Reload the dashboard to try the request again.</p>
            <button type="button" onClick={() => window.location.reload()} className="primary-button">Reload dashboard</button>
          </section>
        </main>
      );
    }
    return this.child;
  }
}
