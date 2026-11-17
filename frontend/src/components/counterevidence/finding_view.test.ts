import { describe, expect, it } from 'vitest';
import {
  acceptedWithFindingsText, confidenceLine, disputeText, formatImpact, highestSeverity, impactTotal, sortFindings,
} from './finding_view';

const f = (rule_id: string, severity: 'LOW' | 'MEDIUM' | 'HIGH', confidence_impact: number) => ({ rule_id, severity, confidence_impact });

describe('counter-evidence presentation', () => {
  const list = [f('CE-7', 'LOW', -0.02), f('CE-3', 'HIGH', -0.4), f('CE-5', 'MEDIUM', -0.1), f('CE-1', 'HIGH', -0.3)];

  it('sorts worst first, then by rule id, without mutating the input', () => {
    expect(sortFindings(list).map(x => x.rule_id)).toEqual(['CE-1', 'CE-3', 'CE-5', 'CE-7']);
    expect(list[0].rule_id).toBe('CE-7');
  });

  it('reports the highest severity and the summed impact', () => {
    expect(highestSeverity(list)).toBe('HIGH');
    expect(highestSeverity([])).toBeNull();
    expect(impactTotal(list)).toBeCloseTo(-0.82);
  });

  it('formats impacts with a typographic minus and two decimals', () => {
    expect(formatImpact(-0.3)).toBe('−0.30');
    expect(formatImpact(0)).toBe('+0.00');
  });

  it('builds the confidence line from the stored adjusted value', () => {
    expect(confidenceLine(0.7, 0.2, [f('CE-3', 'HIGH', -0.4), f('CE-5', 'MEDIUM', -0.1)])).toBe('Base 70% → adjusted 20% (−0.50 from 2 findings)');
    expect(confidenceLine(0.75, 0.75, [])).toBe('Confidence 75% (no counter-evidence recorded)');
    expect(confidenceLine(0.7, 0.6, [f('CE-2', 'MEDIUM', -0.1)])).toContain('1 finding)');
  });

  it('explains a dispute by its source and says nothing for undisputed links', () => {
    expect(disputeText('OBSERVED_MATCH')).toBeNull();
    expect(disputeText('DISPUTED_ASSOCIATION', { source: 'RULE', rules: ['CE-3'] })).toMatch(/automatically.*CE-3/);
    expect(disputeText('DISPUTED_ASSOCIATION', { source: 'ANALYST', rules: [] })).toMatch(/analyst/);
  });

  it('keeps findings on record after an analyst accepts a link', () => {
    expect(acceptedWithFindingsText('ANALYST_VERIFIED_ASSOCIATION', list)).toMatch(/remain on record/);
    expect(acceptedWithFindingsText('ANALYST_VERIFIED_ASSOCIATION', [])).toBeNull();
    expect(acceptedWithFindingsText('OBSERVED_MATCH', list)).toBeNull();
  });
});
