import { GraphData, IncidentDetail, IncidentListItem, AssociationInspectorData } from '../../types';
import { DEMO_DATA_BASE } from './config';
import { LiveBackendRequiredError } from './errors';

/**
 * Static adapter: reads ONLY the precomputed synthetic JSON in /demo-data/, which
 * scripts/export_static_demo.py generates from the real pipeline. There are deliberately no
 * hard-coded fallback values here: if a file is missing we fail visibly instead of inventing data.
 */
async function loadDemo<T>(file: string): Promise<T> {
  const res = await fetch(`${DEMO_DATA_BASE}/${file}`);
  if (!res.ok) throw new Error(`Precomputed demo data "${file}" is not available (HTTP ${res.status}).`);
  const contentType = res.headers.get('content-type') || '';
  if (!contentType.includes('json')) throw new Error(`Precomputed demo data "${file}" is not valid JSON.`);
  return res.json();
}

export const staticAdapter = {
  listIncidents(): Promise<IncidentListItem[]> {
    return loadDemo('incidents.json');
  },

  getIncident(id: number): Promise<IncidentDetail> {
    return loadDemo(`incident_${id}.json`);
  },

  async createIncident(_payload: unknown): Promise<IncidentDetail> {
    throw new LiveBackendRequiredError('Analysing new evidence');
  },

  getGraph(): Promise<GraphData> {
    return loadDemo('graph.json');
  },

  getAssociationInspector(assocId: number): Promise<AssociationInspectorData> {
    return loadDemo(`association_${assocId}.json`);
  },

  async clearAllData(): Promise<void> {
    throw new LiveBackendRequiredError('Clearing data');
  },
};
