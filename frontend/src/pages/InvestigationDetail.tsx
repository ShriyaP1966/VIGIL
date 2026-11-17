import React, { useEffect, useState } from 'react';
import { ShieldAlert, ArrowLeft, Network, AlertTriangle, CheckCircle, Info, Lock } from 'lucide-react';
import { apiClient } from '../services/api/client';
import { IncidentDetail } from '../types';

interface InvestigationDetailProps {
  incidentId: number;
  onBack: () => void;
  onOpenGraph: () => void;
}

export const InvestigationDetail: React.FC<InvestigationDetailProps> = ({ incidentId, onBack, onOpenGraph }) => {
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await apiClient.getIncident(incidentId);
        setIncident(data);
      } catch (e) {
        console.error('Failed to load incident detail', e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [incidentId]);

  if (loading) {
    return (
      <div className="p-8 text-center text-sm font-mono text-text-muted animate-pulse">
        Loading investigation details for INC-{incidentId.toString().padStart(4, '0')}...
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="p-8 text-center space-y-4">
        <div className="text-risk-critical text-sm">Incident not found.</div>
        <button onClick={onBack} className="text-accent-primary text-xs hover:underline">
          Return to Overview
        </button>
      </div>
    );
  }

  const analysis = incident.analysis;
  const riskScore = analysis?.risk_score || 0;
  const riskBand = analysis?.risk_band || 'LOW';
  const contributions = analysis?.contributions || [];
  const evidence = incident.evidence_items[0];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Navigation & Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Overview</span>
        </button>
        <button
          onClick={onOpenGraph}
          className="inline-flex items-center gap-2 bg-bg-elevated hover:bg-border-subtle text-accent-primary border border-border-subtle px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
        >
          <Network className="w-3.5 h-3.5" />
          <span>View in Intelligence Graph</span>
        </button>
      </div>

      {/* Case Header Card */}
      <div className="bg-bg-card border border-border-subtle rounded-lg p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs bg-bg-elevated px-2 py-0.5 rounded text-text-muted border border-border-subtle">
              INC-{incident.id.toString().padStart(4, '0')}
            </span>
            <span className="text-xs font-mono uppercase bg-accent-primary/10 text-accent-primary px-2 py-0.5 rounded">
              {incident.source_channel}
            </span>
            <span className="text-xs font-mono uppercase bg-bg-elevated text-text-muted px-2 py-0.5 rounded">
              {incident.language}
            </span>
          </div>
          <h1 className="text-xl font-bold text-text-primary">{incident.title}</h1>
          <p className="text-xs text-text-muted">
            Provenance SHA-256: <span className="font-mono">{evidence?.sha256 ? evidence.sha256.slice(0, 16) + '...' : 'N/A'}</span>
          </p>
        </div>

        {/* Risk Score Widget */}
        <div className="bg-bg-main p-4 rounded-lg border border-border-subtle flex items-center gap-5 shrink-0">
          <div>
            <div className="text-[10px] uppercase font-mono text-text-muted tracking-wider">
              Scam Risk Heuristic
            </div>
            <div className="flex items-baseline gap-2">
              <span className={`text-3xl font-extrabold font-mono ${
                riskBand === 'CRITICAL' ? 'text-risk-critical' :
                riskBand === 'HIGH' ? 'text-risk-high' :
                riskBand === 'ELEVATED' ? 'text-risk-elevated' : 'text-risk-low'
              }`}>
                {riskScore}
              </span>
              <span className="text-xs font-bold text-text-muted">/ 100</span>
              <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded uppercase ${
                riskBand === 'CRITICAL' ? 'bg-risk-critical/20 text-risk-critical' :
                riskBand === 'HIGH' ? 'bg-risk-high/20 text-risk-high' :
                riskBand === 'ELEVATED' ? 'bg-risk-elevated/20 text-risk-elevated' : 'bg-risk-low/20 text-risk-low'
              }`}>
                {riskBand}
              </span>
            </div>
            <div className="text-[10px] text-text-muted mt-0.5 italic">
              *Experimental heuristic, not calibrated probability.
            </div>
          </div>
        </div>
      </div>

      {/* Tactic Stage Progression Bar */}
      <div className="bg-bg-card border border-border-subtle rounded-lg p-4 space-y-2">
        <div className="text-xs font-semibold text-text-muted uppercase tracking-wider">
          Playbook Tactic Progression Sequence (§6.6)
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {['AUTHORITY', 'ALLEGATION', 'THREAT', 'ISOLATION', 'URGENCY', 'DEMAND'].map((stage, idx) => {
            const isObserved = (analysis?.fingerprint?.stage_sequence || ['AUTHORITY', 'DEMAND']).includes(stage);
            return (
              <div
                key={stage}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border font-mono text-xs ${
                  isObserved 
                    ? 'bg-accent-primary/10 border-accent-primary/40 text-accent-primary font-semibold' 
                    : 'bg-bg-main border-border-subtle text-text-muted opacity-50'
                }`}
              >
                <span>{idx + 1}.</span>
                <span>{stage}</span>
                {isObserved && <CheckCircle className="w-3.5 h-3.5 text-accent-primary" />}
              </div>
            );
          })}
        </div>
      </div>

      {/* Two Column Layout: Evidence & Risk Contributions */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Evidence Transcript & Extracted Entities */}
        <div className="lg:col-span-7 space-y-6">
          {/* Evidence Transcript */}
          <div className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-text-primary">Evidence Content</h3>
              <span className="text-[10px] font-mono text-text-muted uppercase">
                Extractor: {analysis?.extractor || 'RuleMLExtractor'}
              </span>
            </div>
            <div className="bg-bg-main border border-border-subtle rounded-md p-4 text-sm font-mono text-text-secondary whitespace-pre-wrap leading-relaxed">
              {evidence?.original_text}
            </div>
          </div>

          {/* Masked Extracted Indicators */}
          <div className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-3">
            <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <Lock className="w-4 h-4 text-accent-secondary" />
              Extracted Indicators (Privacy Masked §5.5)
            </h3>
            {(!evidence?.entities || evidence.entities.length === 0) ? (
              <p className="text-xs text-text-muted italic">No structured indicators extracted.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {evidence.entities.map((ent, idx) => (
                  <div key={idx} className="bg-bg-main p-3 rounded-md border border-border-subtle text-xs space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="font-mono text-[10px] text-text-muted uppercase font-semibold">
                        {ent.type}
                      </span>
                      <span className="text-[10px] font-mono bg-bg-elevated px-1.5 py-0.5 rounded text-accent-secondary">
                        {ent.norm_method}
                      </span>
                    </div>
                    <div className="font-mono font-medium text-text-primary text-sm">
                      {ent.display_value}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: "Why this score" Contribution Breakdown */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
                <Info className="w-4 h-4 text-accent-primary" />
                Why This Score (Contribution Ledger)
              </h3>
              <p className="text-xs text-text-muted mt-0.5">
                Additive components summing exactly to {riskScore}/100.
              </p>
            </div>

            <div className="space-y-2.5">
              {contributions.length === 0 ? (
                <div className="text-xs text-text-muted italic bg-bg-main p-3 rounded">
                  No individual risk factors triggered. Baseline neutral.
                </div>
              ) : (
                contributions.map((c, idx) => (
                  <div
                    key={idx}
                    className="bg-bg-main border border-border-subtle p-3 rounded-md flex items-start justify-between gap-3 text-xs"
                  >
                    <div className="space-y-0.5">
                      <div className="font-semibold text-text-primary">{c.factor}</div>
                      <div className="text-text-muted text-[11px] leading-snug">{c.explanation}</div>
                      <div className="text-[10px] font-mono text-text-muted pt-0.5">
                        Ref: {c.evidence_ref || 'global'} · {c.rule_version}
                      </div>
                    </div>
                    <div className={`font-mono font-bold text-sm shrink-0 ${
                      c.effect === 'SUPPORTING' ? 'text-risk-high' : 'text-risk-low'
                    }`}>
                      {c.contribution > 0 ? `+${c.contribution}` : c.contribution}
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="pt-3 border-t border-border-subtle flex justify-between items-center text-xs font-mono">
              <span className="text-text-secondary font-semibold">Ledger Sum Total:</span>
              <span className="font-bold text-accent-primary">{riskScore} pts</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
