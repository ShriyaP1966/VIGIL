export type ViewMode = 
  | 'overview' 
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

export interface EvidenceItem {
  id: number;
  type: string;
  original_text: string;
  normalised_text: string;
  sha256: string;
  provenance: string;
  timestamp: string;
  entities: EntityMention[];
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
  }>;
  counter_evidence: Array<{
    id: number;
    rule_id: string;
    kind: string;
    severity: 'LOW' | 'MEDIUM' | 'HIGH';
    observation: string;
    confidence_impact: number;
    explanation: string;
  }>;
  explanation: string;
  versions: Record<string, string>;
  review: {
    state: string;
    history: Array<any>;
  };
}
