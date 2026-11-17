import { httpAdapter } from './http_adapter';
import { staticAdapter } from './static_adapter';
import { API_BASE_URL } from './config';
import { GraphData, IncidentDetail, IncidentListItem, AssociationInspectorData } from '../../types';

/**
 * live    = backend answered the health probe; the HttpApi adapter is used
 * static  = precomputed synthetic JSON (StaticApi); no backend, or none configured
 * waking  = first probe still running, or a configured backend is not answering yet and is being retried
 */
export type ApiMode = 'live' | 'static' | 'waking';

type ModeListener = (mode: ApiMode) => void;

const PROBE_TIMEOUT_MS = 2000;
const RETRY_INTERVAL_MS = 10_000;
const MAX_RETRIES = 12;

/**
 * Probe GET {base}/api/v1/health. The backend only counts as "live" if it returns JSON
 * {"status": "ok"}: a static host that rewrites every path to index.html answers 200 with HTML
 * and must NOT be mistaken for the backend.
 */
export async function probeBackend(
  base: string = API_BASE_URL,
  fetchFn: typeof fetch = fetch,
  timeoutMs: number = PROBE_TIMEOUT_MS
): Promise<boolean> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetchFn(`${base}/api/v1/health`, { signal: controller.signal });
    if (!res.ok) return false;
    const body = await res.json();
    return body?.status === 'ok';
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

class ApiClient {
  private currentMode: ApiMode = 'waking';
  private listeners: ModeListener[] = [];
  private retries = 0;
  /** Resolves once the first probe finished, so first page loads pick the right adapter. */
  private ready: Promise<void>;

  constructor() {
    this.ready = this.detectBackend();
  }

  public subscribeMode(listener: ModeListener): () => void {
    this.listeners.push(listener);
    listener(this.currentMode);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  public getMode(): ApiMode {
    return this.currentMode;
  }

  private setMode(mode: ApiMode) {
    this.currentMode = mode;
    this.listeners.forEach(l => l(mode));
  }

  private get adapter() {
    return this.currentMode === 'live' ? httpAdapter : staticAdapter;
  }

  public async detectBackend(): Promise<void> {
    if (await probeBackend()) {
      this.setMode('live');
      return;
    }
    // A backend URL is configured but not answering (e.g. a free host that is asleep): keep the
    // static demo usable and retry in the background.
    if (API_BASE_URL && this.retries < MAX_RETRIES) {
      this.retries += 1;
      this.setMode('waking');
      setTimeout(() => { void this.detectBackend(); }, RETRY_INTERVAL_MS);
      return;
    }
    this.setMode('static');
  }

  public async listIncidents(): Promise<IncidentListItem[]> {
    await this.ready;
    return this.adapter.listIncidents();
  }

  public async getIncident(id: number): Promise<IncidentDetail> {
    await this.ready;
    return this.adapter.getIncident(id);
  }

  public async createIncident(payload: unknown): Promise<IncidentDetail> {
    await this.ready;
    return this.adapter.createIncident(payload);
  }

  public async getGraph(): Promise<GraphData> {
    await this.ready;
    return this.adapter.getGraph();
  }

  public async getAssociationInspector(assocId: number): Promise<AssociationInspectorData> {
    await this.ready;
    return this.adapter.getAssociationInspector(assocId);
  }

  public async clearAllData(): Promise<void> {
    await this.ready;
    return this.adapter.clearAllData();
  }
}

export const apiClient = new ApiClient();
