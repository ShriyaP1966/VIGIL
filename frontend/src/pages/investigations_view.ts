import type { IncidentListItem, RiskBand } from '../types';

export type BandFilter = RiskBand | 'ALL';
export type SortKey = 'newest' | 'risk';

export interface IncidentFilter {
  q: string;
  band: BandFilter;
  channel: string;          // 'ALL' or a source channel
  sort: SortKey;
}

export const DEFAULT_FILTER: IncidentFilter = { q: '', band: 'ALL', channel: 'ALL', sort: 'newest' };
export const BANDS: RiskBand[] = ['LOW', 'ELEVATED', 'HIGH', 'CRITICAL'];

export const incidentCode = (id: number): string => `INC-${id.toString().padStart(4, '0')}`;

const bandOf = (i: IncidentListItem): RiskBand => i.risk_band ?? 'LOW';

/** Search matches every word against the case code, numeric id, title, channel, language, status and band. */
export function filterIncidents(items: IncidentListItem[], f: IncidentFilter): IncidentListItem[] {
  const words = f.q.toLowerCase().split(/\s+/).filter(Boolean);
  const out = items.filter(i => {
    if (f.band !== 'ALL' && bandOf(i) !== f.band) return false;
    if (f.channel !== 'ALL' && i.source_channel !== f.channel) return false;
    if (!words.length) return true;
    const haystack = [incidentCode(i.id), String(i.id), i.title, i.source_channel, i.language, i.status, bandOf(i)]
      .join(' ').toLowerCase();
    return words.every(w => haystack.includes(w));
  });
  const newest = (a: IncidentListItem, b: IncidentListItem) =>
    b.created_at.localeCompare(a.created_at) || b.id - a.id;
  return out.sort(f.sort === 'risk'
    ? (a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0) || newest(a, b)
    : newest);
}

export function bandCounts(items: IncidentListItem[]): Record<RiskBand, number> {
  const counts: Record<RiskBand, number> = { LOW: 0, ELEVATED: 0, HIGH: 0, CRITICAL: 0 };
  for (const i of items) counts[bandOf(i)] += 1;
  return counts;
}

export const isFiltered = (f: IncidentFilter): boolean =>
  f.q.trim() !== '' || f.band !== 'ALL' || f.channel !== 'ALL';
