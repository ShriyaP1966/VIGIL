import type { ScenarioCheck, ScenarioInfo, ScenarioRun } from '../types';

export const CATEGORY_LABEL: Record<ScenarioInfo['category'], string> = {
  positive: 'Campaign',
  negative: 'Legitimate',
  ambiguous: 'Ambiguous',
  decoy: 'Decoy',
  counter_evidence: 'Counter-evidence',
  injection: 'Injection',
};

export const CATEGORY_ORDER: ScenarioInfo['category'][] =
  ['positive', 'negative', 'ambiguous', 'decoy', 'counter_evidence', 'injection'];

export type CheckTone = 'pass' | 'fail' | 'info';

/** Pass and fail are both shown in words (colour is never the only cue); null is informational. */
export function checkTone(check: ScenarioCheck): { tone: CheckTone; label: string } {
  if (check.passed === true) return { tone: 'pass', label: 'Pass' };
  if (check.passed === false) return { tone: 'fail', label: 'Differs' };
  return { tone: 'info', label: 'Info' };
}

export function formatActual(value: unknown): string {
  if (value === null || value === undefined) return 'none';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

/** A replay is "identical" when the whole result matches the previous one (the server is deterministic). */
export function sameResult(a: ScenarioRun | null, b: ScenarioRun | null): boolean {
  return a !== null && b !== null && JSON.stringify(a) === JSON.stringify(b);
}

export function groupByCategory(items: ScenarioInfo[]): Array<{ category: ScenarioInfo['category']; items: ScenarioInfo[] }> {
  return CATEGORY_ORDER
    .map(category => ({ category, items: items.filter(i => i.category === category) }))
    .filter(g => g.items.length > 0);
}

export function expectationSummary(run: ScenarioRun): string {
  const required = run.checks.filter(c => c.passed !== null);
  const failed = required.filter(c => c.passed === false).length;
  return failed === 0
    ? `All ${required.length} expectations hold.`
    : `${failed} of ${required.length} expectations differ from what the scenario expects.`;
}
