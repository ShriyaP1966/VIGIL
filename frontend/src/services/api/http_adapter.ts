import {
  GraphData, IncidentDetail, IncidentListItem, AssociationInspectorData,
  CampaignDetail, CampaignListItem, ReviewDecision, ScenarioInfo, ScenarioRun, IncidentReport,
  SimulationScript, SimulationFrame,
} from '../../types';
import { API_BASE_URL } from './config';
import { readApiError } from './errors';

async function getJson<T>(path: string, what: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`);
  if (!res.ok) throw new Error(await readApiError(res, `Failed to load ${what}`));
  return res.json();
}

async function postReview<T>(path: string, decision: ReviewDecision, note?: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, note: note?.trim() ? note.trim() : null }),
  });
  if (!res.ok) throw new Error(await readApiError(res, 'Failed to save the review'));
  return res.json();
}

async function getText(path: string, what: string): Promise<string> {
  const res = await fetch(`${API_BASE_URL}${path}`);
  if (!res.ok) throw new Error(await readApiError(res, `Failed to load ${what}`));
  return res.text();
}

export const httpAdapter = {
  listIncidents(): Promise<IncidentListItem[]> {
    return getJson('/api/v1/incidents', 'incidents');
  },

  getIncident(id: number): Promise<IncidentDetail> {
    return getJson(`/api/v1/incidents/${id}`, `incident ${id}`);
  },

  async createIncident(payload: unknown): Promise<IncidentDetail> {
    const res = await fetch(`${API_BASE_URL}/api/v1/incidents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await readApiError(res, 'Failed to create incident'));
    return res.json();
  },

  getGraph(): Promise<GraphData> {
    return getJson('/api/v1/graph', 'graph');
  },

  getAssociationInspector(assocId: number): Promise<AssociationInspectorData> {
    return getJson(`/api/v1/associations/${assocId}`, `association ${assocId}`);
  },

  listCampaigns(): Promise<CampaignListItem[]> {
    return getJson('/api/v1/campaigns', 'campaign hypotheses');
  },

  getCampaign(id: number): Promise<CampaignDetail> {
    return getJson(`/api/v1/campaigns/${id}`, `campaign hypothesis ${id}`);
  },

  async reviewAssociation(id: number, decision: ReviewDecision, note?: string): Promise<AssociationInspectorData> {
    return postReview(`/api/v1/associations/${id}/review`, decision, note);
  },

  async reviewCampaign(id: number, decision: ReviewDecision, note?: string): Promise<CampaignDetail> {
    return postReview(`/api/v1/campaigns/${id}/review`, decision, note);
  },

  async clearAllData(): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/api/v1/data?confirm=true`, { method: 'DELETE' });
    if (!res.ok) throw new Error(await readApiError(res, 'Failed to clear data'));
  },

  listScenarios(): Promise<ScenarioInfo[]> {
    return getJson('/api/v1/scenarios', 'scenarios');
  },

  async runScenario(name: string, rotation: number | null): Promise<ScenarioRun> {
    const res = await fetch(`${API_BASE_URL}/api/v1/scenarios/${encodeURIComponent(name)}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rotation == null ? {} : { rotation }),
    });
    if (!res.ok) throw new Error(await readApiError(res, 'Failed to run the scenario'));
    return res.json();
  },

  getReport(id: number): Promise<IncidentReport> {
    return getJson(`/api/v1/incidents/${id}/report`, `report for incident ${id}`);
  },

  getReportCsv(id: number): Promise<string> {
    return getText(`/api/v1/incidents/${id}/report?format=csv`, `CSV report for incident ${id}`);
  },

  listSimulations(): Promise<SimulationScript[]> {
    return getJson('/api/v1/simulations', 'call simulations');
  },

  async getSimulationFrame(script: SimulationScript, step: number): Promise<SimulationFrame> {
    const res = await fetch(`${API_BASE_URL}/api/v1/simulations/live-call/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ utterances: script.utterances.slice(0, step), language: script.language }),
    });
    if (!res.ok) throw new Error(await readApiError(res, 'Failed to analyse the simulated call'));
    return res.json();
  },
};
