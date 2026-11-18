import type { RiskBand, SimulationFrame } from '../types';

export const SPEEDS = [
  { label: '0.5x', ms: 3200 },
  { label: '1x', ms: 1600 },
  { label: '2x', ms: 800 },
] as const;

/** Next turn to show, or null when the script is finished. */
export function nextStep(step: number, total: number): number | null {
  return step < total ? step + 1 : null;
}

/** Share of the gauge to fill (the risk score runs 0 to 100). */
export function gaugeFraction(score: number): number {
  return Math.min(1, Math.max(0, score / 100));
}

export const BAND_TEXT: Record<RiskBand, string> = {
  LOW: 'text-risk-low', ELEVATED: 'text-risk-elevated', HIGH: 'text-risk-high', CRITICAL: 'text-risk-critical',
};
export const BAND_BG: Record<RiskBand, string> = {
  LOW: 'bg-risk-low', ELEVATED: 'bg-risk-elevated', HIGH: 'bg-risk-high', CRITICAL: 'bg-risk-critical',
};

export function stagesReached(frame: SimulationFrame | null): string[] {
  return frame ? frame.stages.filter(s => s.reached).map(s => s.stage) : [];
}

/** Stages that appeared in the newest turn (so the tracker can highlight what just lit up). */
export function newlyReached(prev: SimulationFrame | null, next: SimulationFrame | null): string[] {
  const before = new Set(stagesReached(prev));
  return stagesReached(next).filter(s => !before.has(s));
}

/** The contributions that changed between two frames, largest first (the "live" list). */
export function contributionDelta(prev: SimulationFrame | null, next: SimulationFrame | null) {
  const key = (c: { factor: string; evidence_ref?: string }) => `${c.factor}|${c.evidence_ref ?? ''}`;
  const before = new Set((prev?.risk.contributions ?? []).map(key));
  return (next?.risk.contributions ?? []).filter(c => !before.has(key(c)))
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
}
