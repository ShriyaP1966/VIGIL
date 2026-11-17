import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { SEVERITY_LABEL, formatImpact, severityTone, type Severity } from './finding_view';

interface FindingCardProps {
  ruleId: string;
  kind: string;
  severity: Severity;
  observation: string;
  explanation: string;
  impact: number;
  ruleVersion?: string;
  refs?: Array<{ evidence_id?: number; incident_id?: number; excerpt?: string; stage?: string; entity?: string }>;
  /** Optional context line, e.g. which link a campaign-level finding belongs to. */
  context?: React.ReactNode;
}

const humanKind = (k: string) => k.replace(/_/g, ' ').toLowerCase();

/** One counter-evidence finding: the contradictory observation, where it came from, how severe it is and
 *  what it did to the confidence. Evidence excerpts are untrusted text and are rendered as plain text. */
export const FindingCard: React.FC<FindingCardProps> = ({
  ruleId, kind, severity, observation, explanation, impact, ruleVersion, refs = [], context,
}) => (
  <li className={`border rounded p-2.5 text-xs space-y-1.5 ${severityTone(severity)}`}>
    <div className="flex items-center justify-between gap-2 font-mono text-[10px]">
      <span className="flex items-center gap-1 font-bold">
        <AlertTriangle className="w-3 h-3" aria-hidden="true" />
        {ruleId} · {humanKind(kind)}
      </span>
      <span className="uppercase">{SEVERITY_LABEL[severity]} severity</span>
    </div>
    {context && <div className="text-[10px] font-mono text-text-muted">{context}</div>}
    <p className="text-text-primary font-medium leading-snug">{observation}</p>
    <p className="text-text-secondary text-[11px] leading-snug">{explanation}</p>
    {refs.length > 0 && (
      <ul className="space-y-1" aria-label="Evidence for this finding">
        {refs.slice(0, 4).map((r, i) => (
          <li key={i} className="text-[11px] text-text-secondary bg-bg-main/60 border border-border-subtle/60 rounded px-2 py-1 break-words">
            <span className="font-mono text-[10px] text-text-muted">
              {r.incident_id != null ? `INC-${String(r.incident_id).padStart(4, '0')}` : 'evidence'}
              {r.stage ? ` · ${r.stage}` : ''}{r.evidence_id != null ? ` · #${r.evidence_id}` : ''}
            </span>
            {(r.excerpt || r.entity) && <> “{r.excerpt || r.entity}”</>}
          </li>
        ))}
      </ul>
    )}
    <div className="flex justify-between font-mono text-[10px] text-text-muted">
      <span>{ruleVersion ?? ''}</span>
      <span>confidence impact {formatImpact(impact)}</span>
    </div>
  </li>
);
