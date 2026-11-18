import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus, Search } from 'lucide-react';
import { apiClient } from '../services/api/client';
import type { IncidentListItem, RiskBand } from '../types';
import { Link } from '../router';
import { pathFor } from '../router/routes';
import { EmptyState, ErrorBanner, Skeleton } from '../components/ui/States';
import {
  BANDS, DEFAULT_FILTER, IncidentFilter, SortKey, bandCounts, filterIncidents, incidentCode, isFiltered,
} from './investigations_view';
import { BAND_TEXT } from './simulation_view';

const focusRing = 'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary';

export const Investigations: React.FC = () => {
  const [items, setItems] = useState<IncidentListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<IncidentFilter>(DEFAULT_FILTER);

  const load = useCallback(async () => {
    setError(null);
    setItems(null);
    try {
      setItems(await apiClient.listIncidents());
    } catch (e: any) {
      setError(e?.message || 'Failed to load investigations.');
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const shown = useMemo(() => (items ? filterIncidents(items, filter) : []), [items, filter]);
  const counts = useMemo(() => bandCounts(items ?? []), [items]);
  const channels = useMemo(() => [...new Set((items ?? []).map(i => i.source_channel))].sort(), [items]);
  const set = (patch: Partial<IncidentFilter>) => setFilter(f => ({ ...f, ...patch }));

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">Investigations</h1>
          <p className="text-sm text-text-secondary mt-1">
            Every evidence record in this workspace. Search, filter by risk indicator or channel, and open a case.
          </p>
        </div>
        <Link
          to={pathFor('new_investigation')}
          className={`inline-flex items-center gap-2 self-start bg-accent-primary hover:bg-sky-400 text-bg-main font-semibold px-4 py-2 rounded-md text-sm transition-colors ${focusRing}`}
        >
          <Plus className="w-4 h-4" aria-hidden="true" />
          <span>New Investigation</span>
        </Link>
      </div>

      <div className="bg-bg-card border border-border-subtle rounded-lg p-4 space-y-4">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
            <input
              type="search"
              value={filter.q}
              onChange={e => set({ q: e.target.value })}
              aria-label="Search investigations"
              placeholder="Search by case code, title, channel, language or status"
              className={`w-full bg-bg-main border border-border-subtle rounded-md pl-9 pr-3 py-2 text-sm text-text-primary placeholder:text-text-muted ${focusRing}`}
            />
          </div>
          <label className="flex items-center gap-2 text-xs text-text-secondary">
            Channel
            <select
              value={filter.channel}
              onChange={e => set({ channel: e.target.value })}
              className={`bg-bg-main border border-border-subtle rounded-md px-2 py-2 text-sm text-text-primary ${focusRing}`}
            >
              <option value="ALL">All</option>
              {channels.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2 text-xs text-text-secondary">
            Sort
            <select
              value={filter.sort}
              onChange={e => set({ sort: e.target.value as SortKey })}
              className={`bg-bg-main border border-border-subtle rounded-md px-2 py-2 text-sm text-text-primary ${focusRing}`}
            >
              <option value="newest">Newest first</option>
              <option value="risk">Highest risk first</option>
            </select>
          </label>
        </div>

        <div role="group" aria-label="Filter by risk indicator" className="flex flex-wrap gap-2">
          {(['ALL', ...BANDS] as Array<RiskBand | 'ALL'>).map(b => {
            const active = filter.band === b;
            const n = b === 'ALL' ? (items?.length ?? 0) : counts[b];
            return (
              <button
                key={b}
                type="button"
                aria-pressed={active}
                onClick={() => set({ band: b })}
                className={`px-3 py-1.5 rounded-full border text-xs font-medium transition-colors ${focusRing} ${
                  active ? 'border-accent-primary bg-accent-primary/15 text-text-primary'
                         : 'border-border-subtle text-text-secondary hover:text-text-primary'
                }`}
              >
                {b === 'ALL' ? 'All risk levels' : b} <span className="font-mono text-text-secondary">({n})</span>
              </button>
            );
          })}
        </div>
        <p className="text-[11px] text-text-muted">
          The risk indicator is an experimental heuristic, not a probability.
        </p>
      </div>

      {error ? (
        <ErrorBanner message={error} onRetry={load} />
      ) : items === null ? (
        <Skeleton rows={5} label="Loading investigations" />
      ) : items.length === 0 ? (
        <EmptyState
          title="No investigations yet"
          action={<Link to={pathFor('new_investigation')} className={`text-accent-primary underline text-sm ${focusRing}`}>Paste your first synthetic transcript</Link>}
        >
          Nothing has been analysed in this workspace. Evidence you paste is analysed on the live backend; the hosted demo shows precomputed synthetic cases only.
        </EmptyState>
      ) : shown.length === 0 ? (
        <EmptyState
          title="No investigation matches"
          action={isFiltered(filter) ? (
            <button type="button" onClick={() => setFilter(DEFAULT_FILTER)} className={`text-accent-primary underline text-sm rounded ${focusRing}`}>
              Clear filters
            </button>
          ) : undefined}
        >
          Try a different search word or risk level.
        </EmptyState>
      ) : (
        <>
          <p className="text-xs text-text-muted" role="status" aria-live="polite">
            Showing {shown.length} of {items.length} investigation{items.length === 1 ? '' : 's'}.
          </p>
          <ul className="bg-bg-card border border-border-subtle rounded-lg divide-y divide-border-subtle" aria-label="Investigations">
            {shown.map(inc => {
              const band = inc.risk_band ?? 'LOW';
              return (
                <li key={inc.id}>
                  <Link
                    to={pathFor('investigation_detail', inc.id)}
                    className={`px-4 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-3 hover:bg-bg-elevated/40 transition-colors ${focusRing}`}
                  >
                    <div className="space-y-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs text-text-muted">{incidentCode(inc.id)}</span>
                        <span className="font-semibold text-sm text-text-primary break-words">{inc.title}</span>
                        <span className="text-[10px] font-mono uppercase bg-bg-elevated px-2 py-0.5 rounded text-text-secondary border border-border-subtle">{inc.source_channel}</span>
                        <span className="text-[10px] font-mono uppercase bg-bg-elevated px-2 py-0.5 rounded text-text-muted">{inc.language}</span>
                      </div>
                      <div className="text-xs text-text-muted">
                        Ingested {new Date(inc.created_at).toLocaleDateString()} · status {inc.status}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-xs font-mono font-bold ${BAND_TEXT[band]}`}>Risk {inc.risk_score ?? 0}</div>
                      <div className="text-[10px] text-text-muted uppercase font-mono">{band}</div>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
};
