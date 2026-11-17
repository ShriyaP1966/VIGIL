import React, { useEffect, useState } from 'react';
import { ArrowLeft, Network, Info, Lock, AlertCircle, Link2, ShieldCheck, ShieldAlert } from 'lucide-react';
import { apiClient } from '../services/api/client';
import { GraphEdge, IncidentDetail } from '../types';
import { TacticTimeline } from '../components/tactics/TacticTimeline';
import { TacticTranscript } from '../components/tactics/TacticTranscript';
import { associationIdOf, isAssociationEdge } from '../components/graph/graph_layout';

interface InvestigationDetailProps {
  incidentId: number;
  onBack: () => void;
  onOpenGraph: () => void;
  onInspectAssociation: (assocId: number) => void;
}

const bandText = (band: string) =>
  band === 'CRITICAL' ? 'text-risk-critical' :
  band === 'HIGH' ? 'text-risk-high' :
  band === 'ELEVATED' ? 'text-risk-elevated' : 'text-risk-low';

const bandChip = (band: string) =>
  band === 'CRITICAL' ? 'bg-risk-critical/20 text-risk-critical' :
  band === 'HIGH' ? 'bg-risk-high/20 text-risk-high' :
  band === 'ELEVATED' ? 'bg-risk-elevated/20 text-risk-elevated' : 'bg-risk-low/20 text-risk-low';

export const InvestigationDetail: React.FC<InvestigationDetailProps> = ({
  incidentId, onBack, onOpenGraph, onInspectAssociation,
}) => {
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [links, setLinks] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [data, graph] = await Promise.all([apiClient.getIncident(incidentId), apiClient.getGraph()]);
        if (cancelled) return;
        setIncident(data);
        const node = `incident_${incidentId}`;
        setLinks(graph.edges.filter(e => isAssociationEdge(e) && (e.source === node || e.target === node)));
      } catch (e: any) {
        if (!cancelled) setError(e?.message || 'Failed to load this investigation.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [incidentId]);

  if (loading) {
    return (
      <div role="status" className="p-8 text-center text-sm font-mono text-text-muted animate-pulse">
        Loading INC-{incidentId.toString().padStart(4, '0')}…
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div role="alert" className="p-8 text-center space-y-4">
        <AlertCircle className="w-6 h-6 text-risk-critical mx-auto" aria-hidden="true" />
        <div className="text-risk-critical text-sm">{error || 'Incident not found.'}</div>
        <button type="button" onClick={onBack} className="text-accent-primary text-xs hover:underline">
          Back to Overview
        </button>
      </div>
    );
  }

  const analysis = incident.analysis;
  const riskScore = analysis?.risk_score ?? 0;
  const riskBand = analysis?.risk_band ?? 'LOW';
  const contributions = analysis?.contributions ?? [];
  const observedStages: string[] = Array.isArray(analysis?.fingerprint?.stage_sequence)
    ? analysis!.fingerprint.stage_sequence
    : [];
  const injectionFlags: string[] = analysis?.injection_flags ?? [];
  const contributionSum = contributions.reduce((s, c) => s + c.contribution, 0);
  const redactions = incident.redactions ?? [];
  const redactedTotal = redactions.reduce((s, r) => s + r.count, 0);

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="w-4 h-4" aria-hidden="true" />
          <span>Back to Overview</span>
        </button>
        <button
          type="button"
          onClick={onOpenGraph}
          className="inline-flex items-center gap-2 bg-bg-elevated hover:bg-border-subtle text-accent-primary border border-border-subtle px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
        >
          <Network className="w-3.5 h-3.5" aria-hidden="true" />
          <span>View in Intelligence Graph</span>
        </button>
      </div>

      {/* Case header */}
      <div className="bg-bg-card border border-border-subtle rounded-lg p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1.5 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs bg-bg-elevated px-2 py-0.5 rounded text-text-muted border border-border-subtle">
              INC-{incident.id.toString().padStart(4, '0')}
            </span>
            <span className="text-xs font-mono uppercase bg-accent-primary/10 text-accent-primary px-2 py-0.5 rounded">
              {incident.source_channel}
            </span>
            <span className="text-xs font-mono uppercase bg-bg-elevated text-text-muted px-2 py-0.5 rounded">
              {incident.language}
            </span>
            {incident.is_synthetic && (
              <span className="text-xs font-mono uppercase bg-bg-elevated text-text-muted px-2 py-0.5 rounded">synthetic</span>
            )}
          </div>
          <h1 className="text-xl font-bold text-text-primary break-words">{incident.title}</h1>
        </div>

        <div className="bg-bg-main p-4 rounded-lg border border-border-subtle shrink-0">
          <div className="text-[10px] uppercase font-mono text-text-muted tracking-wider">Scam risk indicator</div>
          <div className="flex items-baseline gap-2">
            <span className={`text-3xl font-extrabold font-mono ${bandText(riskBand)}`}>{riskScore}</span>
            <span className="text-xs font-bold text-text-muted">/ 100</span>
            <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded uppercase ${bandChip(riskBand)}`}>{riskBand}</span>
          </div>
          <div className="text-[10px] text-text-muted mt-0.5 italic">Experimental heuristic, not a probability.</div>
        </div>
      </div>

      {redactedTotal > 0 && (
        <div role="note" className="bg-accent-secondary/10 border border-accent-secondary/30 rounded-lg p-3 text-xs text-text-secondary flex gap-2">
          <ShieldCheck className="w-4 h-4 shrink-0 text-accent-secondary mt-0.5" aria-hidden="true" />
          <span>
            <strong className="text-text-primary">
              {redactedTotal} sensitive value{redactedTotal === 1 ? ' was' : 's were'} removed before storage
            </strong>{' '}
            ({redactions.map(r => `${r.kind.replace('_', ' ').toLowerCase()} ×${r.count}`).join(', ')}).
            They appear as [REDACTED:…] below. Detection is best effort, so avoid pasting real secrets.
          </span>
        </div>
      )}

      {injectionFlags.length > 0 && (
        <div role="alert" className="bg-risk-critical/10 border border-risk-critical/40 rounded-lg p-3 text-xs flex gap-2">
          <ShieldAlert className="w-4 h-4 shrink-0 text-risk-critical mt-0.5" aria-hidden="true" />
          <span className="text-text-secondary">
            <strong className="text-risk-critical">Manipulation attempt detected.</strong>{' '}
            This text contains instruction-like wording aimed at the analyser ({injectionFlags.join(', ').replace(/_/g, ' ')}).
            The flagged wording is outlined below, was ignored when detecting tactics, and cannot lower the risk indicator.
          </span>
        </div>
      )}

      <TacticTimeline
        stageSequence={observedStages}
        credentialRequested={Boolean(analysis?.fingerprint?.credential_requested)}
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 space-y-6">
          {incident.evidence_items.map((ev, i) => (
            <div key={ev.id} className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-3">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-sm font-semibold text-text-primary">
                  Evidence {incident.evidence_items.length > 1 ? `${i + 1} · ` : ''}{ev.type.replace('_', ' ')}
                </h2>
                <span className="text-[10px] font-mono text-text-muted uppercase">{ev.provenance}</span>
              </div>
              {/* Evidence is untrusted: rendered as text, never as HTML. */}
              {ev.utterances && ev.utterances.length > 0 ? (
                <TacticTranscript utterances={ev.utterances} />
              ) : (
                <div className="bg-bg-main border border-border-subtle rounded-md p-4 text-sm font-mono text-text-secondary whitespace-pre-wrap break-words leading-relaxed">
                  {ev.original_text}
                </div>
              )}
              <div className="text-[10px] font-mono text-text-muted break-all">SHA-256 of original: {ev.sha256}</div>

              <div className="pt-2">
                <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider flex items-center gap-1.5 mb-2">
                  <Lock className="w-3.5 h-3.5 text-accent-secondary" aria-hidden="true" />
                  Extracted indicators (masked for display)
                </h3>
                {ev.entities.length === 0 ? (
                  <p className="text-xs text-text-muted italic">No structured indicators extracted.</p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {ev.entities.map((ent, idx) => (
                      <div key={`${ent.id}-${idx}`} className="bg-bg-main p-3 rounded-md border border-border-subtle text-xs space-y-1">
                        <div className="flex justify-between items-center">
                          <span className="font-mono text-[10px] text-text-muted uppercase font-semibold">{ent.type}</span>
                          <span className="text-[10px] font-mono bg-bg-elevated px-1.5 py-0.5 rounded text-accent-secondary">
                            {ent.norm_method}
                          </span>
                        </div>
                        <div className="font-mono font-medium text-text-primary text-sm break-all">{ent.display_value}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="lg:col-span-5 space-y-6">
          {/* Observed matches */}
          <div className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-3">
            <h2 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
              <Link2 className="w-4 h-4 text-accent-primary" aria-hidden="true" />
              Observed matches ({links.length})
            </h2>
            {links.length === 0 ? (
              <p className="text-xs text-text-muted">No identifier shared with another incident.</p>
            ) : (
              <ul className="space-y-2">
                {links.map(edge => {
                  const id = associationIdOf(edge);
                  const other = edge.source === `incident_${incidentId}` ? edge.target : edge.source;
                  return (
                    <li key={edge.id} className="bg-bg-main border border-border-subtle rounded-md p-3 text-xs space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-accent-primary">{(edge.status ?? edge.type).replace(/_/g, ' ').toLowerCase()}</span>
                        <span className="font-mono text-text-secondary">with {other.replace('incident_', 'INC-')}</span>
                      </div>
                      <p className="text-text-muted leading-snug">{edge.explanation}</p>
                      {id != null && (
                        <button
                          type="button"
                          onClick={() => onInspectAssociation(id)}
                          className="text-accent-primary hover:underline font-medium"
                        >
                          Open evidence inspector →
                        </button>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* Why this score */}
          <div className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
                <Info className="w-4 h-4 text-accent-primary" aria-hidden="true" />
                Why this score
              </h2>
              <p className="text-xs text-text-muted mt-0.5">
                Contributions add up exactly to {riskScore}/100. Version {analysis?.risk_version ?? 'n/a'}.
              </p>
            </div>

            <div className="space-y-2.5">
              {contributions.length === 0 ? (
                <div className="text-xs text-text-muted italic bg-bg-main p-3 rounded">
                  No risk factors triggered, so the indicator is 0.
                </div>
              ) : (
                contributions.map((c, idx) => (
                  <div key={idx} className="bg-bg-main border border-border-subtle p-3 rounded-md flex items-start justify-between gap-3 text-xs">
                    <div className="space-y-0.5 min-w-0">
                      <div className="font-semibold text-text-primary">{c.factor}</div>
                      <div className="text-text-muted text-[11px] leading-snug">{c.explanation}</div>
                      <div className="text-[10px] font-mono text-text-muted pt-0.5">
                        Ref: {c.evidence_ref || 'global'} · {c.rule_version} · {c.effect.toLowerCase()}
                      </div>
                    </div>
                    <div className={`font-mono font-bold text-sm shrink-0 ${c.effect === 'SUPPORTING' ? 'text-risk-high' : 'text-risk-low'}`}>
                      {c.contribution > 0 ? `+${c.contribution}` : c.contribution}
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="pt-3 border-t border-border-subtle flex justify-between items-center text-xs font-mono">
              <span className="text-text-secondary font-semibold">Sum of contributions</span>
              <span className="font-bold text-accent-primary">{contributionSum} pts</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
