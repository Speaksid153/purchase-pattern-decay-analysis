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
        <main className="min-h-screen bg-slate-50 dark:bg-[#121418] text-slate-900 dark:text-slate-100 flex items-center justify-center p-6">
          <section className="max-w-md w-full rounded-2xl border border-rose-200 dark:border-rose-900 bg-white dark:bg-[#1c1f26] p-8 text-center shadow-lg">
            <h1 className="text-lg font-bold">Something went wrong</h1>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">The dashboard could not be displayed. Reload to try again.</p>
            <button onClick={() => window.location.reload()} className="mt-5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">Reload dashboard</button>
          </section>
        </main>
      );
    }
    return this.child;
  }
}
