import { describe, expect, it } from 'vitest';
import { basisLabel, confidencePct, linkSummary } from './campaign_view';
import type { CampaignLink } from '../../types';

const link = (over: Partial<CampaignLink>): CampaignLink => ({
  id: 1, incident_a_id: 1, incident_b_id: 2, status: 'OBSERVED_MATCH', match_type: 'EXACT_IDENTIFIER',
  similarity: null, adjusted_confidence: 0.75, explanation: 'x', is_weakest: false, ...over,
});

describe('campaign wording', () => {
  it('describes each basis without implying proof', () => {
    expect(basisLabel('OBSERVED')).toMatch(/observed identifier/i);
    expect(basisLabel('CANDIDATE')).toMatch(/behaviour only/i);
    expect(basisLabel('ANALYST')).toMatch(/analyst/i);
    for (const b of ['OBSERVED', 'CANDIDATE', 'ANALYST']) {
      expect(basisLabel(b)).not.toMatch(/confirmed|criminal|guilty|proven/i);
    }
  });

  it('summarises links by status and shows the similarity only when there is one', () => {
    expect(linkSummary(link({}))).toBe('observed match');
    expect(linkSummary(link({ match_type: 'COMBINED', similarity: 0.912 }))).toBe('observed match, behaviour also matches, similarity 91%');
    expect(linkSummary(link({ status: 'CANDIDATE_ASSOCIATION', match_type: 'PLAYBOOK', similarity: 0.833 }))).toBe('behaviour match, similarity 83%');
    expect(linkSummary(link({ status: 'DISPUTED_ASSOCIATION' }))).toBe('disputed');
    expect(linkSummary(link({ status: 'REJECTED_ASSOCIATION' }))).toBe('rejected by an analyst');
  });

  it('formats confidence as a rounded percentage', () => {
    expect(confidencePct(0.75)).toBe('75%');
    expect(confidencePct(0.8333)).toBe('83%');
  });
});
