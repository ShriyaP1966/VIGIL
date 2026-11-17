import React from 'react';
import { FileText, Download, CheckCircle } from 'lucide-react';

export const Reports: React.FC = () => {
  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">Investigation Reports</h1>
          <p className="text-sm text-text-secondary mt-1">
            Structured forensic exports separating observed facts, model inferences, analyst decisions, and limitations.
          </p>
        </div>
      </div>

      <div className="bg-bg-card border border-border-subtle rounded-lg p-8 text-center space-y-3">
        <FileText className="w-10 h-10 text-accent-primary mx-auto opacity-80" />
        <h3 className="text-base font-semibold text-text-primary">Structured Report Export</h3>
        <p className="text-xs text-text-muted max-w-md mx-auto">
          JSON and CSV forensic exports formatted for incident responders and fraud operations will activate in Phase 6.
        </p>
      </div>
    </div>
  );
};
