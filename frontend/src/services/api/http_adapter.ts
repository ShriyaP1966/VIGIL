import { GraphData, IncidentDetail, IncidentListItem, AssociationInspectorData } from '../../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const httpAdapter = {
  async getHealth(): Promise<{ status: string; mode: string; version: string }> {
    const res = await fetch(`${BASE_URL}/api/v1/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return res.json();
  },

  async listIncidents(): Promise<IncidentListItem[]> {
    const res = await fetch(`${BASE_URL}/api/v1/incidents`);
    if (!res.ok) throw new Error('Failed to fetch incidents');
    return res.json();
  },

  async getIncident(id: number): Promise<IncidentDetail> {
    const res = await fetch(`${BASE_URL}/api/v1/incidents/${id}`);
    if (!res.ok) throw new Error(`Failed to fetch incident ${id}`);
    return res.json();
  },

  async createIncident(payload: { title: string; source_channel: string; language: string; evidence: Array<{ text: string; type: string }> }): Promise<IncidentDetail> {
    const res = await fetch(`${BASE_URL}/api/v1/incidents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Failed to create incident');
    return res.json();
  },

  async getGraph(): Promise<GraphData> {
    const res = await fetch(`${BASE_URL}/api/v1/graph`);
    if (!res.ok) throw new Error('Failed to fetch graph');
    return res.json();
  },

  async getAssociationInspector(assocId: number): Promise<AssociationInspectorData> {
    const res = await fetch(`${BASE_URL}/api/v1/associations/${assocId}`);
    if (!res.ok) throw new Error(`Failed to fetch association ${assocId}`);
    return res.json();
  },

  async clearAllData(): Promise<void> {
    const res = await fetch(`${BASE_URL}/api/v1/data?confirm=true`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to clear data');
  }
};
