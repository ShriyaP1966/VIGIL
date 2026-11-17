import React, { useEffect, useRef } from 'react';
import { X, AlertTriangle, ExternalLink, HelpCircle, Info } from 'lucide-react';
import { AssociationInspectorData, NodeInspectorInfo } from '../../types';

interface InspectorShellProps {
  association: AssociationInspectorData | null;
  node: NodeInspectorInfo | null;
  isOpen: boolean;
  onClose: () => void;
  onOpenIncident: (id: number) => void;
}

const SectionTitle: React.FC<{ icon?: React.ReactNode; children: React.ReactNode }> = ({ icon, children }) => (
  <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
    {icon}
    {children}
  </h4>
);

const AssociationPanel: React.FC<{ data: AssociationInspectorData }> = ({ data }) => (
  <>
    {data.status === 'OBSERVED_MATCH' && (
      <div className="flex gap-2 text-[11px] leading-snug text-text-secondary bg-accent-primary/10 border border-accent-primary/30 rounded-md p-2.5">
        <Info className="w-4 h-4 shrink-0 text-accent-primary" aria-hidden="true" />
        <span>
          Observed match: the same normalised identifier appears in evidence of both incidents.
          This is an observation. It is not proof that one group is behind both.
        </span>
      </div>
    )}

    <div>
      <SectionTitle icon={<HelpCircle className="w-3.5 h-3.5 text-accent-primary" aria-hidden="true" />}>
        Why this link exists
      </SectionTitle>
      <p className="text-xs text-text-primary bg-bg-main p-3 rounded-md border border-border-subtle leading-relaxed">
        {data.explanation}
      </p>
    </div>

    <div>
      <SectionTitle>Incidents</SectionTitle>
      <ul className="text-xs space-y-1">
        {data.incidents.map(i => (
          <li key={i.id} className="font-mono text-text-secondary">
            INC-{String(i.id).padStart(4, '0')} · <span className="font-sans text-text-primary">{i.title}</span>
          </li>
        ))}
      </ul>
    </div>

    <div className="bg-bg-elevated/50 p-3 rounded-md border border-border-subtle">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-text-secondary">Matching method</span>
        <span className="font-mono text-text-primary">{data.match_type.replace(/_/g, ' ').toLowerCase()}</span>
      </div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-text-secondary">Base confidence</span>
        <span className="font-mono text-text-primary">{(data.base_confidence * 100).toFixed(0)}%</span>
      </div>
      <div className="flex justify-between text-xs mb-2">
        <span className="text-text-secondary">Adjusted confidence</span>
        <span className="font-mono font-bold text-accent-primary">{(data.adjusted_confidence * 100).toFixed(0)}%</span>
      </div>
      <div className="w-full bg-bg-main h-1.5 rounded-full overflow-hidden" aria-hidden="true">
        <div className="bg-accent-primary h-full" style={{ width: `${Math.round(data.adjusted_confidence * 100)}%` }} />
      </div>
      <p className="text-[10px] text-text-muted mt-1.5">Confidence is a prior for this link, not a probability of fraud.</p>
    </div>

    {data.shared_entities.length > 0 && (
      <div>
        <SectionTitle>Shared identifier</SectionTitle>
        <div className="space-y-2">
          {data.shared_entities.map(ent => (
            <div key={ent.entity_id} className="bg-bg-main p-2.5 rounded border border-border-subtle text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-mono text-text-muted uppercase">{ent.type}</span>
                <span className="text-[10px] font-mono bg-bg-elevated px-1.5 py-0.5 rounded text-accent-secondary">
                  normalised: {ent.norm_method}
                </span>
              </div>
              <div className="font-mono text-text-primary font-medium break-all">{ent.display_value}</div>
            </div>
          ))}
        </div>
      </div>
    )}

    <div>
      <SectionTitle icon={<ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />}>
        Source excerpts ({data.evidence.length})
      </SectionTitle>
      <div className="space-y-2">
        {data.evidence.map((ev, idx) => (
          <div key={idx} className="bg-bg-main p-2.5 rounded border border-border-subtle text-xs space-y-1">
            <div className="flex justify-between text-[10px] text-text-muted font-mono">
              <span>Incident #{ev.incident_id}</span>
              <span>Evidence #{ev.evidence_id}</span>
            </div>
            {/* Evidence is untrusted text: rendered as plain text, never as HTML. */}
            <p className="text-text-secondary italic bg-bg-card p-2 rounded border border-border-subtle/50 break-words">
              “{ev.excerpt}”
            </p>
          </div>
        ))}
      </div>
    </div>

    <div>
      <SectionTitle icon={<AlertTriangle className="w-3.5 h-3.5 text-risk-high" aria-hidden="true" />}>
        Counter-evidence ({data.counter_evidence.length})
      </SectionTitle>
      {data.counter_evidence.length === 0 ? (
        <div className="text-xs text-text-muted bg-bg-main/50 p-3 rounded border border-border-subtle">
          None recorded. The counter-evidence engine arrives in a later phase, so this does not mean the link is uncontested.
        </div>
      ) : (
        <div className="space-y-2">
          {data.counter_evidence.map(ce => (
            <div key={ce.id} className="bg-risk-critical/10 border border-risk-critical/30 p-2.5 rounded text-xs space-y-1">
              <div className="flex items-center justify-between font-mono text-[10px]">
                <span className="font-bold text-risk-critical">{ce.rule_id}</span>
                <span className="text-risk-critical uppercase">{ce.severity}</span>
              </div>
              <div className="text-text-primary font-medium">{ce.observation}</div>
              <div className="text-text-secondary text-[11px]">{ce.explanation}</div>
              <div className="text-risk-critical font-mono text-[10px] text-right">Impact: {ce.confidence_impact}</div>
            </div>
          ))}
        </div>
      )}
    </div>

    <div className="pt-2 border-t border-border-subtle flex flex-wrap justify-between gap-x-4 text-[10px] font-mono text-text-muted">
      <span>Algorithm: {data.versions?.algorithm}</span>
      <span>Extractor: {data.versions?.extractor}</span>
    </div>

    <div className="text-[11px] text-text-muted bg-bg-elevated/40 border border-border-subtle rounded p-2.5">
      <strong className="text-text-secondary">Review state: {data.review.state.replace(/_/g, ' ').toLowerCase()}.</strong>{' '}
      Analyst Accept / Reject / Flag controls arrive in a later phase; no review has been recorded.
    </div>
  </>
);

const NodePanel: React.FC<{ info: NodeInspectorInfo; onOpenIncident: (id: number) => void }> = ({ info, onOpenIncident }) => {
  if (info.kind === 'incident') {
    const d = info.node.details;
    return (
      <>
        <div>
          <SectionTitle>Incident</SectionTitle>
          <p className="text-sm font-semibold text-text-primary">{d.title}</p>
          <dl className="mt-2 text-xs grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-text-secondary">
            <dt className="text-text-muted">Channel</dt><dd className="font-mono">{d.channel}</dd>
            <dt className="text-text-muted">Language</dt><dd className="font-mono">{d.language}</dd>
            <dt className="text-text-muted">Risk indicator</dt>
            <dd className="font-mono">{d.risk_score} / 100 ({info.node.risk_band}) · experimental heuristic</dd>
          </dl>
        </div>
        <button
          type="button"
          onClick={() => onOpenIncident(d.incident_id)}
          className="w-full text-xs font-semibold bg-accent-primary text-bg-main py-2 rounded-md hover:bg-sky-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
        >
          Open investigation detail
        </button>
      </>
    );
  }
  const d = info.node.details;
  return (
    <>
      <div>
        <SectionTitle>Extracted identifier</SectionTitle>
        <div className="bg-bg-main p-2.5 rounded border border-border-subtle text-xs">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-mono text-text-muted uppercase">{d.type}</span>
            <span className="text-[10px] font-mono bg-bg-elevated px-1.5 py-0.5 rounded text-accent-secondary">
              normalised: {d.norm_method}
            </span>
          </div>
          <div className="font-mono text-text-primary font-medium break-all">{d.display_value}</div>
        </div>
      </div>
      <div>
        <SectionTitle>Mentioned in ({info.mentionedBy.length})</SectionTitle>
        <ul className="space-y-1.5">
          {info.mentionedBy.map(n => (
            <li key={n.id} className="flex items-center justify-between gap-2 text-xs bg-bg-main border border-border-subtle rounded p-2">
              <span className="text-text-primary truncate">{n.details.title}</span>
              <button
                type="button"
                onClick={() => onOpenIncident(n.details.incident_id)}
                className="text-accent-primary hover:underline shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary rounded"
              >
                Open
              </button>
            </li>
          ))}
        </ul>
        {info.mentionedBy.length >= 2 && info.node.type !== 'organisation' && (
          <p className="text-[11px] text-text-muted mt-2">
            The same normalised value appears in {info.mentionedBy.length} incidents. That is an observation, not proof of a shared origin.
          </p>
        )}
      </div>
    </>
  );
};

export const InspectorShell: React.FC<InspectorShellProps> = ({ association, node, isOpen, onClose, onOpenIncident }) => {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    closeRef.current?.focus();
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  if (!isOpen || (!association && !node)) return null;

  const heading = association ? association.status.replace(/_/g, ' ') : node?.kind === 'incident' ? 'INCIDENT' : 'IDENTIFIER';

  return (
    <aside
      role="complementary"
      aria-label="Evidence inspector"
      className="w-96 max-w-[90vw] bg-bg-card border-l border-border-subtle h-full flex flex-col z-20 shadow-xl overflow-hidden"
    >
      <div className="p-4 border-b border-border-subtle flex items-center justify-between bg-bg-elevated/40">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono uppercase bg-accent-primary/20 text-accent-primary px-2 py-0.5 rounded border border-accent-primary/30">
            {heading}
          </span>
          {association && <span className="text-xs text-text-muted">#{association.id}</span>}
        </div>
        <button
          ref={closeRef}
          type="button"
          onClick={onClose}
          aria-label="Close inspector (Esc)"
          className="p-1 text-text-muted hover:text-text-primary rounded hover:bg-bg-elevated transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
        >
          <X className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5 text-sm">
        {association ? <AssociationPanel data={association} /> : node ? <NodePanel info={node} onOpenIncident={onOpenIncident} /> : null}
      </div>
    </aside>
  );
};
