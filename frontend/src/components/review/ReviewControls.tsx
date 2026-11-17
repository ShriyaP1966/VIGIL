import React, { useState } from 'react';
import { AlertTriangle, CheckCircle, X } from 'lucide-react';
import type { ReviewDecision } from '../../types';

interface ReviewHistoryEntry {
  id: number;
  decision: string;
  note?: string | null;
  previous_status: string;
  new_status: string;
  created_at: string;
}

interface ReviewControlsProps {
  /** What is being reviewed, for labels: "link" or "hypothesis". */
  subject: 'link' | 'hypothesis';
  state: string;                       // UNREVIEWED | ACCEPTED | REJECTED | FLAGGED
  history: ReviewHistoryEntry[];
  canReview: boolean;                  // false in the hosted static demo
  onReview: (decision: ReviewDecision, note: string) => Promise<void>;
}

const pretty = (s: string) => s.replace(/_/g, ' ').toLowerCase();

/** Analyst Accept / Reject / Flag with an optional note. Notes are stored, so secrets are removed server-side. */
export const ReviewControls: React.FC<ReviewControlsProps> = ({ subject, state, history, canReview, onReview }) => {
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (decision: ReviewDecision) => {
    setBusy(true);
    setError(null);
    try {
      await onReview(decision, note);
      setNote('');
    } catch (e: any) {
      setError(e?.message || 'Could not save the review.');
    } finally {
      setBusy(false);
    }
  };

  const btn = 'flex items-center justify-center gap-1 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary border';

  return (
    <section aria-label="Analyst review" className="space-y-2.5">
      <div className="flex items-center justify-between text-xs">
        <h4 className="font-semibold text-text-muted uppercase tracking-wider">Analyst review</h4>
        <span className="font-mono text-text-secondary">{state === 'UNREVIEWED' ? 'not reviewed yet' : pretty(state)}</span>
      </div>

      {history.length > 0 && (
        <ol className="space-y-1.5">
          {history.map(h => (
            <li key={h.id} className="text-[11px] bg-bg-main border border-border-subtle rounded p-2 text-text-secondary">
              <span className="font-mono text-text-primary">{h.decision.toLowerCase()}</span>{' '}
              <span className="text-text-muted">({pretty(h.previous_status)} → {pretty(h.new_status)})</span>
              {h.note && <p className="mt-0.5 italic break-words">“{h.note}”</p>}
            </li>
          ))}
        </ol>
      )}

      {canReview ? (
        <>
          <label className="block text-[11px] text-text-muted">
            Note (optional)
            <textarea
              value={note}
              onChange={e => setNote(e.target.value)}
              maxLength={1000}
              rows={2}
              placeholder="Why? Do not paste OTPs, passwords or card numbers."
              className="mt-1 w-full bg-bg-main border border-border-subtle rounded p-2 text-xs text-text-primary focus:outline-none focus:border-accent-primary"
            />
          </label>
          <div className="grid grid-cols-3 gap-2">
            <button type="button" disabled={busy} onClick={() => void submit('ACCEPT')}
                    className={`${btn} bg-accent-secondary/20 hover:bg-accent-secondary/30 text-accent-secondary border-accent-secondary/40`}>
              <CheckCircle className="w-3.5 h-3.5" aria-hidden="true" /> Accept
            </button>
            <button type="button" disabled={busy} onClick={() => void submit('FLAG')}
                    className={`${btn} bg-risk-elevated/20 hover:bg-risk-elevated/30 text-risk-elevated border-risk-elevated/40`}>
              <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" /> Flag
            </button>
            <button type="button" disabled={busy} onClick={() => void submit('REJECT')}
                    className={`${btn} bg-risk-critical/20 hover:bg-risk-critical/30 text-risk-critical border-risk-critical/40`}>
              <X className="w-3.5 h-3.5" aria-hidden="true" /> Reject
            </button>
          </div>
          <p className="text-[10px] text-text-muted">
            Accepting a {subject} records your decision; it does not turn a {subject} into a proven fact.
          </p>
        </>
      ) : (
        <p className="text-[11px] text-text-muted bg-bg-main border border-border-subtle rounded p-2">
          Reviews are saved by the live backend. The hosted demo shows precomputed data only, so review is unavailable here.
        </p>
      )}
      {error && <p role="alert" className="text-[11px] text-risk-critical">{error}</p>}
    </section>
  );
};
