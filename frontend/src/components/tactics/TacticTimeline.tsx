import React from 'react';
import { CheckCircle, KeyRound } from 'lucide-react';
import { isCanonicalOrder, stageChips } from './segments';

interface TacticTimelineProps {
  stageSequence?: string[];
  credentialRequested?: boolean;
}

/** Six canonical playbook stages, lit in the order they were observed. Shows only what was detected. */
export const TacticTimeline: React.FC<TacticTimelineProps> = ({ stageSequence, credentialRequested }) => {
  const chips = stageChips(stageSequence);
  const seen = chips.filter(c => c.observed).length;

  return (
    <div className="bg-bg-card border border-border-subtle rounded-lg p-4 space-y-2" aria-label="Tactic timeline">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xs font-semibold text-text-muted uppercase tracking-wider">Tactic timeline</h2>
        <span className="text-[11px] font-mono text-text-muted">
          {seen} of 6 stages observed{seen >= 2 ? (isCanonicalOrder(stageSequence) ? ' · typical order' : ' · unusual order') : ''}
        </span>
      </div>
      <ol className="flex flex-wrap items-center gap-2 text-xs">
        {chips.map((c, idx) => (
          <li
            key={c.stage}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border font-mono text-xs ${
              c.observed
                ? 'bg-accent-primary/10 border-accent-primary/40 text-accent-primary font-semibold'
                : 'bg-bg-main border-border-subtle text-text-muted opacity-60'
            }`}
            aria-label={c.observed ? `${c.stage}, observed ${c.order === 1 ? 'first' : `as number ${c.order}`}` : `${c.stage}, not observed`}
          >
            <span>{idx + 1}.</span>
            <span>{c.stage}</span>
            {c.observed && (
              <>
                <CheckCircle className="w-3.5 h-3.5" aria-hidden="true" />
                <span className="text-[10px] font-normal text-text-secondary">#{c.order}</span>
              </>
            )}
          </li>
        ))}
        {credentialRequested && (
          <li className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border font-mono text-xs bg-accent-secondary/10 border-accent-secondary/40 text-accent-secondary font-semibold"
              aria-label="Credential request observed (parallel branch)">
            <KeyRound className="w-3.5 h-3.5" aria-hidden="true" />
            <span>CREDENTIAL</span>
          </li>
        )}
      </ol>
      {seen === 0 && !credentialRequested && (
        <p className="text-[11px] text-text-muted">
          No playbook stage was detected by the rules. That does not mean the text is safe: the rules only know the
          phrasings in the lexicon.
        </p>
      )}
      <p className="text-[11px] text-text-muted">
        Rule-based detection (lexicon rules). Numbers show the order in which each stage first appeared.
      </p>
    </div>
  );
};
