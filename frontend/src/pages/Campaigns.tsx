import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, AlertTriangle, Layers, Link2, ShieldQuestion } from 'lucide-react';
import { apiClient } from '../services/api/client';
import type { CampaignDetail, CampaignLink, CampaignListItem, ReviewDecision } from '../types';
import { FindingCard } from '../components/counterevidence/FindingCard';
import { SEVERITY_LABEL, severityTone } from '../components/counterevidence/finding_view';
import { ReviewControls } from '../components/review/ReviewControls';
import { alignmentRows, stageChips } from '../components/tactics/segments';
import { basisLabel, basisTone, confidencePct, linkSummary, statusTone } from '../components/campaigns/campaign_view';

interface CampaignsProps {
  canReview: boolean;
  refreshKey: number;
  /** Hypothesis chosen by the URL (/campaigns/<id>); null means "show the first one". */
  selectedId: number | null;
  onSelect: (id: number) => void;
  onInspectAssociation: (assocId: number) => void;
  onSelectIncident: (id: number) => void;
  onChanged: () => void;
}

const bandText = (band: string) =>
  band === 'CRITICAL' ? 'text-risk-critical' : band === 'HIGH' ? 'text-risk-high' :
  band === 'ELEVATED' ? 'text-risk-elevated' : 'text-risk-low';

export const Campaigns: React.FC<CampaignsProps> = ({
  canReview, refreshKey, selectedId, onSelect, onInspectAssociation, onSelectIncident, onChanged,
}) => {
  const [list, setList] = useState<CampaignListItem[]>([]);
  const selected = selectedId ?? list[0]?.id ?? null;
  const [detail, setDetail] = useState<CampaignDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const items = await apiClient.listCampaigns();
        if (cancelled) return;
        setList(items);
      } catch (e: any) {
        if (!cancelled) setError(e?.message || 'Failed to load campaign hypotheses.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [refreshKey]);

  useEffect(() => {
    setDetail(null);
    if (selected == null) return;
    let cancelled = false;
    setError(null);
    apiClient.getCampaign(selected)
      .then(d => { if (!cancelled) setDetail(d); })
      .catch((e: any) => { if (!cancelled) setError(e?.message || 'Failed to load this hypothesis.'); });
    return () => { cancelled = true; };
  }, [selected, refreshKey]);

  const review = useCallback(async (decision: ReviewDecision, note: string) => {
    if (selected == null) return;
    setDetail(await apiClient.reviewCampaign(selected, decision, note));
    onChanged();
  }, [selected, onChanged]);

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">Campaign hypotheses</h1>
        <p className="text-sm text-text-secondary mt-1 max-w-3xl">
          Groups of incidents that may be related, built from shared identifiers and similar behaviour.
          Every group is a hypothesis for an analyst to review, not a finding. A behavioural match means a similar
          script (playbook); it does not identify a specific group, person or organisation.
        </p>
      </div>

      {error && (
        <div role="alert" className="flex gap-2 bg-risk-critical/10 border border-risk-critical/30 rounded-lg p-3 text-xs text-risk-critical">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" /> {error}
        </div>
      )}

      {loading ? (
        <div role="status" className="p-8 text-center text-sm font-mono text-text-muted animate-pulse">Loading hypotheses…</div>
      ) : list.length === 0 ? (
        <div className="bg-bg-card border border-border-subtle rounded-lg p-8 text-center text-sm text-text-muted">
          <ShieldQuestion className="w-6 h-6 mx-auto mb-2 text-text-muted" aria-hidden="true" />
          No campaign hypotheses yet. A hypothesis appears when two or more incidents share an identifier or follow a
          similar script.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <ul className="lg:col-span-4 space-y-3" aria-label="Campaign hypotheses">
            {list.map(c => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => onSelect(c.id)}
                  aria-pressed={selected === c.id}
                  className={`w-full text-left bg-bg-card border rounded-lg p-4 space-y-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary ${
                    selected === c.id ? 'border-accent-primary' : 'border-border-subtle hover:border-accent-primary/50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[10px] text-text-muted">H-{String(c.id).padStart(3, '0')}</span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${statusTone(c.status)}`}>{c.status_label}</span>
                  </div>
                  <div className="text-sm font-semibold text-text-primary">{c.hypothesis_title}</div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-text-muted font-mono">
                    <span>{c.member_count} incidents</span>
                    <span>link confidence {confidencePct(c.confidence)}</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(c.basis_counts).map(([b, n]) => (
                      <span key={b} className={`text-[10px] px-1.5 py-0.5 rounded border ${basisTone(b)}`}>
                        {n} × {b.toLowerCase()}
                      </span>
                    ))}
                    {(c.counter_evidence_count ?? 0) > 0 && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded border ${severityTone(c.highest_severity ?? 'LOW')}`}>
                        ⚠ {c.counter_evidence_count} counter-evidence finding{c.counter_evidence_count === 1 ? '' : 's'}
                        {c.highest_severity ? ` (worst: ${SEVERITY_LABEL[c.highest_severity].toLowerCase()})` : ''}
                      </span>
                    )}
                  </div>
                </button>
              </li>
            ))}
          </ul>

          <section className="lg:col-span-8 space-y-5" aria-label="Hypothesis detail">
            {!detail ? (
              <div role="status" className="p-8 text-center text-sm font-mono text-text-muted animate-pulse">Loading…</div>
            ) : (
              <>
                <div className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h2 className="text-base font-bold text-text-primary">{detail.hypothesis_title}</h2>
                    <span className={`text-xs font-mono px-2 py-0.5 rounded border ${statusTone(detail.status)}`}>{detail.status_label}</span>
                  </div>
                  <p className="text-xs text-text-secondary bg-bg-main border border-border-subtle rounded p-3 leading-relaxed">{detail.disclaimer}</p>
                  <dl className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                    <div><dt className="text-text-muted">Mean link confidence</dt><dd className="font-mono text-text-primary">{confidencePct(detail.confidence)}</dd></div>
                    <div><dt className="text-text-muted">Incidents</dt><dd className="font-mono text-text-primary">{detail.member_count}</dd></div>
                    <div>
                      <dt className="text-text-muted">Weakest link</dt>
                      <dd className="font-mono">
                        {detail.weakest_link_association_id != null ? (
                          <button type="button" className="text-accent-primary hover:underline"
                                  onClick={() => onInspectAssociation(detail.weakest_link_association_id as number)}>
                            link #{detail.weakest_link_association_id}
                          </button>
                        ) : '—'}
                      </dd>
                    </div>
                  </dl>
                </div>

                <div className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-3">
                  <h3 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-accent-primary" aria-hidden="true" /> Incidents in this hypothesis
                  </h3>
                  <ul className="space-y-2">
                    {detail.members.map(m => (
                      <li key={m.incident_id} className="bg-bg-main border border-border-subtle rounded-md p-3 space-y-1.5">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <button type="button" onClick={() => onSelectIncident(m.incident_id)}
                                  className="text-sm font-semibold text-text-primary hover:text-accent-primary text-left">
                            INC-{String(m.incident_id).padStart(4, '0')} · {m.title}
                          </button>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded border ${basisTone(m.membership_basis)}`}>{basisLabel(m.membership_basis)}</span>
                        </div>
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-text-muted font-mono">
                          <span className={bandText(m.risk_band)}>risk {m.risk_score} {m.risk_band}</span>
                          <span>{m.source_channel} · {m.language}</span>
                          <span>{m.institution_class.replace(/_/g, ' ').toLowerCase()} · {m.payment_channel.replace(/_/g, ' ').toLowerCase()}</span>
                        </div>
                        <ol className="flex flex-wrap gap-1" aria-label="Stages observed">
                          {stageChips(m.stage_sequence).map(c => (
                            <li key={c.stage} className={`text-[10px] px-1.5 py-0.5 rounded border font-mono ${
                              c.observed ? 'border-accent-primary/40 text-accent-primary bg-accent-primary/10' : 'border-border-subtle text-text-muted'}`}>
                              {c.order ? `${c.order}. ` : ''}{c.stage}
                            </li>
                          ))}
                        </ol>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-3">
                  <h3 className="text-sm font-semibold text-text-primary">Playbook alignment, side by side</h3>
                  <p className="text-[11px] text-text-muted">
                    Each row is one incident; each column a stage of the usual script. A number is the order in which the stage appeared. A shared script is a lead, not proof of one actor.
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <caption className="sr-only">Stage order of every incident in this hypothesis</caption>
                      <thead className="text-[10px] uppercase text-text-muted">
                        <tr>
                          <th scope="col" className="py-1 pr-3">Incident</th>
                          {alignmentRows(detail.members.map(m => ({ id: m.incident_id, sequence: m.stage_sequence })))[0]?.cells.map(c => (
                            <th key={c.stage} scope="col" className="py-1 px-1 text-center">{c.stage.slice(0, 5)}</th>
                          ))}
                          <th scope="col" className="py-1 pl-2">Order</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-subtle">
                        {alignmentRows(detail.members.map(m => ({ id: m.incident_id, sequence: m.stage_sequence }))).map(row => (
                          <tr key={row.id}>
                            <th scope="row" className="py-1.5 pr-3 font-mono text-text-primary">INC-{String(row.id).padStart(4, '0')}</th>
                            {row.cells.map(c => (
                              <td key={c.stage} className={`py-1.5 px-1 text-center font-mono ${c.order ? 'text-accent-primary font-bold' : 'text-text-muted'}`}>
                                <span aria-label={c.order ? `${c.stage} was stage ${c.order}` : `${c.stage} not seen`}>{c.order ?? '–'}</span>
                              </td>
                            ))}
                            <td className="py-1.5 pl-2 text-text-secondary">{row.inOrder ? 'usual order' : 'different order'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-3">
                  <h3 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
                    <Link2 className="w-4 h-4 text-accent-primary" aria-hidden="true" /> Links between them
                  </h3>
                  <ul className="space-y-2">
                    {detail.links.map(l => (
                      <li key={l.id} className="bg-bg-main border border-border-subtle rounded-md p-3 text-xs space-y-1">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-mono text-text-primary">
                            INC-{String(l.incident_a_id).padStart(4, '0')} ↔ INC-{String(l.incident_b_id).padStart(4, '0')}
                          </span>
                          <span className="font-mono text-text-secondary">
                            {linkSummary(l)} · {confidencePct(l.adjusted_confidence)}{l.is_weakest ? ' · weakest link' : ''}
                          </span>
                        </div>
                        <p className="text-text-muted leading-snug">{l.explanation}</p>
                        <button type="button" onClick={() => onInspectAssociation(l.id)} className="text-accent-primary hover:underline font-medium">
                          Open evidence inspector →
                        </button>
                      </li>
                    ))}
                  </ul>
                  {detail.excluded_links.length > 0 && (
                    <div className="pt-2 border-t border-border-subtle">
                      <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1.5">Excluded links (not used to connect incidents)</h4>
                      <ul className="space-y-1.5">
                        {detail.excluded_links.map(l => (
                          <li key={l.id} className="text-[11px] text-text-secondary flex flex-wrap justify-between gap-2">
                            <span className="font-mono">INC-{String(l.incident_a_id).padStart(4, '0')} ↔ INC-{String(l.incident_b_id).padStart(4, '0')} · {linkSummary(l)}</span>
                            <button type="button" onClick={() => onInspectAssociation(l.id)} className="text-accent-primary hover:underline">Inspect</button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {detail.shared_indicators.length > 0 && (
                    <div className="pt-2 border-t border-border-subtle">
                      <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1.5">Identifiers seen in more than one incident</h4>
                      <ul className="flex flex-wrap gap-2">
                        {detail.shared_indicators.map(s => (
                          <li key={`${s.type}-${s.display_value}`} className="text-[11px] font-mono bg-bg-main border border-border-subtle rounded px-2 py-1 text-text-secondary">
                            {s.type.replace(/_/g, ' ').toLowerCase()}: {s.display_value}
                            <span className="text-text-muted"> (in {s.incident_ids.length} incidents)</span>
                          </li>
                        ))}
                      </ul>
                      <p className="text-[10px] text-text-muted mt-1.5">Seeing the same identifier twice is an observation, not proof of one origin.</p>
                    </div>
                  )}
                </div>

                <section aria-label="Counter-evidence across this hypothesis" className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-3">
                  <h3 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4 text-risk-high" aria-hidden="true" />
                    Why this hypothesis might NOT hold ({detail.counter_evidence.length})
                  </h3>
                  {detail.counter_evidence.length === 0 ? (
                    <p className="text-xs text-text-muted">
                      No contradicting evidence was found by the rules that are implemented. Some checks are not built yet,
                      so this does not prove the hypothesis.
                    </p>
                  ) : (
                    <>
                      <p className="text-[11px] text-text-muted">
                        Findings on the links between these incidents, worst first. They stay on record even after an analyst accepts the hypothesis.
                      </p>
                      <ul className="space-y-2">
                        {detail.counter_evidence.map((f, i) => (
                          <FindingCard
                            key={`${f.association_id}-${f.rule_id}-${i}`}
                            ruleId={f.rule_id}
                            kind={f.kind}
                            severity={f.severity}
                            observation={f.observation}
                            explanation={f.explanation}
                            impact={f.confidence_impact}
                            ruleVersion={f.rule_version}
                            refs={f.evidence_refs}
                            context={(
                              <>
                                link #{f.association_id} · INC-{String(f.incident_a_id).padStart(4, '0')} ↔ INC-{String(f.incident_b_id).padStart(4, '0')} · {linkSummary({ ...(detail.links.concat(detail.excluded_links).find(l => l.id === f.association_id) as CampaignLink), status: f.link_status })}
                                {' '}
                                <button type="button" onClick={() => onInspectAssociation(f.association_id)} className="text-accent-primary hover:underline">inspect</button>
                              </>
                            )}
                          />
                        ))}
                      </ul>
                    </>
                  )}
                </section>

                <div className="bg-bg-card border border-border-subtle rounded-lg p-5">
                  <ReviewControls subject="hypothesis" state={detail.review.state} history={detail.review.history}
                                  canReview={canReview} onReview={review} />
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
};
