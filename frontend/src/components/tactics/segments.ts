import type { InjectionSpan, TacticSpan } from '../../types';

/** Display order of tactic labels; the first label present on a segment decides its colour. */
export const LABEL_ORDER = [
  'AUTHORITY_IMPERSONATION', 'FALSE_ALLEGATION', 'THREAT_INTIMIDATION', 'ISOLATION', 'URGENCY',
  'FINANCIAL_DEMAND', 'CREDENTIAL_REQUEST', 'LEGITIMATE', 'OTHER_SUSPICIOUS',
] as const;

export const LABEL_COLORS: Record<string, string> = {
  AUTHORITY_IMPERSONATION: '#38BDF8',
  FALSE_ALLEGATION: '#A78BFA',
  THREAT_INTIMIDATION: '#EF4444',
  ISOLATION: '#F97316',
  URGENCY: '#EAB308',
  FINANCIAL_DEMAND: '#F472B6',
  CREDENTIAL_REQUEST: '#2DD4BF',
  LEGITIMATE: '#22C55E',
  OTHER_SUSPICIOUS: '#94A3B8',
};

export const LABEL_NAMES: Record<string, string> = {
  AUTHORITY_IMPERSONATION: 'Authority claim',
  FALSE_ALLEGATION: 'Allegation',
  THREAT_INTIMIDATION: 'Threat',
  ISOLATION: 'Isolation',
  URGENCY: 'Urgency',
  FINANCIAL_DEMAND: 'Payment demand',
  CREDENTIAL_REQUEST: 'Credential request',
  LEGITIMATE: 'Benign cue',
  OTHER_SUSPICIOUS: 'Other suspicious',
};

export interface Segment {
  text: string;
  labels: string[];        // tactic labels covering this segment, in LABEL_ORDER
  injection: string[];     // injection rule ids covering this segment
}

/**
 * Split `text` into segments at every span boundary so overlapping tactic and injection spans can be
 * rendered together. Spans are clamped to the text; empty or inverted spans are ignored.
 */
export function buildSegments(text: string, tactics: TacticSpan[], injection: InjectionSpan[] = []): Segment[] {
  if (!text) return [];
  const clamp = (n: number) => Math.max(0, Math.min(text.length, n));
  const t = tactics.map(s => ({ ...s, start: clamp(s.start), end: clamp(s.end) })).filter(s => s.end > s.start);
  const inj = injection.map(s => ({ ...s, start: clamp(s.start), end: clamp(s.end) })).filter(s => s.end > s.start);

  const cuts = new Set<number>([0, text.length]);
  for (const s of [...t, ...inj]) { cuts.add(s.start); cuts.add(s.end); }
  const points = [...cuts].sort((a, b) => a - b);

  const segments: Segment[] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const [from, to] = [points[i], points[i + 1]];
    const labels = LABEL_ORDER.filter(l => t.some(s => s.label === l && s.start <= from && s.end >= to));
    const rules = [...new Set(inj.filter(s => s.start <= from && s.end >= to).map(s => s.rule_id))];
    segments.push({ text: text.slice(from, to), labels: [...labels], injection: rules });
  }
  return segments;
}

/** Observed stage order -> display model for the six canonical stages plus the credential branch. */
export const CANONICAL_STAGES = ['AUTHORITY', 'ALLEGATION', 'THREAT', 'ISOLATION', 'URGENCY', 'DEMAND'] as const;

export interface StageChip {
  stage: string;
  observed: boolean;
  order: number | null;   // 1-based position in the order stages first appeared
}

export function stageChips(sequence: string[] | undefined): StageChip[] {
  const seq = Array.isArray(sequence) ? sequence : [];
  return CANONICAL_STAGES.map(stage => {
    const at = seq.indexOf(stage);
    return { stage, observed: at >= 0, order: at >= 0 ? at + 1 : null };
  });
}

/** True when the observed stages appear in the canonical order (a partial call is still "in order"). */
export function isCanonicalOrder(sequence: string[] | undefined): boolean {
  const idx = (sequence ?? []).map(s => (CANONICAL_STAGES as readonly string[]).indexOf(s)).filter(i => i >= 0);
  return idx.every((v, i) => i === 0 || idx[i - 1] < v);
}
