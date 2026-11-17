import React from 'react';
import { Layers, AlertCircle, Info } from 'lucide-react';

export const Campaigns: React.FC = () => {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">Campaign Hypotheses</h1>
          <p className="text-sm text-text-secondary mt-1">
            Grouped scam syndicates derived from connected observed matches and candidate playbook links.
          </p>
        </div>
        <span className="text-xs font-mono uppercase bg-accent-primary/20 text-accent-primary px-2.5 py-1 rounded border border-accent-primary/30">
          Hypothesis Unreviewed
        </span>
      </div>

      <div className="bg-bg-elevated/40 border border-border-subtle rounded-lg p-4 flex items-start gap-3">
        <Info className="w-5 h-5 text-accent-primary shrink-0 mt-0.5" />
        <div className="text-xs text-text-secondary leading-relaxed">
          <strong className="text-text-primary font-semibold">Safety Invariant I4:</strong> A campaign is always categorized as a <span className="text-accent-primary underline">hypothesis</span> until an analyst explicitly issues an acceptance review. No unilateral criminal attribution is made.
        </div>
      </div>

      <div className="bg-bg-card border border-border-subtle rounded-lg p-8 text-center space-y-3">
        <Layers className="w-10 h-10 text-accent-primary mx-auto opacity-80" />
        <h3 className="text-base font-semibold text-text-primary">Phase 3 Intelligence Milestone</h3>
        <p className="text-xs text-text-muted max-w-md mx-auto">
          Connected component clustering over observed matches and playbook candidate extensions will be fully activated in Phase 3.
        </p>
      </div>
    </div>
  );
};
