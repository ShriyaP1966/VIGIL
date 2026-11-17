import React, { useEffect, useState } from 'react';
import { ShieldAlert, Users, Network, Layers, ArrowUpRight, Plus, AlertCircle } from 'lucide-react';
import { apiClient } from '../services/api/client';
import { IncidentListItem, GraphData } from '../types';

interface OverviewProps {
  onNavigate: (view: any, id?: number) => void;
}

export const Overview: React.FC<OverviewProps> = ({ onNavigate }) => {
  const [incidents, setIncidents] = useState<IncidentListItem[]>([]);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [incList, g] = await Promise.all([
          apiClient.listIncidents(),
          apiClient.getGraph()
        ]);
        setIncidents(incList);
        setGraphData(g);
      } catch (e: any) {
        setError(e?.message || 'Failed to load overview data.');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const totalIncidents = incidents.length;
  const observedMatches = graphData?.edges.filter(e => e.type === 'OBSERVED_MATCH').length || 0;
  const candidateAssocs = graphData?.edges.filter(e => e.type === 'CANDIDATE_ASSOCIATION').length || 0;
  const totalEntities = graphData?.nodes.filter(n => n.type !== 'incident').length || 0;

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">Intelligence Overview</h1>
          <p className="text-sm text-text-secondary mt-1">
            Cross-channel scam evidence, observed identifier matches and risk indicators.
          </p>
        </div>
        <button
          onClick={() => onNavigate('new_investigation')}
          className="inline-flex items-center gap-2 bg-accent-primary hover:bg-sky-400 text-bg-main px-4 py-2 rounded-md font-semibold text-sm transition-colors shadow-sm self-start"
        >
          <Plus className="w-4 h-4" />
          <span>New Investigation</span>
        </button>
      </div>

      {/* Synthetic Data Disclaimer Banner */}
      <div className="bg-bg-elevated/40 border border-border-subtle rounded-lg p-4 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-accent-primary shrink-0 mt-0.5" />
        <div className="text-xs text-text-secondary leading-relaxed">
          <strong className="text-text-primary font-semibold">Synthetic data:</strong> all evidence here is synthetic and the risk indicator is an uncalibrated heuristic. A solid blue line means the same identifier was observed in two incidents. <span className="text-text-primary">It is not proof of one campaign.</span>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-bg-card border border-border-subtle rounded-lg p-5">
          <div className="flex items-center justify-between text-text-muted mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Total Incidents</span>
            <ShieldAlert className="w-4 h-4 text-accent-primary" />
          </div>
          <div className="text-2xl font-bold font-mono text-text-primary">{totalIncidents}</div>
          <div className="text-[11px] text-text-muted mt-1">Cross-channel reports</div>
        </div>

        <div className="bg-bg-card border border-border-subtle rounded-lg p-5">
          <div className="flex items-center justify-between text-text-muted mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Observed Matches</span>
            <Network className="w-4 h-4 text-risk-elevated" />
          </div>
          <div className="text-2xl font-bold font-mono text-text-primary">{observedMatches}</div>
          <div className="text-[11px] text-accent-primary mt-1">Exact normalized identifiers</div>
        </div>

        <div className="bg-bg-card border border-border-subtle rounded-lg p-5">
          <div className="flex items-center justify-between text-text-muted mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Candidate Links</span>
            <Layers className="w-4 h-4 text-accent-secondary" />
          </div>
          <div className="text-2xl font-bold font-mono text-text-primary">{candidateAssocs}</div>
          <div className="text-[11px] text-text-muted mt-1">Similar script, no shared identifier</div>
        </div>

        <div className="bg-bg-card border border-border-subtle rounded-lg p-5">
          <div className="flex items-center justify-between text-text-muted mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Extracted Indicators</span>
            <Users className="w-4 h-4 text-text-secondary" />
          </div>
          <div className="text-2xl font-bold font-mono text-text-primary">{totalEntities}</div>
          <div className="text-[11px] text-text-muted mt-1">Phones, UPI, domains, orgs</div>
        </div>
      </div>

      {/* Recent Incidents Feed */}
      <div className="bg-bg-card border border-border-subtle rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-border-subtle flex items-center justify-between">
          <h2 className="text-base font-semibold text-text-primary">Recent Evidence Records</h2>
          <button 
            onClick={() => onNavigate('graph')}
            className="text-xs text-accent-primary hover:underline flex items-center gap-1 font-medium"
          >
            Explore Graph <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {loading ? (
          <div role="status" className="p-8 text-center text-sm text-text-muted font-mono animate-pulse">
            Loading investigation records...
          </div>
        ) : error ? (
          <div role="alert" className="p-8 text-center text-sm text-risk-critical">{error}</div>
        ) : incidents.length === 0 ? (
          <div className="p-8 text-center text-sm text-text-muted">
            No incidents ingested yet. Click "New Investigation" to paste evidence.
          </div>
        ) : (
          <div className="divide-y divide-border-subtle">
            {incidents.map((inc) => (
              <div
                key={inc.id}
                role="button"
                tabIndex={0}
                onClick={() => onNavigate('investigation_detail', inc.id)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onNavigate('investigation_detail', inc.id); } }}
                className="px-6 py-4 flex items-center justify-between hover:bg-bg-elevated/40 cursor-pointer transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-text-muted">INC-{inc.id.toString().padStart(4, '0')}</span>
                    <span className="font-semibold text-sm text-text-primary hover:text-accent-primary transition-colors">
                      {inc.title}
                    </span>
                    <span className="text-[10px] font-mono uppercase bg-bg-elevated px-2 py-0.5 rounded text-text-secondary border border-border-subtle">
                      {inc.source_channel}
                    </span>
                    <span className="text-[10px] font-mono uppercase bg-bg-elevated px-2 py-0.5 rounded text-text-muted">
                      {inc.language}
                    </span>
                  </div>
                  <div className="text-xs text-text-muted">
                    Ingested on {new Date(inc.created_at).toLocaleDateString()} at {new Date(inc.created_at).toLocaleTimeString()}
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="text-xs font-mono font-bold">
                      <span className={
                        inc.risk_band === 'CRITICAL' ? 'text-risk-critical' :
                        inc.risk_band === 'HIGH' ? 'text-risk-high' :
                        inc.risk_band === 'ELEVATED' ? 'text-risk-elevated' : 'text-risk-low'
                      }>
                        Risk {inc.risk_score || 0}
                      </span>
                    </div>
                    <div className="text-[10px] text-text-muted uppercase font-mono">
                      {inc.risk_band || 'LOW'}
                    </div>
                  </div>
                  <ArrowUpRight className="w-4 h-4 text-text-muted" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
