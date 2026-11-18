import React, { Suspense, lazy, useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar';
import { InspectorShell } from './components/layout/InspectorShell';
import { Overview } from './pages/Overview';
import { NewInvestigation } from './pages/NewInvestigation';
import { InvestigationDetail } from './pages/InvestigationDetail';
import { Skeleton } from './components/ui/States';

// The graph pulls in React Flow (the largest dependency), so it loads only when that page is opened.
const IntelligenceGraph = lazy(() => import('./pages/IntelligenceGraph').then(m => ({ default: m.IntelligenceGraph })));
import { Campaigns } from './pages/Campaigns';
import { ScenarioLab } from './pages/ScenarioLab';
import { SimulatedLiveCall } from './pages/SimulatedLiveCall';
import { Reports } from './pages/Reports';
import { Settings } from './pages/Settings';
import { NotFound } from './pages/NotFound';
import { Investigations } from './pages/Investigations';
import { ToastProvider } from './components/ui/Toast';
import { apiClient, ApiMode } from './services/api/client';
import { ViewMode, AssociationInspectorData, NodeInspectorInfo, ReviewDecision } from './types';
import { getRouter, useRoute } from './router';
import { TITLES, pathFor, sectionOf } from './router/routes';

export const App: React.FC = () => {
  const route = useRoute();
  const router = getRouter();

  const [apiMode, setApiMode] = useState<ApiMode>('waking');
  const [association, setAssociation] = useState<AssociationInspectorData | null>(null);
  const [nodeInfo, setNodeInfo] = useState<NodeInspectorInfo | null>(null);
  const [inspectorError, setInspectorError] = useState<string | null>(null);
  // Bumped after a review so the graph and the campaign pages re-read the (changed) associations.
  const [refreshKey, setRefreshKey] = useState(0);
  const canReview = apiMode === 'live';

  // Below 768 px the sidebar is a drawer, closed by default; it also closes whenever the page changes (e.g. Back).
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = useCallback(() => setMenuOpen(false), []);
  useEffect(() => { setMenuOpen(false); }, [route.path]);

  useEffect(() => {
    const unsubscribe = apiClient.subscribeMode((mode) => setApiMode(mode));
    return () => unsubscribe();
  }, []);

  // The page title follows the URL.
  useEffect(() => {
    document.title = `${TITLES[route.view]} · VIGIL`;
  }, [route.view]);

  // A node inspector belongs to the page it was opened on.
  useEffect(() => { setNodeInfo(null); }, [route.path]);

  // The evidence inspector is part of the URL (?assoc=<id>): load it whenever that parameter is present, so a
  // refresh or a pasted link reopens it, in live and in static demo mode alike.
  useEffect(() => {
    if (route.assocId == null) {
      setAssociation(null);
      return;
    }
    let cancelled = false;
    setInspectorError(null);
    apiClient.getAssociationInspector(route.assocId)
      .then((data) => { if (!cancelled) { setAssociation(data); setNodeInfo(null); } })
      .catch((e: any) => {
        if (!cancelled) {
          setAssociation(null);
          setInspectorError(e?.message || 'Failed to load the evidence inspector.');
        }
      });
    return () => { cancelled = true; };
  }, [route.assocId]);

  const handleNavigate = (view: ViewMode, id?: number) => router.navigate(pathFor(view, id));

  const handleInspectAssociation = (assocId: number) => {
    setInspectorError(null);
    router.openAssociation(assocId);
  };

  const handleInspectNode = (info: NodeInspectorInfo) => {
    setInspectorError(null);
    if (route.assocId != null) router.navigate(route.path, { replace: true });   // one inspector at a time
    setNodeInfo(info);
  };

  const closeInspector = useCallback(() => {
    if (route.assocId != null) router.closeAssociation();
    else setNodeInfo(null);
  }, [route.assocId, router]);

  const handleReviewAssociation = async (id: number, decision: ReviewDecision, note: string) => {
    const updated = await apiClient.reviewAssociation(id, decision, note);   // errors surface in the review controls
    setAssociation(updated);
    setRefreshKey(k => k + 1);
  };

  const shownAssociation = route.assocId != null && association?.id === route.assocId ? association : null;
  const inspectorOpen = shownAssociation != null || (route.assocId == null && nodeInfo != null);

  return (
    <ToastProvider>
    <div className="flex h-screen w-full max-w-full overflow-hidden bg-bg-main text-text-primary">
      <Sidebar
        currentView={sectionOf(route)}
        open={menuOpen}
        onClose={closeMenu}
        onNavigate={closeMenu}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar
          apiMode={apiMode}
          onNewInvestigation={() => handleNavigate('new_investigation')}
          onOpenMenu={() => setMenuOpen(true)}
          menuOpen={menuOpen}
        />

        {inspectorError && (
          <div role="alert" className="bg-risk-critical/10 border-b border-risk-critical/30 text-risk-critical text-xs px-4 sm:px-6 py-2 flex justify-between gap-3">
            <span>{inspectorError}</span>
            <button type="button" onClick={() => setInspectorError(null)} className="underline">Dismiss</button>
          </div>
        )}

        <main className="flex-1 overflow-y-auto">
          {route.view === 'overview' && (
            <Overview onNavigate={(view, id) => handleNavigate(view, id)} />
          )}

          {route.view === 'investigations' && <Investigations />}

          {route.view === 'new_investigation' && (
            <NewInvestigation
              apiMode={apiMode}
              onSuccess={(id) => handleNavigate('investigation_detail', id)}
            />
          )}

          {route.view === 'investigation_detail' && route.incidentId != null && (
            <InvestigationDetail
              key={route.incidentId}
              incidentId={route.incidentId}
              onBack={() => handleNavigate('overview')}
              onOpenGraph={() => handleNavigate('graph')}
              onInspectAssociation={handleInspectAssociation}
            />
          )}

          {route.view === 'graph' && (
            <Suspense fallback={<div className="p-4 sm:p-8"><Skeleton rows={4} label="Loading the graph" /></div>}>
              <IntelligenceGraph
                refreshKey={refreshKey}
                onInspectAssociation={handleInspectAssociation}
                onInspectNode={handleInspectNode}
                onSelectIncident={(id) => handleNavigate('investigation_detail', id)}
              />
            </Suspense>
          )}

          {route.view === 'campaigns' && (
            <Campaigns
              canReview={canReview}
              refreshKey={refreshKey}
              selectedId={route.campaignId ?? null}
              onSelect={(id) => handleNavigate('campaigns', id)}
              onInspectAssociation={handleInspectAssociation}
              onSelectIncident={(id) => handleNavigate('investigation_detail', id)}
              onChanged={() => setRefreshKey(k => k + 1)}
            />
          )}

          {route.view === 'scenario_lab' && <ScenarioLab apiMode={apiMode} />}
          {route.view === 'simulated_live_call' && <SimulatedLiveCall />}
          {route.view === 'reports' && <Reports />}
          {route.view === 'settings' && <Settings apiMode={apiMode} />}
          {route.view === 'not_found' && <NotFound path={route.path} />}
        </main>
      </div>

      <InspectorShell
        association={shownAssociation}
        node={route.assocId == null ? nodeInfo : null}
        isOpen={inspectorOpen}
        onClose={closeInspector}
        onOpenIncident={(id) => handleNavigate('investigation_detail', id)}
        canReview={canReview}
        onReviewAssociation={handleReviewAssociation}
      />
    </div>
    </ToastProvider>
  );
};

export default App;
