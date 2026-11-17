import { GraphData, IncidentDetail, IncidentListItem, AssociationInspectorData } from '../../types';
import { API_BASE_URL } from './config';
import { readApiError } from './errors';

async function getJson<T>(path: string, what: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`);
  if (!res.ok) throw new Error(await readApiError(res, `Failed to load ${what}`));
  return res.json();
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

  async clearAllData(): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/api/v1/data?confirm=true`, { method: 'DELETE' });
    if (!res.ok) throw new Error(await readApiError(res, 'Failed to clear data'));
  },
};
