import React from 'react';
import { Compass } from 'lucide-react';
import { Link } from '../router';

/** Shown for any URL the app does not know. The requested path is shown as plain text (never as HTML). */
export const NotFound: React.FC<{ path: string }> = ({ path }) => (
  <div className="p-4 sm:p-8 max-w-xl mx-auto text-center space-y-4" role="alert">
    <Compass className="w-10 h-10 mx-auto text-text-muted" aria-hidden="true" />
    <h1 className="text-xl font-bold text-text-primary">Page not found</h1>
    <p className="text-sm text-text-secondary">
      There is no page at <span className="font-mono text-text-primary break-all">{path}</span>. It may have been
      moved, or the link may be mistyped.
    </p>
    <div className="flex flex-wrap items-center justify-center gap-3 text-sm">
      <Link to="/" className="inline-flex items-center bg-accent-primary hover:bg-sky-400 text-bg-main font-semibold px-4 py-2 rounded-md transition-colors">
        Go to Overview
      </Link>
      <Link to="/campaigns" className="text-accent-primary hover:underline">Campaign hypotheses</Link>
      <Link to="/graph" className="text-accent-primary hover:underline">Intelligence graph</Link>
    </div>
  </div>
);
