import React from 'react';
import { X, CheckCircle, AlertTriangle, ShieldCheck, Clock, ExternalLink, HelpCircle } from 'lucide-react';
import { AssociationInspectorData } from '../../types';

interface InspectorShellProps {
  data: AssociationInspectorData | null;
  isOpen: boolean;
  onClose: () => void;
  onReview?: (decision: 'ACCEPT' | 'REJECT' | 'FLAG', note: string) => void;
}

export const InspectorShell: React.FC<InspectorShellProps> = ({ data, isOpen, onClose, onReview }) => {
  if (!isOpen || !data) return null;

  return (
    <div className="w-96 bg-bg-card border-l border-border-subtle h-full flex flex-col z-20 shadow-xl overflow-hidden animate-in slide-in-from-right duration-200">
      {/* Inspector Header */}
      <div className="p-4 border-b border-border-subtle flex items-center justify-between bg-bg-elevated/40">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono uppercase bg-accent-primary/20 text-accent-primary px-2 py-0.5 rounded border border-accent-primary/30">
            {data.status.replace('_', ' ')}
          </span>
          <span className="text-xs text-text-muted">ID: #{data.id}</span>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-text-muted hover:text-text-primary rounded hover:bg-bg-elevated transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Scrollable Inspector Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5 text-sm">
        {/* Core Rationale: Why this edge exists */}
        <div>
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
            <HelpCircle className="w-3.5 h-3.5 text-accent-primary" />
            Why This Link Exists
          </h4>
          <p className="text-xs text-text-primary bg-bg-main p-3 rounded-md border border-border-subtle leading-relaxed">
            {data.explanation}
          </p>
        </div>

        {/* Association Confidence Breakdown */}
        <div className="bg-bg-elevated/50 p-3 rounded-md border border-border-subtle">
          <div className="flex justify-between items-center mb-1 text-xs">
            <span className="text-text-secondary">Base Confidence:</span>
            <span className="font-mono text-text-primary">{(data.base_confidence * 100).toFixed(0)}%</span>
          </div>
          <div className="flex justify-between items-center mb-2 text-xs">
            <span className="text-text-secondary">Adjusted Confidence:</span>
            <span className="font-mono font-bold text-accent-primary">{(data.adjusted_confidence * 100).toFixed(0)}%</span>
          </div>
          <div className="w-full bg-bg-main h-1.5 rounded-full overflow-hidden">
            <div 
              className="bg-accent-primary h-full transition-all duration-300" 
              style={{ width: `${Math.round(data.adjusted_confidence * 100)}%` }}
            />
          </div>
        </div>

        {/* Shared Normalized Identifiers */}
        {data.shared_entities && data.shared_entities.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
              Shared Identifier(s)
            </h4>
            <div className="space-y-2">
              {data.shared_entities.map((ent, idx) => (
                <div key={idx} className="bg-bg-main p-2.5 rounded border border-border-subtle text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-mono text-text-muted uppercase">{ent.type}</span>
                    <span className="text-[10px] font-mono bg-bg-elevated px-1.5 py-0.5 rounded text-accent-secondary">
                      {ent.norm_method}
                    </span>
                  </div>
                  <div className="font-mono text-text-primary font-medium">{ent.display_value}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Source Evidence Excerpts */}
        <div>
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <ExternalLink className="w-3.5 h-3.5 text-text-muted" />
            Source Excerpts ({data.evidence.length})
          </h4>
          <div className="space-y-2">
            {data.evidence.map((ev, idx) => (
              <div key={idx} className="bg-bg-main p-2.5 rounded border border-border-subtle text-xs space-y-1">
                <div className="flex justify-between text-[10px] text-text-muted font-mono">
                  <span>Incident #{ev.incident_id}</span>
                  <span>Evidence #{ev.evidence_id}</span>
                </div>
                <p className="text-text-secondary text-xs italic bg-bg-card p-2 rounded border border-border-subtle/50">
                  "{ev.excerpt}"
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Counter-Evidence Findings (§6.10) */}
        <div>
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-risk-high" />
            Counter-Evidence Panel ({data.counter_evidence.length})
          </h4>
          {data.counter_evidence.length === 0 ? (
            <div className="text-xs text-text-muted bg-bg-main/50 p-3 rounded border border-border-subtle text-center">
              No contradictory signals identified.
            </div>
          ) : (
            <div className="space-y-2">
              {data.counter_evidence.map((ce, idx) => (
                <div key={idx} className="bg-risk-critical/10 border border-risk-critical/30 p-2.5 rounded text-xs space-y-1">
                  <div className="flex items-center justify-between font-mono text-[10px]">
                    <span className="font-bold text-risk-critical">{ce.rule_id}</span>
                    <span className="text-risk-critical uppercase">{ce.severity}</span>
                  </div>
                  <div className="text-text-primary font-medium">{ce.observation}</div>
                  <div className="text-text-secondary text-[11px]">{ce.explanation}</div>
                  <div className="text-risk-critical font-mono text-[10px] text-right">
                    Impact: {ce.confidence_impact}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Component Scores (Fingerprint breakdown) */}
        {data.component_scores && Object.keys(data.component_scores).length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
              Component Breakdown
            </h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {Object.entries(data.component_scores).map(([k, v]) => (
                <div key={k} className="bg-bg-main p-2 rounded border border-border-subtle">
                  <div className="text-[10px] text-text-muted uppercase">{k}</div>
                  <div className="font-mono text-text-primary font-semibold">
                    {typeof v === 'number' ? (v * 100).toFixed(0) + '%' : String(v)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Version Provenance */}
        <div className="pt-2 border-t border-border-subtle flex justify-between text-[10px] font-mono text-text-muted">
          <span>Algo: {data.versions?.algorithm || 'vigil@3.1.0'}</span>
          <span>Extractor: {data.versions?.extractor || 'rules@1.0'}</span>
        </div>
      </div>

      {/* Analyst Review Controls (§6.8, Invariant I3) */}
      <div className="p-3 border-t border-border-subtle bg-bg-elevated/40 space-y-2">
        <div className="text-[11px] font-semibold text-text-secondary">Analyst Review Action</div>
        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={() => onReview?.('ACCEPT', 'Analyst verified association')}
            className="flex items-center justify-center gap-1 bg-accent-secondary/20 hover:bg-accent-secondary/30 text-accent-secondary border border-accent-secondary/40 py-1.5 rounded text-xs font-medium transition-colors"
          >
            <CheckCircle className="w-3.5 h-3.5" />
            Accept
          </button>
          <button
            onClick={() => onReview?.('FLAG', 'Contradictions flagged for inquiry')}
            className="flex items-center justify-center gap-1 bg-risk-elevated/20 hover:bg-risk-elevated/30 text-risk-elevated border border-risk-elevated/40 py-1.5 rounded text-xs font-medium transition-colors"
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            Flag
          </button>
          <button
            onClick={() => onReview?.('REJECT', 'Hypothesis dismissed by analyst')}
            className="flex items-center justify-center gap-1 bg-risk-critical/20 hover:bg-risk-critical/30 text-risk-critical border border-risk-critical/40 py-1.5 rounded text-xs font-medium transition-colors"
          >
            <X className="w-3.5 h-3.5" />
            Reject
          </button>
        </div>
      </div>
    </div>
  );
};
