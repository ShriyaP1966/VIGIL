import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar';
import { InspectorShell } from './components/layout/InspectorShell';
import { Overview } from './pages/Overview';
import { NewInvestigation } from './pages/NewInvestigation';
import { InvestigationDetail } from './pages/InvestigationDetail';
import { IntelligenceGraph } from './pages/IntelligenceGraph';
import { Campaigns } from './pages/Campaigns';
import { ScenarioLab } from './pages/ScenarioLab';
import { SimulatedLiveCall } from './pages/SimulatedLiveCall';
import { Reports } from './pages/Reports';
import { Settings } from './pages/Settings';
import { apiClient, ApiMode } from './services/api/client';
import { ViewMode, AssociationInspectorData, NodeInspectorInfo } from './types';

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewMode>('overview');
  const [selectedIncidentId, setSelectedIncidentId] = useState<number | null>(null);
  const [apiMode, setApiMode] = useState<ApiMode>('waking');
  const [association, setAssociation] = useState<AssociationInspectorData | null>(null);
  const [nodeInfo, setNodeInfo] = useState<NodeInspectorInfo | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [inspectorError, setInspectorError] = useState<string | null>(null);

  useEffect(() => {
    const unsubscribe = apiClient.subscribeMode((mode) => setApiMode(mode));
    return () => unsubscribe();
  }, []);

  const closeInspector = useCallback(() => setInspectorOpen(false), []);

  const handleNavigate = (view: ViewMode, id?: number) => {
    if (id !== undefined) {
      setSelectedIncidentId(id);
    }
    setCurrentView(view);
    setInspectorOpen(false);
  };

  const handleInspectAssociation = async (assocId: number) => {
    setInspectorError(null);
    try {
      const data = await apiClient.getAssociationInspector(assocId);
      setAssociation(data);
      setNodeInfo(null);
      setInspectorOpen(true);
    } catch (e: any) {
      setInspectorError(e?.message || 'Failed to load the evidence inspector.');
    }
  };

  const handleInspectNode = (info: NodeInspectorInfo) => {
    setInspectorError(null);
    setNodeInfo(info);
    setAssociation(null);
    setInspectorOpen(true);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg-main text-text-primary">
      <Sidebar currentView={currentView} onNavigate={(view) => handleNavigate(view)} />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar apiMode={apiMode} onNewInvestigation={() => handleNavigate('new_investigation')} />

        {inspectorError && (
          <div role="alert" className="bg-risk-critical/10 border-b border-risk-critical/30 text-risk-critical text-xs px-6 py-2 flex justify-between">
            <span>{inspectorError}</span>
            <button type="button" onClick={() => setInspectorError(null)} className="underline">Dismiss</button>
          </div>
        )}

        <main className="flex-1 overflow-y-auto">
          {currentView === 'overview' && (
            <Overview onNavigate={(view, id) => handleNavigate(view, id)} />
          )}

          {currentView === 'new_investigation' && (
            <NewInvestigation
              apiMode={apiMode}
              onSuccess={(id) => handleNavigate('investigation_detail', id)}
            />
          )}

          {currentView === 'investigation_detail' && selectedIncidentId && (
            <InvestigationDetail
              incidentId={selectedIncidentId}
              onBack={() => handleNavigate('overview')}
              onOpenGraph={() => handleNavigate('graph')}
              onInspectAssociation={handleInspectAssociation}
            />
          )}

          {currentView === 'graph' && (
            <IntelligenceGraph
              onInspectAssociation={handleInspectAssociation}
              onInspectNode={handleInspectNode}
              onSelectIncident={(id) => handleNavigate('investigation_detail', id)}
            />
          )}

          {currentView === 'campaigns' && <Campaigns />}
          {currentView === 'scenario_lab' && <ScenarioLab />}
          {currentView === 'simulated_live_call' && <SimulatedLiveCall />}
          {currentView === 'reports' && <Reports />}
          {currentView === 'settings' && <Settings apiMode={apiMode} />}
        </main>
      </div>

      <InspectorShell
        association={association}
        node={nodeInfo}
        isOpen={inspectorOpen}
        onClose={closeInspector}
        onOpenIncident={(id) => handleNavigate('investigation_detail', id)}
      />
    </div>
  );
};

export default App;
