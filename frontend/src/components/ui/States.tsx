import React from 'react';
import { AlertCircle, Inbox } from 'lucide-react';

/** Loading placeholder: grey bars with the page's shape, announced once as "Loading". */
export const Skeleton: React.FC<{ rows?: number; label?: string }> = ({ rows = 4, label = 'Loading' }) => (
  <div role="status" aria-label={label} className="space-y-3 animate-pulse">
    {Array.from({ length: rows }, (_, i) => (
      <div key={i} className="h-12 rounded-md bg-bg-elevated/60 border border-border-subtle" />
    ))}
    <span className="sr-only">{label}…</span>
  </div>
);

export const ErrorBanner: React.FC<{ message: string; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div role="alert" className="flex items-start gap-3 rounded-lg border border-risk-critical/40 bg-risk-critical/10 p-4 text-sm">
    <AlertCircle className="w-4 h-4 text-risk-critical shrink-0 mt-0.5" aria-hidden="true" />
    <div className="flex-1 text-text-primary break-words">{message}</div>
    {onRetry && (
      <button
        type="button"
        onClick={onRetry}
        className="text-xs font-semibold text-accent-primary underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary rounded"
      >
        Try again
      </button>
    )}
  </div>
);

export const EmptyState: React.FC<{ title: string; children?: React.ReactNode; action?: React.ReactNode }> = (
  { title, children, action },
) => (
  <div className="rounded-lg border border-border-subtle bg-bg-card p-8 text-center space-y-2">
    <Inbox className="w-8 h-8 mx-auto text-text-muted" aria-hidden="true" />
    <h2 className="text-sm font-semibold text-text-primary">{title}</h2>
    {children && <div className="text-xs text-text-secondary max-w-md mx-auto">{children}</div>}
    {action && <div className="pt-2">{action}</div>}
  </div>
);
