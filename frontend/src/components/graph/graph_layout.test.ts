import { describe, it, expect } from 'vitest';
import {
  buildFlowElements, associationIdOf, edgeLabel, edgeVisual, incidentsMentioning, layoutNodes, nodeKind,
} from './graph_layout';
import type { GraphData } from '../../types';

// Shape matches what GET /api/v1/graph returns for the seed scenario (two incidents share one UPI, one is isolated).
const graph: GraphData = {
  nodes: [
    { id: 'incident_1', type: 'incident', label: 'INC-0001', risk_band: 'HIGH', details: { incident_id: 1, title: 'A', risk_score: 60 } },
    { id: 'incident_2', type: 'incident', label: 'INC-0002', risk_band: 'HIGH', details: { incident_id: 2, title: 'B', risk_score: 60 } },
    { id: 'incident_3', type: 'incident', label: 'INC-0003', risk_band: 'LOW', details: { incident_id: 3, title: 'C', risk_score: 0 } },
    { id: 'entity_1', type: 'upi_handle', label: 've•••@okhdfcbank', details: { type: 'UPI_HANDLE' } },
    { id: 'entity_2', type: 'organisation', label: 'Central Bureau of Investigation', details: { type: 'ORGANISATION' } },
  ],
  edges: [
    { id: 'struct_1_1', source: 'incident_1', target: 'entity_1', type: 'structural' },
    { id: 'struct_2_1', source: 'incident_2', target: 'entity_1', type: 'structural' },
    { id: 'struct_1_2', source: 'incident_1', target: 'entity_2', type: 'structural' },
    { id: 'assoc_1', source: 'incident_1', target: 'incident_2', type: 'OBSERVED_MATCH', status: 'OBSERVED_MATCH', label: 'observed match', confidence: 0.75, explanation: 'x' },
  ],
};

describe('graph layout and edge semantics', () => {
  it('labels an observed match "observed match" and draws it solid, thin and sky-blue', () => {
    const { edges } = buildFlowElements(graph);
    const assoc = edges.find(e => e.id === 'assoc_1')!;
    expect(assoc.label).toBe('observed match');
    expect(assoc.style?.stroke).toBe('#38BDF8');
    expect(assoc.style?.strokeDasharray).toBeUndefined();
    expect(assoc.style?.strokeWidth).toBeLessThan(2.5);
  });

  it('never labels or styles an observed match as a campaign', () => {
    const { edges } = buildFlowElements(graph);
    for (const e of edges) expect(String(e.label ?? '').toLowerCase()).not.toContain('campaign');
  });

  it('keeps the unrelated incident without any association edge', () => {
    const { edges } = buildFlowElements(graph);
    const touching3 = edges.filter(e => e.source === 'incident_3' || e.target === 'incident_3');
    expect(touching3).toEqual([]);
  });

  it('has one distinct visual per association state (blueprint §12.5)', () => {
    const observed = edgeVisual('OBSERVED_MATCH');
    const candidate = edgeVisual('CANDIDATE_ASSOCIATION');
    const verified = edgeVisual('ANALYST_VERIFIED_ASSOCIATION');
    const disputed = edgeVisual('DISPUTED_ASSOCIATION');
    const rejected = edgeVisual('REJECTED_ASSOCIATION');
    expect(candidate.strokeDasharray).toBeTruthy();
    expect(disputed.strokeDasharray).toBeTruthy();
    expect(verified.strokeWidth).toBeGreaterThan(observed.strokeWidth);
    expect(rejected.opacity).toBeLessThan(1);
    expect(new Set([observed.stroke, candidate.stroke, verified.stroke, disputed.stroke, rejected.stroke]).size).toBe(5);
  });

  it('derives edge labels from status, including candidate similarity', () => {
    expect(edgeLabel({ id: 'assoc_2', source: 'a', target: 'b', type: 'CANDIDATE_ASSOCIATION', status: 'CANDIDATE_ASSOCIATION', similarity: 0.812 })).toBe('81%');
    expect(edgeLabel({ id: 'assoc_3', source: 'a', target: 'b', type: 'DISPUTED_ASSOCIATION', status: 'DISPUTED_ASSOCIATION' })).toContain('disputed');
  });

  it('parses association ids and ignores structural edges', () => {
    expect(associationIdOf(graph.edges[3])).toBe(1);
    expect(associationIdOf(graph.edges[0])).toBeNull();
  });

  it('filters association edges by status but keeps structural edges (or hides them on request)', () => {
    const none = buildFlowElements(graph, { status: 'CANDIDATE_ASSOCIATION', showStructural: true });
    expect(none.edges.filter(e => e.id.startsWith('assoc_'))).toHaveLength(0);
    expect(none.edges.filter(e => e.id.startsWith('struct_'))).toHaveLength(3);
    const hidden = buildFlowElements(graph, { status: 'ALL', showStructural: false });
    expect(hidden.edges.map(e => e.id)).toEqual(['assoc_1']);
  });

  it('places an identifier shared by two incidents above and between them, and a private one below its incident', () => {
    const nodes = layoutNodes(graph);
    const byId = Object.fromEntries(nodes.map(n => [n.id, n.position]));
    expect(byId.entity_1.y).toBeLessThan(byId.incident_1.y);
    expect(byId.entity_1.x).toBeCloseTo((byId.incident_1.x + byId.incident_2.x) / 2);
    expect(byId.entity_2.y).toBeGreaterThan(byId.incident_1.y);
  });

  it('is deterministic', () => {
    expect(layoutNodes(graph)).toEqual(layoutNodes(graph));
  });

  it('classifies node kinds and lists the incidents that mention an entity', () => {
    expect(nodeKind('UPI_HANDLE')).toBe('upi_handle');
    expect(nodeKind('mystery')).toBe('other');
    expect(incidentsMentioning(graph, 'entity_1').map(n => n.id).sort()).toEqual(['incident_1', 'incident_2']);
  });

  it('handles an empty graph', () => {
    expect(buildFlowElements({ nodes: [], edges: [] })).toEqual({ nodes: [], edges: [] });
  });
});
