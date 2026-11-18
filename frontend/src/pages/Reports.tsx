import React, { useCallback, useEffect, useState } from 'react';
import { Download, FileJson, FileSpreadsheet } from 'lucide-react';
import { apiClient } from '../services/api/client';
import type { IncidentListItem, IncidentReport } from '../types';
import { EmptyState, ErrorBanner, Skeleton } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import { downloadText, reportFileName } from '../lib/download';
import { incidentCode } from './investigations_view';
import { LABEL_NAMES } from '../components/tactics/segments';

const focusRing = 'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary';

const Section: React.FC<{ id: string; title: string; hint: string; children: React.ReactNode }> = (
  { id, title, hint, children },
) => (
  <section aria-labelledby={id} className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-3">
    <div>
      <h2 id={id} className="text-sm font-semibold text-text-primary">{title}</h2>
      <p className="text-[11px] text-text-muted">{hint}</p>
    </div>
    {children}
  </section>
);

const Empty: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="text-xs text-text-muted">{children}</p>
);

export const Reports: React.FC = () => {
  const toast = useToast();
  const [incidents, setIncidents] = useState<IncidentListItem[] | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [report, setReport] = useState<IncidentReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<'json' | 'csv' | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const loadList = useCallback(async () => {
    setError(null);
    try {
      const list = await apiClient.listIncidents();
      setIncidents(list);
      setSelected(prev => prev ?? list[0]?.id ?? null);
    } catch (e: any) {
      setError(e?.message || 'Failed to load incidents.');
    }
  }, []);
  useEffect(() => { void loadList(); }, [loadList]);

  useEffect(() => {
    if (selected == null) { setReport(null); return; }
    let cancelled = false;
    setReport(null);
    setError(null);
    apiClient.getReport(selected)
      .then(r => { if (!cancelled) setReport(r); })
      .catch((e: any) => { if (!cancelled) setError(e?.message || 'Failed to build the report.'); });
    return () => { cancelled = true; };
  }, [selected, reloadKey]);

  const download = async (format: 'json' | 'csv') => {
    if (selected == null) return;
    setBusy(format);
    try {
      if (format === 'json') {
        const fresh = report ?? await apiClient.getReport(selected);
        downloadText(reportFileName(selected, 'json'), 'application/json', JSON.stringify(fresh, null, 2) + '\n');
      } else {
        downloadText(reportFileName(selected, 'csv'), 'text/csv', await apiClient.getReportCsv(selected));
      }
      toast.success(`Saved ${reportFileName(selected, format)}`);
    } catch (e: any) {
      toast.error(e?.message || 'The report could not be saved.');
    } finally {
      setBusy(null);
    }
  };

  const r = report;
  return (
    <div className="p-4 sm:p-8 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">Investigation Reports</h1>
        <p className="text-sm text-text-secondary mt-1">
          One report per case, with observed facts, model inferences, analyst decisions and counter-evidence kept in separate sections, plus the limits that apply.
        </p>
      </div>

      {error && <ErrorBanner message={error} onRetry={selected == null ? loadList : () => setReloadKey(k => k + 1)} />}

      {incidents === null && !error ? (
        <Skeleton rows={3} label="Loading reports" />
      ) : incidents && incidents.length === 0 ? (
        <EmptyState title="No cases to report on">Analyse some synthetic evidence first, then come back to export a report.</EmptyState>
      ) : incidents && (
        <>
          <div className="bg-bg-card border border-border-subtle rounded-lg p-4 flex flex-col md:flex-row md:items-end gap-4">
            <label className="flex-1 text-xs text-text-secondary space-y-1 block">
              <span>Case</span>
              <select
                value={selected ?? ''}
                onChange={e => setSelected(Number(e.target.value))}
                className={`w-full bg-bg-main border border-border-subtle rounded-md px-3 py-2 text-sm text-text-primary ${focusRing}`}
              >
                {incidents.map(i => <option key={i.id} value={i.id}>{incidentCode(i.id)} · {i.title}</option>)}
              </select>
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button" onClick={() => download('json')} disabled={selected == null || busy !== null}
                className={`inline-flex items-center gap-2 bg-accent-primary hover:bg-sky-400 text-bg-main font-semibold px-4 py-2 rounded-md text-sm transition-colors disabled:opacity-50 ${focusRing}`}
              >
                <FileJson className="w-4 h-4" aria-hidden="true" />{busy === 'json' ? 'Saving…' : 'Download JSON'}
              </button>
              <button
                type="button" onClick={() => download('csv')} disabled={selected == null || busy !== null}
                className={`inline-flex items-center gap-2 border border-accent-primary text-accent-primary hover:bg-accent-primary/10 font-semibold px-4 py-2 rounded-md text-sm transition-colors disabled:opacity-50 ${focusRing}`}
              >
                <FileSpreadsheet className="w-4 h-4" aria-hidden="true" />{busy === 'csv' ? 'Saving…' : 'Download CSV'}
              </button>
            </div>
          </div>

          {!r && !error ? <Skeleton rows={4} label="Building the report" /> : r && (
            <div className="space-y-4">
              <p className="text-[11px] text-text-muted flex items-center gap-1.5">
                <Download className="w-3 h-3" aria-hidden="true" />
                {r.report_version} · {r.synthetic ? 'synthetic data' : 'data not marked synthetic'} · {r.incident.title}
              </p>

              <Section id="rep-facts" title="1. Observed facts" hint="What the evidence contains and what matched exactly. Observations, not conclusions.">
                <div className="grid sm:grid-cols-2 gap-4 text-xs">
                  <div className="space-y-1">
                    <h3 className="font-semibold text-text-primary">Evidence records</h3>
                    {r.observed_facts.evidence.map(e => (
                      <p key={e.id} className="text-text-secondary break-all">
                        {e.type} · {e.characters} characters · <span className="font-mono">sha256 {e.sha256.slice(0, 16)}…</span>
                      </p>
                    ))}
                  </div>
                  <div className="space-y-1">
                    <h3 className="font-semibold text-text-primary">Identifiers (masked)</h3>
                    {r.observed_facts.identifiers.length === 0 ? <Empty>No identifiers were extracted.</Empty> :
                      r.observed_facts.identifiers.map((i, k) => (
                        <p key={k} className="text-text-secondary font-mono break-all">{i.type}: {i.display_value} ({i.mentions}x)</p>
                      ))}
                  </div>
                </div>
                <div className="space-y-1 text-xs">
                  <h3 className="font-semibold text-text-primary">Exact identifier matches</h3>
                  {r.observed_facts.observed_matches.length === 0 ? <Empty>None. This case shares no normalised identifier with another.</Empty> :
                    r.observed_facts.observed_matches.map(m => (
                      <p key={m.association_id} className="text-text-secondary">
                        With {incidentCode(m.other_incident_id)}: {m.shared_identifiers.map(s => s.display_value).join(', ')}. {m.explanation}
                      </p>
                    ))}
                </div>
              </Section>

              <Section id="rep-inf" title="2. Model inferences" hint="Produced by hand-written rules and heuristics. They can be wrong.">
                <div className="space-y-3 text-xs">
                  <p className="text-text-secondary">
                    Stage order: {r.model_inferences.stage_sequence.length ? r.model_inferences.stage_sequence.join(' → ') : 'no scam stage detected'}
                  </p>
                  {r.model_inferences.risk && (
                    <div>
                      <p className="text-text-primary font-semibold">
                        Risk indicator {r.model_inferences.risk.score} ({r.model_inferences.risk.band}) <span className="font-normal text-text-muted">· {r.model_inferences.risk.version}</span>
                      </p>
                      <p className="text-text-muted">{r.model_inferences.risk.note}</p>
                      <ul className="mt-1 space-y-0.5">
                        {r.model_inferences.risk.contributions.map((c, k) => (
                          <li key={k} className="text-text-secondary">
                            <span className="font-mono">{c.contribution > 0 ? '+' : ''}{c.contribution}</span> {c.factor}: {c.explanation}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div>
                    <h3 className="font-semibold text-text-primary">Tactics detected</h3>
                    {r.model_inferences.tactics.length === 0 ? <Empty>None.</Empty> : (
                      <ul className="space-y-0.5">
                        {r.model_inferences.tactics.map(t => (
                          <li key={t.label} className="text-text-secondary">
                            {LABEL_NAMES[t.label] ?? t.label} ({t.count}x, confidence up to {t.max_confidence}){t.excerpts[0] ? `: “${t.excerpts[0].text}”` : ''}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div>
                    <h3 className="font-semibold text-text-primary">Behaviour-only candidate links</h3>
                    {r.model_inferences.behavioural_candidates.length === 0 ? <Empty>None.</Empty> : (
                      <p className="text-text-secondary">
                        {r.model_inferences.behavioural_candidates.length} candidate link(s): a similar script with no shared identifier, to investigate and not a confirmed link.
                      </p>
                    )}
                  </div>
                  <div>
                    <h3 className="font-semibold text-text-primary">Campaign hypotheses</h3>
                    {r.model_inferences.campaign_hypotheses.length === 0 ? <Empty>This case is not part of a hypothesis.</Empty> : (
                      <ul>{r.model_inferences.campaign_hypotheses.map(c => (
                        <li key={c.id} className="text-text-secondary">{c.title} · {c.status.replace(/_/g, ' ').toLowerCase()} · confidence {c.confidence}</li>
                      ))}</ul>
                    )}
                  </div>
                </div>
              </Section>

              <Section id="rep-act" title="3. Analyst actions" hint="Reviews recorded by a person. Nothing here is decided by the system.">
                {r.analyst_actions.length === 0 ? <Empty>No analyst has reviewed a link or hypothesis for this case.</Empty> : (
                  <ul className="text-xs space-y-1">{r.analyst_actions.map((a, k) => (
                    <li key={k} className="text-text-secondary">
                      {a.decision} on {a.target_type} {a.target_id}: {a.previous_status} → {a.new_status}{a.note ? ` (“${a.note}”)` : ''}
                    </li>
                  ))}</ul>
                )}
              </Section>

              <Section id="rep-ce" title="4. Counter-evidence" hint="Why the links might not hold, shown next to the evidence for them.">
                {r.counter_evidence.findings.length === 0 && r.counter_evidence.disputed_or_rejected_links.length === 0
                  ? <Empty>No counter-evidence rule fired for this case.</Empty> : (
                  <ul className="text-xs space-y-1">
                    {r.counter_evidence.findings.map((f, k) => (
                      <li key={k} className="text-text-secondary">
                        <span className="font-mono">{f.rule_id}</span> ({f.severity}): {f.observation} {f.explanation}
                      </li>
                    ))}
                    {r.counter_evidence.disputed_or_rejected_links.map(l => (
                      <li key={l.association_id} className="text-text-secondary">
                        Link with {incidentCode(l.other_incident_id)} is {l.status.replace(/_/g, ' ').toLowerCase()}.
                      </li>
                    ))}
                  </ul>
                )}
              </Section>

              <Section id="rep-lim" title="5. Limitations" hint="Read these before relying on anything above.">
                <ul className="text-xs space-y-1 list-disc pl-5">
                  {r.limitations.map((l, k) => <li key={k} className="text-text-secondary">{l}</li>)}
                </ul>
              </Section>
            </div>
          )}
        </>
      )}
    </div>
  );
};
