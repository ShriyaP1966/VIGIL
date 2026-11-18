import {
  GraphData, IncidentDetail, IncidentListItem, AssociationInspectorData,
  CampaignDetail, CampaignListItem, ReviewDecision, ScenarioInfo, ScenarioRun, IncidentReport,
  SimulationScript, SimulationFrame,
} from '../../types';
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

async function loadDemoText(file: string): Promise<string> {
  const res = await fetch(`${DEMO_DATA_BASE}/${file}`);
  if (!res.ok) throw new Error(`Precomputed demo data "${file}" is not available (HTTP ${res.status}).`);
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('html')) throw new Error(`Precomputed demo data "${file}" is not available.`);
  return res.text();
}

/** The rotation levels the hosted demo has precomputed (the same five levels as the experiment). */
export const STATIC_ROTATION_LEVELS = [0, 0.25, 0.5, 0.75, 1] as const;

/** Snap a slider value to the nearest precomputed level (the live backend accepts any value from 0 to 1). */
export function snapRotation(r: number): number {
  const x = Number.isFinite(r) ? Math.min(1, Math.max(0, r)) : 0.5;
  return STATIC_ROTATION_LEVELS.reduce((best, l) => (Math.abs(l - x) < Math.abs(best - x) ? l : best));
}

export function scenarioFile(name: string, rotation: number | null): string {
  return rotation == null ? `scenario_${name}.json` : `scenario_${name}__r${Math.round(snapRotation(rotation) * 100)}.json`;
}

const simulationCache = new Map<string, Promise<{ frames: SimulationFrame[] }>>();

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

  listCampaigns(): Promise<CampaignListItem[]> {
    return loadDemo('campaigns.json');
  },

  getCampaign(id: number): Promise<CampaignDetail> {
    return loadDemo(`campaign_${id}.json`);
  },

  async reviewAssociation(_id: number, _decision: ReviewDecision, _note?: string): Promise<AssociationInspectorData> {
    throw new LiveBackendRequiredError('Saving an analyst review');
  },

  async reviewCampaign(_id: number, _decision: ReviewDecision, _note?: string): Promise<CampaignDetail> {
    throw new LiveBackendRequiredError('Saving an analyst review');
  },

  async clearAllData(): Promise<void> {
    throw new LiveBackendRequiredError('Clearing data');
  },

  listScenarios(): Promise<ScenarioInfo[]> {
    return loadDemo('scenarios.json');
  },

  runScenario(name: string, rotation: number | null): Promise<ScenarioRun> {
    return loadDemo(scenarioFile(name, rotation));
  },

  getReport(id: number): Promise<IncidentReport> {
    return loadDemo(`report_${id}.json`);
  },

  getReportCsv(id: number): Promise<string> {
    return loadDemoText(`report_${id}.csv`);
  },

  listSimulations(): Promise<SimulationScript[]> {
    return loadDemo('simulations.json');
  },

  async getSimulationFrame(script: SimulationScript, step: number): Promise<SimulationFrame> {
    let entry = simulationCache.get(script.name);
    if (!entry) {
      entry = loadDemo<{ frames: SimulationFrame[] }>(`simulation_${script.name}.json`);
      simulationCache.set(script.name, entry);
      entry.catch(() => simulationCache.delete(script.name));
    }
    const { frames } = await entry;
    const frame = frames[step - 1];
    if (!frame) throw new Error(`Precomputed frame ${step} of "${script.name}" is not available.`);
    return frame;
  },
};
