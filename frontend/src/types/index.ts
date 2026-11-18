export type ViewMode = 
  | 'overview' 
  | 'investigations'
  | 'new_investigation'
  | 'investigation_detail'
  | 'graph' 
  | 'campaigns' 
  | 'scenario_lab' 
  | 'simulated_live_call' 
  | 'reports' 
  | 'settings';

export type AssociationStatus = 
  | 'OBSERVED_MATCH' 
  | 'CANDIDATE_ASSOCIATION' 
  | 'ANALYST_VERIFIED_ASSOCIATION' 
  | 'DISPUTED_ASSOCIATION' 
  | 'REJECTED_ASSOCIATION';

export type RiskBand = 'LOW' | 'ELEVATED' | 'HIGH' | 'CRITICAL';

export interface EntityMention {
  id: number;
  type: string;
  canonical_value: string;
  display_value: string;
  norm_method: string;
  span_start: number;
  span_end: number;
  confidence: number;
}

/** A tactic that fired on part of an utterance (span relative to the utterance text). */
export interface TacticSpan {
  label: string;
  start: number;
  end: number;
  confidence: number;
}

/** Text flagged as a prompt-injection / manipulation attempt (span relative to the utterance text). */
export interface InjectionSpan {
  rule_id: string;
  start: number;
  end: number;
}

export interface UtteranceView {
  id: number;
  idx: number;
  speaker: string;
  text: string;
  t_start_sec?: number | null;
  language?: string | null;
  tactics: TacticSpan[];
  injection_spans: InjectionSpan[];
}

export interface EvidenceItem {
  id: number;
  type: string;
  original_text: string;
  normalised_text: string;
  sha256: string;
  provenance: string;
  timestamp: string;
  entities: EntityMention[];
  utterances?: UtteranceView[];
}

export interface RiskContribution {
  factor: string;
  evidence_ref?: string;
  rule_version: string;
  contribution: number;
  effect: 'SUPPORTING' | 'MITIGATING';
  explanation: string;
}

export interface IncidentAnalysis {
  id: number;
  incident_id: number;
  extractor: string;
  extractor_version: string;
  fallback_used: boolean;
  risk_score: number;
  risk_band: RiskBand;
  risk_version: string;
  injection_flags: string[];
  fingerprint: Record<string, any>;
  contributions: RiskContribution[];
}

/** Secrets removed before storage, by kind. Counts only; the values are never kept (blueprint §5.5). */
export interface RedactionSummary {
  kind: string;
  count: number;
}

export interface IncidentDetail {
  id: number;
  title: string;
  source_channel: string;
  language: string;
  status: string;
  is_synthetic: boolean;
  created_at: string;
  evidence_items: EvidenceItem[];
  analysis?: IncidentAnalysis;
  redactions?: RedactionSummary[];
}

export interface IncidentListItem {
  id: number;
  title: string;
  source_channel: string;
  language: string;
  status: string;
  risk_score?: number;
  risk_band?: RiskBand;
  created_at: string;
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  risk_band?: RiskBand;
  details: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  label?: string;
  similarity?: number;
  confidence?: number;
  status?: AssociationStatus;
  explanation?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export type ReviewDecision = 'ACCEPT' | 'REJECT' | 'FLAG';

export type CampaignStatus = 'HYPOTHESIS_UNREVIEWED' | 'ACCEPTED_BY_ANALYST' | 'REJECTED_BY_ANALYST' | 'FLAGGED';

/** A campaign HYPOTHESIS. It is never called "confirmed", even after an analyst accepts it. */
export interface CampaignListItem {
  id: number;
  hypothesis_title: string;
  status: CampaignStatus;
  status_label: string;
  confidence: number;
  member_count: number;
  basis_counts: Record<string, number>;
  weakest_link_association_id?: number | null;
  incident_ids: number[];
  counter_evidence_count?: number;
  highest_severity?: 'LOW' | 'MEDIUM' | 'HIGH' | null;
}

/** One counter-evidence finding on a link inside a hypothesis (aggregated view). */
export interface CampaignFinding {
  association_id: number;
  incident_a_id: number;
  incident_b_id: number;
  link_status: AssociationStatus;
  rule_id: string;
  kind: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  observation: string;
  explanation: string;
  confidence_impact: number;
  rule_version?: string;
  evidence_refs?: Array<{ evidence_id?: number; incident_id?: number; excerpt?: string; stage?: string; entity?: string }>;
}

export interface CampaignMemberView {
  incident_id: number;
  title: string;
  source_channel: string;
  language: string;
  risk_score: number;
  risk_band: RiskBand;
  membership_basis: 'OBSERVED' | 'CANDIDATE' | 'ANALYST';
  stage_sequence: string[];
  institution_class: string;
  payment_channel: string;
}

export interface CampaignLink {
  id: number;
  incident_a_id: number;
  incident_b_id: number;
  status: AssociationStatus;
  match_type: string;
  similarity?: number | null;
  adjusted_confidence: number;
  explanation: string;
  is_weakest: boolean;
}

export interface CampaignDetail extends CampaignListItem {
  members: CampaignMemberView[];
  links: CampaignLink[];
  excluded_links: CampaignLink[];
  shared_indicators: Array<{ type: string; display_value: string; incident_ids: number[] }>;
  counter_evidence: CampaignFinding[];
  counter_evidence_summary?: Record<string, number>;
  review: { state: string; history: Array<{ id: number; decision: string; note?: string | null; previous_status: string; new_status: string; created_at: string }> };
  disclaimer: string;
  versions: Record<string, string>;
}

/** What the inspector shows when a graph node (not an association edge) is selected. */
export type NodeInspectorInfo =
  | { kind: 'incident'; node: GraphNode }
  | { kind: 'entity'; node: GraphNode; mentionedBy: GraphNode[] };

export interface AssociationInspectorData {
  id: number;
  status: AssociationStatus;
  match_type: string;
  incidents: { id: number; title: string }[];
  similarity?: number;
  base_confidence: number;
  adjusted_confidence: number;
  component_scores: Record<string, number>;
  shared_entities: Array<{
    entity_id: number;
    type: string;
    canonical_value: string;
    display_value: string;
    norm_method: string;
  }>;
  evidence: Array<{
    evidence_id: number;
    incident_id: number;
    entity_id?: number;
    entity_type?: string;
    canonical_value?: string;
    display_value?: string;
    excerpt: string;
    /** Playbook stage this excerpt shows (behavioural associations only). */
    stage?: string;
  }>;
  counter_evidence: Array<{
    id: number;
    rule_id: string;
    kind: string;
    severity: 'LOW' | 'MEDIUM' | 'HIGH';
    observation: string;
    confidence_impact: number;
    explanation: string;
    rule_version?: string;
    evidence_refs?: Array<{ evidence_id?: number; incident_id?: number; excerpt?: string; stage?: string; entity?: string }>;
  }>;
  /** Why the link is disputed: by a counter-evidence rule or by an analyst's flag. */
  dispute?: { source?: 'RULE' | 'ANALYST' | null; rules?: string[] };
  explanation: string;
  versions: Record<string, string>;
  review: {
    state: string;
    history: Array<any>;
  };
}

// ---------------------------------------------------------------------------------------------
// Scenario Lab, reports and the simulated call (Phase 6)
// ---------------------------------------------------------------------------------------------

export interface ScenarioInfo {
  name: string;
  title: string;
  category: 'positive' | 'negative' | 'ambiguous' | 'decoy' | 'counter_evidence' | 'injection';
  description: string;
  rotation_adjustable: boolean;
  default_rotation: number | null;
}

/** passed = null marks an informational line: the scenario states no requirement there. */
export interface ScenarioCheck {
  name: string;
  expected: string;
  actual: unknown;
  passed: boolean | null;
}

export interface ScenarioRun {
  name: string;
  title: string;
  category: ScenarioInfo['category'];
  description: string;
  rotation: number | null;
  seed: number;
  incidents: Array<{
    id: string; channel: string; language: string; excerpt: string; detected_labels: string[];
    risk: { score: number; band: RiskBand } | null; injection_flags: string[];
    generator_stage_sequence: string[] | null;
  }>;
  links: Array<{ a: string; b: string; status: string; match_type: string; shared: string[]; confidence: number }>;
  hypotheses: Array<{ members: string[]; confidence: number; status: string; bases: string[] }>;
  summary: { observed_links: number; candidate_links: number; disputed_links: number; hypotheses: number };
  checks: ScenarioCheck[];
  matches_expected: boolean;
  disclaimer: string;
}

export interface ReportAssociationRow {
  association_id: number; other_incident_id: number; other_incident_title: string | null; status: string;
  match_type: string; confidence: number; base_confidence: number; explanation: string;
  shared_identifiers: Array<{ type: string; display_value: string }>; algorithm_version: string;
}

export interface IncidentReport {
  report_version: string;
  synthetic: boolean;
  incident: { id: number; title: string; source_channel: string; language: string; status: string; created_at: string | null };
  observed_facts: {
    evidence: Array<{ id: number; type: string; sha256: string; provenance: string; characters: number }>;
    identifiers: Array<{ type: string; display_value: string; mentions: number }>;
    observed_matches: ReportAssociationRow[];
  };
  model_inferences: {
    stage_sequence: string[];
    institution_class: string | null;
    payment_channel: string | null;
    tactics: Array<{ label: string; stage: string | null; count: number; max_confidence: number; excerpts: Array<{ utterance_idx: number; text: string }> }>;
    risk: {
      score: number; band: RiskBand; version: string; note: string; injection_flags: string[];
      contributions: Array<{ factor: string; effect: string; contribution: number; explanation: string; rule_version: string }>;
    } | null;
    behavioural_candidates: ReportAssociationRow[];
    campaign_hypotheses: Array<{ id: number; title: string; status: string; confidence: number }>;
  };
  analyst_actions: Array<{
    target_type: string; target_id: number; decision: string; note: string | null;
    previous_status: string; new_status: string; recorded_at: string | null;
  }>;
  counter_evidence: {
    findings: Array<{
      association_id: number; rule_id: string; kind: string; severity: string; observation: string;
      explanation: string; confidence_impact: number; rule_version: string;
    }>;
    disputed_or_rejected_links: ReportAssociationRow[];
  };
  limitations: string[];
}

export interface SimulationScript {
  name: string;
  title: string;
  language: string;
  description: string;
  turns: number;
  utterances: Array<{ speaker: string; text: string }>;
}

export interface SimulationFrame {
  turns: number;
  stages: Array<{ stage: string; reached: boolean; first_turn: number | null }>;
  risk: { score: number; band: RiskBand; version: string | null; contributions: RiskContribution[] };
  utterances: Array<{
    idx: number; speaker: string; text: string; tactics: TacticSpan[]; injection_spans: InjectionSpan[];
  }>;
  injection_flags: string[];
  guidance: { level: RiskBand; en: string[]; hi: string[] };
  disclaimer: string;
}
