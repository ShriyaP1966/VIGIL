import { httpAdapter } from './http_adapter';
import { staticAdapter } from './static_adapter';
import { GraphData, IncidentDetail, IncidentListItem, AssociationInspectorData } from '../../types';

export type ApiMode = 'live' | 'static' | 'waking';

type ModeListener = (mode: ApiMode) => void;

class ApiClient {
  private currentMode: ApiMode = 'waking';
  private adapter = staticAdapter;
  private listeners: ModeListener[] = [];

  constructor() {
    this.detectBackend();
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
    this.adapter = mode === 'live' ? (httpAdapter as any) : staticAdapter;
    this.listeners.forEach(l => l(mode));
  }

  public async detectBackend(): Promise<void> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      const res = await fetch('/api/v1/health', { signal: controller.signal });
      clearTimeout(timeoutId);

      if (res.ok) {
        this.setMode('live');
        return;
      }
    } catch (e) {
      // Backend asleep or unreachable
    }
    this.setMode('static');
  }

  public async listIncidents(): Promise<IncidentListItem[]> {
    return this.adapter.listIncidents();
  }

  public async getIncident(id: number): Promise<IncidentDetail> {
    return this.adapter.getIncident(id);
  }

  public async createIncident(payload: any): Promise<IncidentDetail> {
    return this.adapter.createIncident(payload);
  }

  public async getGraph(): Promise<GraphData> {
    return this.adapter.getGraph();
  }

  public async getAssociationInspector(assocId: number): Promise<AssociationInspectorData> {
    return this.adapter.getAssociationInspector(assocId);
  }

  public async clearAllData(): Promise<void> {
    return this.adapter.clearAllData();
  }
}

export const apiClient = new ApiClient();
