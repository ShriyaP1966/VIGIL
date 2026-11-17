import type { CampaignLink, CampaignStatus } from '../../types';

/** Plain-language wording for a hypothesis member's basis. Never implies proof. */
export function basisLabel(basis: string): string {
  switch (basis) {
    case 'OBSERVED': return 'Shares an observed identifier';
    case 'ANALYST': return 'Linked by an analyst-verified link';
    case 'CANDIDATE': return 'Behaviour only (no shared identifier)';
    default: return basis;
  }
}

export function basisTone(basis: string): string {
  switch (basis) {
    case 'OBSERVED': return 'border-accent-primary/40 text-accent-primary bg-accent-primary/10';
    case 'ANALYST': return 'border-accent-secondary/40 text-accent-secondary bg-accent-secondary/10';
    default: return 'border-risk-elevated/40 text-risk-elevated bg-risk-elevated/10';
  }
}

export function statusTone(status: CampaignStatus): string {
  switch (status) {
    case 'ACCEPTED_BY_ANALYST': return 'border-accent-secondary/40 text-accent-secondary';
    case 'REJECTED_BY_ANALYST': return 'border-border-subtle text-text-muted';
    case 'FLAGGED': return 'border-risk-elevated/40 text-risk-elevated';
    default: return 'border-accent-primary/40 text-accent-primary';
  }
}

export const confidencePct = (c: number): string => `${Math.round(c * 100)}%`;

/** One-line description of a connecting link, e.g. "observed match" or "behaviour match, similarity 83%". */
export function linkSummary(link: CampaignLink): string {
  const sim = link.similarity != null ? `, similarity ${Math.round(link.similarity * 100)}%` : '';
  switch (link.status) {
    case 'OBSERVED_MATCH':
      return link.match_type === 'COMBINED' ? `observed match, behaviour also matches${sim}` : 'observed match';
    case 'ANALYST_VERIFIED_ASSOCIATION': return `verified by an analyst${sim}`;
    case 'CANDIDATE_ASSOCIATION': return `behaviour match${sim}`;
    case 'DISPUTED_ASSOCIATION': return `disputed${sim}`;
    case 'REJECTED_ASSOCIATION': return 'rejected by an analyst';
    default: return String(link.status).toLowerCase();
  }
}
