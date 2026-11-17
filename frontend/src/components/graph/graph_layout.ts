import type { Edge, Node } from '@xyflow/react';
import type { AssociationStatus, GraphData, GraphEdge, GraphNode, RiskBand } from '../../types';

/** Blueprint §12.5 graph semantics, implemented as pure functions so they can be unit-tested. */

export type NodeKind = 'incident' | 'phone' | 'upi_handle' | 'email' | 'domain' | 'url' | 'organisation' | 'other';

export interface VigilNodeData extends Record<string, unknown> {
  kind: NodeKind;
  label: string;
  riskBand?: RiskBand;
  graphNode: GraphNode;
}

export const RISK_COLORS: Record<RiskBand, string> = {
  LOW: '#22C55E',
  ELEVATED: '#EAB308',
  HIGH: '#F59E0B',
  CRITICAL: '#EF4444',
};

export const EDGE_COLORS = {
  structural: '#475569',
  OBSERVED_MATCH: '#38BDF8',
  CANDIDATE_ASSOCIATION: '#EAB308',
  ANALYST_VERIFIED_ASSOCIATION: '#2DD4BF',
  DISPUTED_ASSOCIATION: '#EF4444',
  REJECTED_ASSOCIATION: '#64748B',
} as const;

const KINDS: NodeKind[] = ['incident', 'phone', 'upi_handle', 'email', 'domain', 'url', 'organisation'];

export function nodeKind(type: string): NodeKind {
  const t = type.toLowerCase();
  return (KINDS as string[]).includes(t) ? (t as NodeKind) : 'other';
}

export function isAssociationEdge(edge: GraphEdge): boolean {
  return edge.id.startsWith('assoc_');
}

export function associationIdOf(edge: GraphEdge): number | null {
  if (!isAssociationEdge(edge)) return null;
  const n = parseInt(edge.id.slice('assoc_'.length), 10);
  return Number.isNaN(n) ? null : n;
}

/** Label shown on an association edge, derived from its status (never from invented data). */
export function edgeLabel(edge: GraphEdge): string {
  switch (edge.status ?? edge.type) {
    case 'OBSERVED_MATCH':
      return 'observed match';
    case 'CANDIDATE_ASSOCIATION':
      return edge.similarity != null ? `${Math.round(edge.similarity * 100)}%` : 'candidate';
    case 'ANALYST_VERIFIED_ASSOCIATION':
      return '✓ analyst verified';
    case 'DISPUTED_ASSOCIATION':
      return '⚠ disputed';
    case 'REJECTED_ASSOCIATION':
      return 'rejected';
    default:
      return edge.label ?? '';
  }
}

export interface EdgeVisual {
  stroke: string;
  strokeWidth: number;
  strokeDasharray?: string;
  opacity?: number;
}

/** Visual style per association state: solid thin blue / dashed amber / thick teal / dashed red / faded grey. */
export function edgeVisual(status: string): EdgeVisual {
  switch (status as AssociationStatus | 'structural') {
    case 'OBSERVED_MATCH':
      return { stroke: EDGE_COLORS.OBSERVED_MATCH, strokeWidth: 1.5 };
    case 'CANDIDATE_ASSOCIATION':
      return { stroke: EDGE_COLORS.CANDIDATE_ASSOCIATION, strokeWidth: 1.5, strokeDasharray: '6 4' };
    case 'ANALYST_VERIFIED_ASSOCIATION':
      return { stroke: EDGE_COLORS.ANALYST_VERIFIED_ASSOCIATION, strokeWidth: 3.5 };
    case 'DISPUTED_ASSOCIATION':
      return { stroke: EDGE_COLORS.DISPUTED_ASSOCIATION, strokeWidth: 1.5, strokeDasharray: '6 4' };
    case 'REJECTED_ASSOCIATION':
      return { stroke: EDGE_COLORS.REJECTED_ASSOCIATION, strokeWidth: 1, opacity: 0.35 };
    default:
      return { stroke: EDGE_COLORS.structural, strokeWidth: 1 };
  }
}

const X_STEP = 340;
const SHARED_Y = -190;
const INCIDENT_Y = 60;
const PRIVATE_Y = 300;
const ENTITY_SPREAD = 170;

/**
 * Deterministic layout: incidents in a row; identifiers mentioned by 2+ incidents sit above,
 * centred over the incidents that mention them; identifiers of a single incident sit below it.
 */
export function layoutNodes(graph: GraphData): Node<VigilNodeData>[] {
  const incidents = graph.nodes
    .filter(n => n.type === 'incident')
    .sort((a, b) => (a.details.incident_id ?? 0) - (b.details.incident_id ?? 0));
  const incidentX = new Map<string, number>();
  incidents.forEach((n, i) => incidentX.set(n.id, i * X_STEP));

  // entity id -> incident ids that mention it
  const mentionedBy = new Map<string, string[]>();
  for (const e of graph.edges) {
    if (e.type !== 'structural') continue;
    const list = mentionedBy.get(e.target) ?? [];
    if (!list.includes(e.source)) list.push(e.source);
    mentionedBy.set(e.target, list);
  }

  const result: Node<VigilNodeData>[] = incidents.map(n => ({
    id: n.id,
    type: 'vigil',
    position: { x: incidentX.get(n.id)!, y: INCIDENT_Y },
    data: { kind: 'incident', label: n.label, riskBand: n.risk_band, graphNode: n },
  }));

  const entities = graph.nodes.filter(n => n.type !== 'incident').sort((a, b) => a.id.localeCompare(b.id));
  const sharedSlots = new Map<number, number>(); // rounded x -> count already placed
  const privateSlots = new Map<string, number>(); // incident id -> count already placed

  for (const n of entities) {
    const owners = mentionedBy.get(n.id) ?? [];
    const ownerXs = owners.map(o => incidentX.get(o)).filter((x): x is number => x !== undefined);
    let position: { x: number; y: number };
    if (ownerXs.length >= 2) {
      const centre = ownerXs.reduce((a, b) => a + b, 0) / ownerXs.length;
      const slot = sharedSlots.get(centre) ?? 0;
      sharedSlots.set(centre, slot + 1);
      position = { x: centre + slot * ENTITY_SPREAD, y: SHARED_Y };
    } else if (ownerXs.length === 1) {
      const slot = privateSlots.get(owners[0]) ?? 0;
      privateSlots.set(owners[0], slot + 1);
      position = { x: ownerXs[0] + (slot - 0.5) * ENTITY_SPREAD, y: PRIVATE_Y };
    } else {
      position = { x: -X_STEP, y: PRIVATE_Y };
    }
    result.push({
      id: n.id,
      type: 'vigil',
      position,
      data: { kind: nodeKind(n.type), label: n.label, graphNode: n },
    });
  }
  return result;
}

export interface FlowFilter {
  /** Association status to keep, or 'ALL'. Structural edges are always kept. */
  status: string;
  showStructural: boolean;
}

export function buildFlowElements(
  graph: GraphData,
  filter: FlowFilter = { status: 'ALL', showStructural: true }
): { nodes: Node<VigilNodeData>[]; edges: Edge[] } {
  const nodes = layoutNodes(graph);
  const edges: Edge[] = [];
  for (const e of graph.edges) {
    const assoc = isAssociationEdge(e);
    if (!assoc) {
      if (!filter.showStructural) continue;
      edges.push({
        id: e.id,
        source: e.source,
        target: e.target,
        style: edgeVisual('structural'),
        selectable: false,
        focusable: false,
      });
      continue;
    }
    const status = e.status ?? e.type;
    if (filter.status !== 'ALL' && status !== filter.status) continue;
    edges.push({
      id: e.id,
      source: e.source,
      target: e.target,
      label: edgeLabel(e),
      style: edgeVisual(status),
      labelStyle: { fill: '#F8FAFC', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' },
      labelBgStyle: { fill: '#111827', fillOpacity: 0.95 },
      labelBgPadding: [6, 3],
      labelBgBorderRadius: 4,
      interactionWidth: 24,
      focusable: true,
      ariaLabel: `${status.replace(/_/g, ' ').toLowerCase()} between ${e.source.replace('incident_', 'incident ')} and ${e.target.replace('incident_', 'incident ')}. Press Enter to inspect.`,
      data: { status, associationId: associationIdOf(e) },
    });
  }
  return { nodes, edges };
}

/** Plain-language list of the incidents that mention an entity node, for the node inspector. */
export function incidentsMentioning(graph: GraphData, entityNodeId: string): GraphNode[] {
  const ids = new Set(graph.edges.filter(e => e.type === 'structural' && e.target === entityNodeId).map(e => e.source));
  return graph.nodes.filter(n => ids.has(n.id));
}
