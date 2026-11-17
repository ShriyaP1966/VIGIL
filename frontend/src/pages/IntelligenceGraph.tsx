import React, { useEffect, useState } from 'react';
import { 
  Network, 
  Filter, 
  Layers, 
  AlertTriangle, 
  CheckCircle, 
  Table, 
  Eye, 
  Info,
  Maximize2
} from 'lucide-react';
import { apiClient } from '../services/api/client';
import { GraphData, GraphNode, GraphEdge, AssociationInspectorData } from '../types';

interface IntelligenceGraphProps {
  onInspectAssociation: (assocId: number) => void;
  onSelectIncident: (id: number) => void;
}

export const IntelligenceGraph: React.FC<IntelligenceGraphProps> = ({ 
  onInspectAssociation, 
  onSelectIncident 
}) => {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [tableView, setTableView] = useState(false);
  const [filterType, setFilterType] = useState<string>('ALL');

  useEffect(() => {
    async function load() {
      try {
        const data = await apiClient.getGraph();
        setGraphData(data);
      } catch (e) {
        console.error('Failed to load graph data', e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const nodes = graphData?.nodes || [];
  const edges = graphData?.edges || [];

  const filteredEdges = edges.filter(e => {
    if (filterType === 'ALL') return true;
    return e.type === filterType;
  });

  return (
    <div className="flex flex-col h-full bg-bg-main relative">
      {/* Graph Toolbar */}
      <div className="h-14 bg-bg-sidebar border-b border-border-subtle flex items-center justify-between px-6 z-10">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
            <Network className="w-4 h-4 text-accent-primary" />
            <span>Cross-Channel Intelligence Graph</span>
          </div>

          <div className="h-4 w-px bg-border-subtle" />

          {/* Filter Chips */}
          <div className="flex items-center gap-2 text-xs">
            <span className="text-text-muted">Edges:</span>
            {['ALL', 'OBSERVED_MATCH', 'CANDIDATE_ASSOCIATION', 'DISPUTED_ASSOCIATION'].map(t => (
              <button
                key={t}
                onClick={() => setFilterType(t)}
                className={`px-2.5 py-1 rounded text-[11px] font-mono transition-colors ${
                  filterType === t 
                    ? 'bg-accent-primary text-bg-main font-bold' 
                    : 'bg-bg-card hover:bg-bg-elevated text-text-secondary border border-border-subtle'
                }`}
              >
                {t === 'ALL' ? 'All Links' : t.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setTableView(!tableView)}
            className="flex items-center gap-1.5 bg-bg-card hover:bg-bg-elevated text-text-secondary px-3 py-1.5 rounded text-xs border border-border-subtle transition-colors"
          >
            <Table className="w-3.5 h-3.5" />
            <span>{tableView ? 'Canvas View' : 'Table View'}</span>
          </button>
        </div>
      </div>

      {/* Mandatory Legend Banner */}
      <div className="bg-bg-elevated/40 border-b border-border-subtle px-6 py-2 flex items-center justify-between text-xs text-text-muted">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="w-4 h-0.5 bg-accent-primary"></span>
            <span className="text-text-primary font-medium">Solid Blue:</span>
            <span>Identical normalized identifier observed. <em>(Not proof of same criminals).</em></span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-0.5 border-t border-dashed border-risk-elevated"></span>
            <span className="text-text-primary font-medium">Dashed Amber:</span>
            <span>Candidate Playbook similarity ≥ 75%.</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-0.5 border-t border-dashed border-risk-critical"></span>
            <span className="text-text-primary font-medium">Dashed Red:</span>
            <span>Disputed link with high counter-evidence.</span>
          </div>
        </div>
      </div>

      {/* Main Canvas / Table Area */}
      <div className="flex-1 relative overflow-auto p-6">
        {loading ? (
          <div className="h-full flex items-center justify-center text-sm font-mono text-text-muted animate-pulse">
            Loading graph topology...
          </div>
        ) : tableView ? (
          /* Accessible Table Alternative */
          <div className="bg-bg-card border border-border-subtle rounded-lg overflow-hidden max-w-6xl mx-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-bg-elevated text-text-muted uppercase font-mono text-[10px] border-b border-border-subtle">
                <tr>
                  <th className="p-3">Link ID</th>
                  <th className="p-3">Association Status</th>
                  <th className="p-3">Source Node</th>
                  <th className="p-3">Target Node</th>
                  <th className="p-3">Confidence / Score</th>
                  <th className="p-3">Explanation</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {filteredEdges.map(edge => (
                  <tr key={edge.id} className="hover:bg-bg-elevated/30">
                    <td className="p-3 font-mono text-text-muted">{edge.id}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded font-mono text-[10px] ${
                        edge.type === 'OBSERVED_MATCH' ? 'bg-accent-primary/20 text-accent-primary border border-accent-primary/40' :
                        edge.type === 'CANDIDATE_ASSOCIATION' ? 'bg-risk-elevated/20 text-risk-elevated' :
                        edge.type === 'DISPUTED_ASSOCIATION' ? 'bg-risk-critical/20 text-risk-critical' : 'bg-bg-elevated text-text-muted'
                      }`}>
                        {edge.type}
                      </span>
                    </td>
                    <td className="p-3 font-mono text-text-primary">{edge.source}</td>
                    <td className="p-3 font-mono text-text-primary">{edge.target}</td>
                    <td className="p-3 font-mono text-text-secondary">
                      {edge.confidence ? `${Math.round(edge.confidence * 100)}%` : '—'}
                    </td>
                    <td className="p-3 text-text-secondary max-w-xs truncate">{edge.explanation || edge.label}</td>
                    <td className="p-3 text-right">
                      {edge.id.startsWith('assoc_') && (
                        <button
                          onClick={() => onInspectAssociation(parseInt(edge.id.replace('assoc_', '')))}
                          className="text-accent-primary hover:underline font-medium"
                        >
                          Inspect
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          /* Interactive Node Network Cards */
          <div className="max-w-6xl mx-auto space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {nodes.filter(n => n.type === 'incident').map(incNode => {
                const incId = incNode.details.incident_id;
                const connectedEdges = edges.filter(e => e.source === incNode.id || e.target === incNode.id);
                return (
                  <div
                    key={incNode.id}
                    className="bg-bg-card border border-border-subtle rounded-lg p-5 shadow-sm hover:border-accent-primary/50 transition-all flex flex-col justify-between"
                  >
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs text-text-muted">INC-{incId.toString().padStart(4, '0')}</span>
                        <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase ${
                          incNode.risk_band === 'CRITICAL' ? 'bg-risk-critical/20 text-risk-critical' :
                          incNode.risk_band === 'HIGH' ? 'bg-risk-high/20 text-risk-high' :
                          incNode.risk_band === 'ELEVATED' ? 'bg-risk-elevated/20 text-risk-elevated' : 'bg-risk-low/20 text-risk-low'
                        }`}>
                          Risk {incNode.details.risk_score || 0}
                        </span>
                      </div>
                      <h3 className="font-bold text-sm text-text-primary">{incNode.details.title}</h3>
                      <div className="text-xs text-text-muted space-y-1">
                        <div>Channel: <span className="text-text-secondary font-mono">{incNode.details.channel}</span></div>
                        <div>Language: <span className="text-text-secondary font-mono">{incNode.details.language}</span></div>
                      </div>
                    </div>

                    <div className="pt-4 border-t border-border-subtle mt-4 flex items-center justify-between">
                      <span className="text-[11px] text-text-muted">
                        {connectedEdges.length} connection(s)
                      </span>
                      <button
                        onClick={() => onSelectIncident(incId)}
                        className="text-xs text-accent-primary hover:underline font-semibold"
                      >
                        Open Details →
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Render Association Edges Summary */}
            <div className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-3">
              <h3 className="text-sm font-semibold text-text-primary">Active Cross-Incident Associations</h3>
              <div className="space-y-2">
                {filteredEdges.filter(e => e.id.startsWith('assoc_')).map(e => {
                  const assocId = parseInt(e.id.replace('assoc_', ''));
                  return (
                    <div
                      key={e.id}
                      onClick={() => onInspectAssociation(assocId)}
                      className="p-3 bg-bg-main border border-border-subtle rounded-md flex items-center justify-between hover:border-accent-primary cursor-pointer transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-xs font-bold text-accent-primary">
                          {e.source.replace('incident_', 'INC-')} ↔ {e.target.replace('incident_', 'INC-')}
                        </span>
                        <span className="text-xs bg-bg-elevated px-2 py-0.5 rounded text-text-secondary border border-border-subtle font-mono">
                          {e.type}
                        </span>
                        <span className="text-xs text-text-muted truncate max-w-md">
                          {e.explanation}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-mono font-bold text-text-primary">
                          {e.confidence ? `${Math.round(e.confidence * 100)}%` : ''}
                        </span>
                        <span className="text-xs text-accent-primary font-medium hover:underline">
                          Open Inspector →
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
