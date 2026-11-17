import React from 'react';
import { FlaskConical, Play, RotateCcw } from 'lucide-react';

export const ScenarioLab: React.FC = () => {
  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">Scenario Lab</h1>
        <p className="text-sm text-text-secondary mt-1">
          Deterministic benchmark replays with variable identifier-rotation parameters (§8).
        </p>
      </div>

      <div className="bg-bg-card border border-border-subtle rounded-lg p-8 text-center space-y-3">
        <FlaskConical className="w-10 h-10 text-accent-secondary mx-auto opacity-80" />
        <h3 className="text-base font-semibold text-text-primary">Phase 5 Evaluation & Scenario Milestone</h3>
        <p className="text-xs text-text-muted max-w-md mx-auto">
          The 12 seeded benchmark scenarios (positive, negative, decoy, chronology conflict, benign helpline) and the identifier rotation slider will activate in Phase 5.
        </p>
      </div>
    </div>
  );
};
