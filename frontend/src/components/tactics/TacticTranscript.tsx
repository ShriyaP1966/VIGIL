import React from 'react';
import type { UtteranceView } from '../../types';
import { buildSegments, LABEL_COLORS, LABEL_NAMES, LABEL_ORDER } from './segments';

interface TacticTranscriptProps {
  utterances: UtteranceView[];
}

/** Transcript with the exact phrases that triggered each tactic highlighted. Evidence is untrusted text:
 *  it is rendered only as React text nodes, never as HTML. */
export const TacticTranscript: React.FC<TacticTranscriptProps> = ({ utterances }) => {
  const present = LABEL_ORDER.filter(l => utterances.some(u => u.tactics.some(t => t.label === l)));
  const hasInjection = utterances.some(u => u.injection_spans.length > 0);

  return (
    <div className="space-y-3">
      <div className="space-y-2" role="list" aria-label="Transcript">
        {utterances.map(u => {
          const segments = buildSegments(u.text, u.tactics, u.injection_spans);
          const labels = LABEL_ORDER.filter(l => u.tactics.some(t => t.label === l));
          return (
            <div key={u.id} role="listitem" className="bg-bg-main border border-border-subtle rounded-md p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-mono uppercase text-text-muted">
                  {u.speaker}{u.t_start_sec != null ? ` · ${u.t_start_sec}s` : ''}
                </span>
                {labels.length > 0 && (
                  <span className="flex flex-wrap gap-1 justify-end">
                    {labels.map(l => (
                      <span key={l} className="text-[10px] px-1.5 py-0.5 rounded border"
                            style={{ borderColor: LABEL_COLORS[l], color: LABEL_COLORS[l] }}>
                        {LABEL_NAMES[l] ?? l}
                      </span>
                    ))}
                  </span>
                )}
              </div>
              <p className="text-sm text-text-secondary font-mono leading-relaxed whitespace-pre-wrap break-words">
                {segments.map((seg, i) => {
                  if (seg.labels.length === 0 && seg.injection.length === 0) return <span key={i}>{seg.text}</span>;
                  const color = seg.labels.length ? LABEL_COLORS[seg.labels[0]] : '#EF4444';
                  const title = [
                    seg.labels.map(l => LABEL_NAMES[l] ?? l).join(', '),
                    seg.injection.length ? `Manipulation attempt (${seg.injection.join(', ')}): ignored for scoring` : '',
                  ].filter(Boolean).join(' · ');
                  return (
                    <mark
                      key={i}
                      title={title}
                      className="rounded px-0.5 text-text-primary"
                      style={{
                        backgroundColor: `${color}33`,
                        boxShadow: `inset 0 -2px 0 ${color}`,
                        outline: seg.injection.length ? '1px dashed #EF4444' : undefined,
                      }}
                    >
                      {seg.text}
                    </mark>
                  );
                })}
              </p>
            </div>
          );
        })}
      </div>

      {(present.length > 0 || hasInjection) && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-text-muted" aria-label="Legend">
          {present.map(l => (
            <span key={l} className="flex items-center gap-1.5">
              <span className="w-3 h-1.5 rounded-sm" style={{ backgroundColor: LABEL_COLORS[l] }} aria-hidden="true" />
              {LABEL_NAMES[l] ?? l}
            </span>
          ))}
          {hasInjection && (
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-sm border border-dashed border-risk-critical" aria-hidden="true" />
              Manipulation attempt
            </span>
          )}
        </div>
      )}
    </div>
  );
};
