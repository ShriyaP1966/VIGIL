import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ReactFlow, Background, Controls, type Edge, type Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Network, Table, AlertCircle, RefreshCw } from 'lucide-react';
import { apiClient } from '../services/api/client';
import { GraphData, NodeInspectorInfo } from '../types';
import { VigilNode } from '../components/graph/VigilNode';
import {
  buildFlowElements,
  associationIdOf,
  edgeLabel,
  incidentsMentioning,
  isAssociationEdge,
  EDGE_COLORS,
  type VigilNodeData,
} from '../components/graph/graph_layout';

const nodeTypes = { vigil: VigilNode };

const STATUS_FILTERS = ['ALL', 'OBSERVED_MATCH', 'CANDIDATE_ASSOCIATION', 'DISPUTED_ASSOCIATION'] as const;

interface IntelligenceGraphProps {
  /** Changes after an analyst review so the graph re-reads the associations. */
  refreshKey: number;
  onInspectAssociation: (assocId: number) => void;
  onInspectNode: (info: NodeInspectorInfo) => void;
  onSelectIncident: (id: number) => void;
}

export const IntelligenceGraph: React.FC<IntelligenceGraphProps> = ({
  refreshKey,
  onInspectAssociation,
  onInspectNode,
  onSelectIncident,
}) => {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tableView, setTableView] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [showStructural, setShowStructural] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setGraphData(await apiClient.getGraph());
    } catch (e: any) {
      setError(e?.message || 'Failed to load the graph.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load, refreshKey]);

  const { nodes, edges } = useMemo(
    () => (graphData ? buildFlowElements(graphData, { status: statusFilter, showStructural }) : { nodes: [], edges: [] }),
    [graphData, statusFilter, showStructural]
  );

  const associationEdges = useMemo(
    () => (graphData?.edges ?? []).filter(isAssociationEdge)
      .filter(e => statusFilter === 'ALL' || (e.status ?? e.type) === statusFilter),
    [graphData, statusFilter]
  );

  const handleEdgeClick = (_: React.MouseEvent, edge: Edge) => {
    const id = (edge.data as { associationId?: number } | undefined)?.associationId;
    if (id != null) onInspectAssociation(id);
  };

  const handleNodeClick = (_: React.MouseEvent, node: Node) => {
    if (!graphData) return;
    const data = node.data as VigilNodeData;
    if (data.kind === 'incident') onInspectNode({ kind: 'incident', node: data.graphNode });
    else onInspectNode({ kind: 'entity', node: data.graphNode, mentionedBy: incidentsMentioning(graphData, node.id) });
  };

  const hasIncidents = (graphData?.nodes ?? []).some(n => n.type === 'incident');

  return (
    <div className="flex flex-col h-full min-h-[560px] bg-bg-main">
      {/* Toolbar */}
      <div className="bg-bg-sidebar border-b border-border-subtle flex flex-wrap items-center justify-between gap-3 px-6 py-3">
        <div className="flex flex-wrap items-center gap-4">
          <h1 className="flex items-center gap-2 text-sm font-semibold text-text-primary">
            <Network className="w-4 h-4 text-accent-primary" aria-hidden="true" />
            Cross-Channel Intelligence Graph
          </h1>
          <div className="flex flex-wrap items-center gap-2 text-xs" role="group" aria-label="Filter association edges by status">
            <span className="text-text-muted">Links:</span>
            {STATUS_FILTERS.map(t => (
              <button
                key={t}
                type="button"
                aria-pressed={statusFilter === t}
                onClick={() => setStatusFilter(t)}
                className={`px-2.5 py-1 rounded text-[11px] font-mono transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary ${
                  statusFilter === t
                    ? 'bg-accent-primary text-bg-main font-bold'
                    : 'bg-bg-card hover:bg-bg-elevated text-text-secondary border border-border-subtle'
                }`}
              >
                {t === 'ALL' ? 'All links' : t.replace(/_/g, ' ').toLowerCase()}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-1.5 text-xs text-text-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={showStructural}
              onChange={e => setShowStructural(e.target.checked)}
              className="accent-sky-400"
            />
            Show identifier links
          </label>
        </div>

        <button
          type="button"
          onClick={() => setTableView(v => !v)}
          className="flex items-center gap-1.5 bg-bg-card hover:bg-bg-elevated text-text-secondary px-3 py-1.5 rounded text-xs border border-border-subtle transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
        >
          <Table className="w-3.5 h-3.5" aria-hidden="true" />
          <span>{tableView ? 'Canvas view' : 'Table view'}</span>
        </button>
      </div>

      {/* Legend (wording required by blueprint §12.5) */}
      <div className="bg-bg-elevated/40 border-b border-border-subtle px-6 py-2 flex flex-wrap items-center gap-x-6 gap-y-1 text-xs text-text-muted">
        <span className="flex items-center gap-2">
          <span className="w-5 h-0.5" style={{ background: EDGE_COLORS.OBSERVED_MATCH }} aria-hidden="true" />
          <span><strong className="text-text-primary">Solid blue = identifier observed in both incidents.</strong> It is not proof of one campaign.</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="w-5 border-t-2 border-dashed" style={{ borderColor: EDGE_COLORS.CANDIDATE_ASSOCIATION }} aria-hidden="true" />
          <span><strong className="text-text-primary">Dashed amber = candidate.</strong> Similar script, no shared identifier; the label is the similarity.</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="w-5 border-t-2 border-dashed" style={{ borderColor: EDGE_COLORS.DISPUTED_ASSOCIATION }} aria-hidden="true" />
          Dashed red = disputed (flagged by an analyst)
        </span>
        <span className="flex items-center gap-2">
          <span className="w-5 h-1 rounded" style={{ background: EDGE_COLORS.ANALYST_VERIFIED_ASSOCIATION }} aria-hidden="true" />
          Thick teal = accepted by an analyst
        </span>
      </div>

      {/* Body */}
      <div className="flex-1 relative min-h-[420px]">
        {loading ? (
          <div className="h-full flex items-center justify-center text-sm font-mono text-text-muted animate-pulse" role="status">
            Loading graph…
          </div>
        ) : error ? (
          <div className="h-full flex flex-col items-center justify-center gap-3 p-8 text-center" role="alert">
            <AlertCircle className="w-6 h-6 text-risk-critical" aria-hidden="true" />
            <p className="text-sm text-text-secondary max-w-md">{error}</p>
            <button
              type="button"
              onClick={() => void load()}
              className="flex items-center gap-1.5 text-xs bg-bg-card border border-border-subtle px-3 py-1.5 rounded text-text-primary hover:bg-bg-elevated"
            >
              <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" /> Retry
            </button>
          </div>
        ) : !hasIncidents ? (
          <div className="h-full flex items-center justify-center p-8 text-sm text-text-muted text-center">
            No incidents yet. Create an investigation to see identifiers and observed matches here.
          </div>
        ) : tableView ? (
          <div className="p-6 overflow-auto h-full">
            <div className="bg-bg-card border border-border-subtle rounded-lg overflow-hidden max-w-6xl mx-auto">
              <table className="w-full text-left text-xs">
                <caption className="sr-only">Association links between incidents</caption>
                <thead className="bg-bg-elevated text-text-muted uppercase font-mono text-[10px] border-b border-border-subtle">
                  <tr>
                    <th scope="col" className="p-3">Status</th>
                    <th scope="col" className="p-3">Incidents</th>
                    <th scope="col" className="p-3">Label</th>
                    <th scope="col" className="p-3">Confidence</th>
                    <th scope="col" className="p-3">Why this link exists</th>
                    <th scope="col" className="p-3 text-right">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {associationEdges.length === 0 && (
                    <tr><td colSpan={6} className="p-4 text-center text-text-muted">No association links match this filter.</td></tr>
                  )}
                  {associationEdges.map(edge => {
                    const id = associationIdOf(edge);
                    return (
                      <tr key={edge.id} className="hover:bg-bg-elevated/30">
                        <td className="p-3 font-mono text-accent-primary">{(edge.status ?? edge.type).replace(/_/g, ' ')}</td>
                        <td className="p-3 font-mono text-text-primary">
                          {edge.source.replace('incident_', 'INC-')} ↔ {edge.target.replace('incident_', 'INC-')}
                        </td>
                        <td className="p-3 text-text-secondary">{edgeLabel(edge)}</td>
                        <td className="p-3 font-mono text-text-secondary">
                          {edge.confidence != null ? `${Math.round(edge.confidence * 100)}%` : '—'}
                        </td>
                        <td className="p-3 text-text-secondary">{edge.explanation}</td>
                        <td className="p-3 text-right">
                          {id != null && (
                            <button
                              type="button"
                              onClick={() => onInspectAssociation(id)}
                              className="text-accent-primary hover:underline font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary rounded"
                            >
                              Inspect
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div className="px-3 py-2 border-t border-border-subtle text-[11px] text-text-muted">
                Incidents without an association link are shown on the canvas view and on the Overview page.
              </div>
            </div>
          </div>
        ) : (
          <>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onEdgeClick={handleEdgeClick}
              onNodeClick={handleNodeClick}
              onNodeDoubleClick={(_, node) => {
                const data = node.data as VigilNodeData;
                if (data.kind === 'incident') onSelectIncident(data.graphNode.details.incident_id);
              }}
              fitView
              fitViewOptions={{ padding: 0.25 }}
              minZoom={0.3}
              maxZoom={1.6}
              nodesConnectable={false}
              colorMode="dark"
              proOptions={{ hideAttribution: true }}
              aria-label="Intelligence graph. Click a node or link to inspect it; use Table view for a keyboard-friendly list."
            >
              <Background gap={24} color="#1E293B" />
              <Controls showInteractive={false} />
            </ReactFlow>
            <p className="absolute bottom-3 right-4 text-[11px] text-text-muted bg-bg-main/80 px-2 py-1 rounded pointer-events-none">
              Click a link or node to inspect · double-click an incident to open it
            </p>
          </>
        )}
      </div>
    </div>
  );
};
