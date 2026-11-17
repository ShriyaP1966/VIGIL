/** Presentation helpers for counter-evidence findings (blueprint §6.10). Pure, so they can be unit-tested. */

export type Severity = 'LOW' | 'MEDIUM' | 'HIGH';

export interface FindingLike {
  rule_id: string;
  severity: Severity;
  confidence_impact: number;
}

const RANK: Record<string, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };

export const SEVERITY_LABEL: Record<Severity, string> = { HIGH: 'High', MEDIUM: 'Medium', LOW: 'Low' };

export function severityTone(severity: string): string {
  switch (severity) {
    case 'HIGH': return 'bg-risk-critical/10 border-risk-critical/40 text-risk-critical';
    case 'MEDIUM': return 'bg-risk-elevated/10 border-risk-elevated/40 text-risk-elevated';
    default: return 'bg-bg-main border-border-subtle text-text-secondary';
  }
}

/** Worst first, then by rule id, without mutating the input. */
export function sortFindings<T extends FindingLike>(findings: T[]): T[] {
  return [...findings].sort((a, b) => (RANK[a.severity] ?? 9) - (RANK[b.severity] ?? 9) || a.rule_id.localeCompare(b.rule_id));
}

export function highestSeverity(findings: FindingLike[]): Severity | null {
  return sortFindings(findings)[0]?.severity ?? null;
}

export const impactTotal = (findings: FindingLike[]): number =>
  findings.reduce((sum, f) => sum + f.confidence_impact, 0);

/** "−0.30" / "+0.00": a typographic minus, two decimals. */
export function formatImpact(n: number): string {
  const sign = n < 0 ? '−' : '+';
  return `${sign}${Math.abs(n).toFixed(2)}`;
}

const pct = (x: number) => `${Math.round(x * 100)}%`;

/** "Base 70% → adjusted 20% (−0.50 from 2 findings)". The adjusted value is the stored one, never recomputed here. */
export function confidenceLine(base: number, adjusted: number, findings: FindingLike[]): string {
  if (findings.length === 0) return `Confidence ${pct(adjusted)} (no counter-evidence recorded)`;
  const n = findings.length;
  return `Base ${pct(base)} → adjusted ${pct(adjusted)} (${formatImpact(impactTotal(findings))} from ${n} finding${n === 1 ? '' : 's'})`;
}

/** Why a link is disputed, in plain language; null when it is not disputed. */
export function disputeText(
  status: string,
  dispute?: { source?: 'RULE' | 'ANALYST' | null; rules?: string[] },
): string | null {
  if (status !== 'DISPUTED_ASSOCIATION') return null;
  if (dispute?.source === 'ANALYST') return 'Flagged as disputed by an analyst.';
  const rules = dispute?.rules?.length ? ` (${dispute.rules.join(', ')})` : '';
  return `Disputed automatically: a high-severity counter-evidence finding${rules} contradicts this link.`;
}

/** Words shown when an analyst has accepted a link that still has findings: they stay on record. */
export function acceptedWithFindingsText(status: string, findings: FindingLike[]): string | null {
  if (status !== 'ANALYST_VERIFIED_ASSOCIATION' || findings.length === 0) return null;
  return `Accepted by an analyst. The ${findings.length} counter-evidence finding${findings.length === 1 ? '' : 's'} below remain on record.`;
}
