import React, { useCallback, useEffect, useRef, useState } from 'react';
import { FlaskConical, Play, RotateCcw } from 'lucide-react';
import { apiClient, ApiMode } from '../services/api/client';
import type { ScenarioInfo, ScenarioRun } from '../types';
import { snapRotation } from '../services/api/static_adapter';
import { EmptyState, ErrorBanner, Skeleton } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import {
  CATEGORY_LABEL, checkTone, expectationSummary, formatActual, groupByCategory, sameResult,
} from './scenario_view';
import { BAND_TEXT } from './simulation_view';

const focusRing = 'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary';
const TONE: Record<string, string> = {
  pass: 'border-risk-low/50 text-risk-low', fail: 'border-risk-critical/60 text-risk-critical',
  info: 'border-border-subtle text-text-muted',
};
const STATUS_TONE: Record<string, string> = {
  OBSERVED_MATCH: 'text-accent-primary', CANDIDATE_ASSOCIATION: 'text-risk-elevated',
  DISPUTED_ASSOCIATION: 'text-risk-critical',
};

export const ScenarioLab: React.FC<{ apiMode: ApiMode }> = ({ apiMode }) => {
  const toast = useToast();
  const live = apiMode === 'live';
  const [scenarios, setScenarios] = useState<ScenarioInfo[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [rotation, setRotation] = useState(0.5);
  const [run, setRun] = useState<ScenarioRun | null>(null);
  const [replayed, setReplayed] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const request = useRef(0);

  const loadList = useCallback(async () => {
    setError(null);
    try {
      const list = await apiClient.listScenarios();
      setScenarios(list);
      setSelected(prev => prev ?? list[0]?.name ?? null);
    } catch (e: any) {
      setError(e?.message || 'Failed to load the scenarios.');
    }
  }, []);
  useEffect(() => { void loadList(); }, [loadList]);

  const info = scenarios?.find(s => s.name === selected) ?? null;
  const step = live ? 0.05 : 0.25;
  const shownRotation = info?.rotation_adjustable ? (live ? rotation : snapRotation(rotation)) : null;

  const execute = useCallback(async (replay: boolean) => {
    if (!selected || !info) return;
    const id = ++request.current;
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.runScenario(selected, info.rotation_adjustable ? shownRotation : null);
      if (id !== request.current) return;           // a newer request superseded this one
      if (replay) {
        setReplayed(sameResult(run, result));
        toast.success(sameResult(run, result) ? 'Replay is identical to the previous run.' : 'Replay differs from the previous run.');
      } else {
        setReplayed(null);
      }
      setRun(result);
    } catch (e: any) {
      if (id === request.current) setError(e?.message || 'The scenario could not be run.');
    } finally {
      if (id === request.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, info, shownRotation, run, toast]);

  // Run when the scenario or the rotation changes (slider commits are debounced).
  useEffect(() => {
    if (!selected || !info) return;
    const timer = setTimeout(() => { void execute(false); }, info.rotation_adjustable ? 250 : 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, shownRotation, info?.name]);

  const select = (name: string) => { setSelected(name); setRun(null); setReplayed(null); };

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">Scenario Lab</h1>
        <p className="text-sm text-text-secondary mt-1">
          Deterministic synthetic scenarios replayed through the real pipeline. Change the identifier-rotation level, run it again, and compare the outcome with what the scenario expects.
        </p>
      </div>

      {!live && (
        <div className="rounded-lg border border-border-subtle bg-bg-elevated/40 p-3 text-xs text-text-secondary">
          Hosted demo: results are precomputed at five rotation levels (0, 0.25, 0.5, 0.75, 1). The slider snaps to them. Run the app locally for any level from 0 to 1.
        </div>
      )}

      {error && <ErrorBanner message={error} onRetry={scenarios ? () => void execute(false) : loadList} />}

      {scenarios === null && !error ? <Skeleton rows={4} label="Loading scenarios" /> : scenarios && scenarios.length === 0 ? (
        <EmptyState title="No scenarios available" />
      ) : scenarios && (
        <div className="grid lg:grid-cols-[18rem_1fr] gap-6">
          <nav aria-label="Scenarios" className="space-y-4">
            {groupByCategory(scenarios).map(g => (
              <div key={g.category}>
                <h2 className="text-[11px] uppercase tracking-wider text-text-muted mb-1">{CATEGORY_LABEL[g.category]}</h2>
                <ul className="space-y-1">
                  {g.items.map(s => (
                    <li key={s.name}>
                      <button
                        type="button"
                        onClick={() => select(s.name)}
                        aria-current={s.name === selected ? 'true' : undefined}
                        className={`w-full text-left px-3 py-2 rounded-md border text-sm transition-colors ${focusRing} ${
                          s.name === selected ? 'border-accent-primary bg-accent-primary/10 text-text-primary'
                                              : 'border-border-subtle text-text-secondary hover:text-text-primary hover:bg-bg-card'}`}
                      >
                        {s.title}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>

          <div className="space-y-4 min-w-0">
            {info && (
              <div className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-4">
                <div>
                  <h2 className="text-base font-semibold text-text-primary flex items-center gap-2">
                    <FlaskConical className="w-4 h-4 text-accent-secondary" aria-hidden="true" />{info.title}
                  </h2>
                  <p className="text-xs text-text-secondary mt-1">{info.description}</p>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-end gap-4">
                  <div className="flex-1">
                    <label htmlFor="rotation" className="text-xs text-text-secondary flex justify-between">
                      <span>Identifier rotation</span>
                      <span className="font-mono text-text-primary" aria-live="polite">
                        {shownRotation == null ? 'not used by this scenario' : shownRotation.toFixed(2)}
                      </span>
                    </label>
                    <input
                      id="rotation" type="range" min={0} max={1} step={step}
                      value={shownRotation ?? 0.5}
                      disabled={!info.rotation_adjustable}
                      onChange={e => setRotation(Number(e.target.value))}
                      aria-valuetext={shownRotation == null ? 'not used' : `${Math.round(shownRotation * 100)} percent of identifiers replaced`}
                      className={`w-full accent-sky-400 disabled:opacity-40 ${focusRing}`}
                    />
                    <div className="flex justify-between text-[10px] text-text-muted"><span>0 never replaced</span><span>1 always replaced</span></div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button" onClick={() => void execute(false)} disabled={loading}
                      className={`inline-flex items-center gap-2 bg-accent-primary hover:bg-sky-400 text-bg-main font-semibold px-4 py-2 rounded-md text-sm disabled:opacity-50 ${focusRing}`}
                    >
                      <Play className="w-4 h-4" aria-hidden="true" />{loading ? 'Running…' : 'Run'}
                    </button>
                    <button
                      type="button" onClick={() => void execute(true)} disabled={loading || !run}
                      className={`inline-flex items-center gap-2 border border-accent-primary text-accent-primary hover:bg-accent-primary/10 font-semibold px-4 py-2 rounded-md text-sm disabled:opacity-50 ${focusRing}`}
                    >
                      <RotateCcw className="w-4 h-4" aria-hidden="true" />Replay
                    </button>
                  </div>
                </div>
                {replayed !== null && (
                  <p role="status" className="text-xs text-text-secondary">
                    Replay {replayed ? 'is identical to the previous run (the scenario is deterministic).' : 'differs from the previous run.'}
                  </p>
                )}
              </div>
            )}

            {loading && !run ? <Skeleton rows={3} label="Running the scenario" /> : run && (
              <div className="space-y-4" aria-busy={loading}>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {([
                    ['Observed links', run.summary.observed_links], ['Candidate links', run.summary.candidate_links],
                    ['Disputed links', run.summary.disputed_links], ['Hypotheses', run.summary.hypotheses],
                  ] as const).map(([label, n]) => (
                    <div key={label} className="bg-bg-card border border-border-subtle rounded-lg p-3">
                      <div className="text-[11px] text-text-muted">{label}</div>
                      <div className="text-xl font-mono font-bold text-text-primary">{n}</div>
                    </div>
                  ))}
                </div>

                <section aria-labelledby="sc-checks" className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-2">
                  <h3 id="sc-checks" className="text-sm font-semibold text-text-primary">Expected and actual</h3>
                  <p className="text-xs text-text-secondary">{expectationSummary(run)} A difference is shown as it is; the scenarios are not tuned to pass.</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <caption className="sr-only">Expected versus actual outcome</caption>
                      <thead className="text-text-muted uppercase text-[10px]">
                        <tr><th scope="col" className="py-2 pr-3">Check</th><th scope="col" className="py-2 pr-3">Expected</th><th scope="col" className="py-2 pr-3">Actual</th><th scope="col" className="py-2">Result</th></tr>
                      </thead>
                      <tbody className="divide-y divide-border-subtle">
                        {run.checks.map((c, i) => {
                          const t = checkTone(c);
                          return (
                            <tr key={i} className="align-top">
                              <td className="py-2 pr-3 text-text-primary">{c.name}</td>
                              <td className="py-2 pr-3 text-text-secondary">{c.expected}</td>
                              <td className="py-2 pr-3 text-text-secondary font-mono break-all">{formatActual(c.actual)}</td>
                              <td className="py-2"><span className={`inline-block border rounded px-1.5 py-0.5 font-semibold ${TONE[t.tone]}`}>{t.label}</span></td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </section>

                <section aria-labelledby="sc-links" className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-2">
                  <h3 id="sc-links" className="text-sm font-semibold text-text-primary">Links and hypotheses</h3>
                  {run.links.length === 0 ? <p className="text-xs text-text-muted">No link between these incidents.</p> : (
                    <ul className="text-xs space-y-1">
                      {run.links.map((l, i) => (
                        <li key={i} className="text-text-secondary break-words">
                          <span className="font-mono">{l.a}</span> ↔ <span className="font-mono">{l.b}</span>{' '}
                          <span className={`font-semibold ${STATUS_TONE[l.status] ?? 'text-text-muted'}`}>{l.status.replace(/_/g, ' ').toLowerCase()}</span>
                          {' '}({l.match_type.toLowerCase().replace('_', ' ')}, confidence {l.confidence}){l.shared.length ? `, shared ${l.shared.join(', ')}` : ''}
                        </li>
                      ))}
                    </ul>
                  )}
                  {run.hypotheses.map((h, i) => (
                    <p key={i} className="text-xs text-text-secondary">
                      Hypothesis (unreviewed, not an established finding): {h.members.join(', ')}; confidence {h.confidence.toFixed(2)}.
                    </p>
                  ))}
                </section>

                <section aria-labelledby="sc-inc" className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-2">
                  <h3 id="sc-inc" className="text-sm font-semibold text-text-primary">Incidents in this scenario</h3>
                  <ul className="space-y-2">
                    {run.incidents.map(i => (
                      <li key={i.id} className="text-xs border border-border-subtle rounded-md p-3 bg-bg-main space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-text-muted">{i.id}</span>
                          <span className="uppercase font-mono text-[10px] text-text-secondary">{i.channel} · {i.language}</span>
                          {i.risk && <span className={`font-mono font-bold ${BAND_TEXT[i.risk.band]}`}>risk {i.risk.score} {i.risk.band}</span>}
                          {i.injection_flags.length > 0 && <span className="text-risk-critical font-semibold">manipulation attempt flagged</span>}
                        </div>
                        <p className="text-text-secondary break-words">{i.excerpt}{i.excerpt.length >= 200 ? '…' : ''}</p>
                        <p className="text-text-muted">Detected: {i.detected_labels.length ? i.detected_labels.join(', ') : 'no tactic'}</p>
                      </li>
                    ))}
                  </ul>
                  <p className="text-[11px] text-text-muted">{run.disclaimer}</p>
                </section>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
