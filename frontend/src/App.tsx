import React, { useState, useEffect } from 'react';
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
import { ViewMode, AssociationInspectorData } from './types';

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewMode>('overview');
  const [selectedIncidentId, setSelectedIncidentId] = useState<number | null>(null);
  const [apiMode, setApiMode] = useState<ApiMode>('static');
  const [inspectorData, setInspectorData] = useState<AssociationInspectorData | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);

  useEffect(() => {
    const unsubscribe = apiClient.subscribeMode((mode) => setApiMode(mode));
    return () => unsubscribe();
  }, []);

  const handleNavigate = (view: ViewMode, id?: number) => {
    if (id !== undefined) {
      setSelectedIncidentId(id);
    }
    setCurrentView(view);
  };

  const handleInspectAssociation = async (assocId: number) => {
    try {
      const data = await apiClient.getAssociationInspector(assocId);
      setInspectorData(data);
      setInspectorOpen(true);
    } catch (e) {
      console.error('Failed to load inspector payload', e);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg-main text-text-primary">
      {/* Persistent Left Sidebar */}
      <Sidebar
        currentView={currentView}
        onNavigate={(view) => handleNavigate(view)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar
          apiMode={apiMode}
          onNewInvestigation={() => handleNavigate('new_investigation')}
        />

        <main className="flex-1 overflow-y-auto">
          {currentView === 'overview' && (
            <Overview
              onNavigate={(view, id) => handleNavigate(view, id)}
            />
          )}

          {currentView === 'new_investigation' && (
            <NewInvestigation
              onSuccess={(id) => handleNavigate('investigation_detail', id)}
            />
          )}

          {currentView === 'investigation_detail' && selectedIncidentId && (
            <InvestigationDetail
              incidentId={selectedIncidentId}
              onBack={() => handleNavigate('overview')}
              onOpenGraph={() => handleNavigate('graph')}
            />
          )}

          {currentView === 'graph' && (
            <IntelligenceGraph
              onInspectAssociation={handleInspectAssociation}
              onSelectIncident={(id) => handleNavigate('investigation_detail', id)}
            />
          )}

          {currentView === 'campaigns' && <Campaigns />}
          {currentView === 'scenario_lab' && <ScenarioLab />}
          {currentView === 'simulated_live_call' && <SimulatedLiveCall />}
          {currentView === 'reports' && <Reports />}
          {currentView === 'settings' && <Settings />}
        </main>
      </div>

      {/* Slide-out Evidence Inspector */}
      <InspectorShell
        data={inspectorData}
        isOpen={inspectorOpen}
        onClose={() => setInspectorOpen(false)}
      />
    </div>
  );
};

export default App;
