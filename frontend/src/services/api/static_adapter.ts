import { GraphData, IncidentDetail, IncidentListItem, AssociationInspectorData } from '../../types';

export const staticAdapter = {
  async getHealth(): Promise<{ status: string; mode: string; version: string }> {
    return { status: 'ok', mode: 'static-demo', version: '3.1.0' };
  },

  async listIncidents(): Promise<IncidentListItem[]> {
    try {
      const res = await fetch('/demo-data/incidents.json');
      if (res.ok) return await res.json();
    } catch (e) {
      // fallback
    }
    return [
      {
        id: 1,
        title: 'Digital Arrest Call (CBI Impersonation)',
        source_channel: 'call',
        language: 'hi-Latn',
        status: 'open',
        risk_score: 78,
        risk_band: 'HIGH',
        created_at: new Date().toISOString()
      },
      {
        id: 2,
        title: 'Customs Contraband Parcel Demand',
        source_channel: 'call',
        language: 'en',
        status: 'open',
        risk_score: 72,
        risk_band: 'HIGH',
        created_at: new Date().toISOString()
      },
      {
        id: 3,
        title: 'Legitimate Branch Notification',
        source_channel: 'sms',
        language: 'en',
        status: 'reviewed',
        risk_score: 10,
        risk_band: 'LOW',
        created_at: new Date().toISOString()
      }
    ];
  },

  async getIncident(id: number): Promise<IncidentDetail> {
    try {
      const res = await fetch(`/demo-data/incident_${id}.json`);
      if (res.ok) return await res.json();
    } catch (e) {}

    return {
      id,
      title: id === 1 ? 'Digital Arrest Call (CBI Impersonation)' : 'Customs Contraband Parcel Demand',
      source_channel: 'call',
      language: 'hi-Latn',
      status: 'open',
      is_synthetic: true,
      created_at: new Date().toISOString(),
      evidence_items: [
        {
          id: 10 + id,
          type: 'transcript',
          original_text: 'Main CBI officer bol raha hoon. Pay verification fee to verify-cbi@okhdfcbank immediately or face FIR.',
          normalised_text: 'Main CBI officer bol raha hoon. Pay verification fee to verify-cbi@okhdfcbank immediately or face FIR.',
          sha256: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
          provenance: 'seed:slice_demo',
          timestamp: new Date().toISOString(),
          entities: [
            {
              id: 100,
              type: 'UPI_HANDLE',
              canonical_value: 'verify-cbi@okhdfcbank',
              display_value: 've•••@okhdfcbank',
              norm_method: 'lower_case',
              span_start: 56,
              span_end: 78,
              confidence: 0.95
            },
            {
              id: 101,
              type: 'ORGANISATION',
              canonical_value: 'Central Bureau of Investigation',
              display_value: 'Central Bureau of Investigation',
              norm_method: 'gazetteer_alias',
              span_start: 5,
              span_end: 8,
              confidence: 0.92
            }
          ]
        }
      ],
      analysis: {
        id: 1,
        incident_id: id,
        extractor: 'RuleMLExtractor',
        extractor_version: '3.1.0',
        fallback_used: false,
        risk_score: 78,
        risk_band: 'HIGH',
        risk_version: 'risk@3.1.0',
        injection_flags: [],
        fingerprint: { stage_sequence: ['AUTHORITY', 'DEMAND'] },
        contributions: [
          {
            factor: 'F1 tactic presence (Financial Demand via UPI)',
            evidence_ref: 'evidence:11',
            rule_version: 'risk@3.1.0',
            contribution: 18,
            effect: 'SUPPORTING',
            explanation: 'Direct UPI payment handle identified in communication.'
          },
          {
            factor: 'F1 tactic presence (Authority Impersonation)',
            evidence_ref: 'evidence:11',
            rule_version: 'risk@3.1.0',
            contribution: 14,
            effect: 'SUPPORTING',
            explanation: 'Claimed representation of law enforcement or regulatory agency.'
          },
          {
            factor: 'F3 OBSERVED_MATCH cross-incident link',
            evidence_ref: 'assoc:1',
            rule_version: 'risk@3.1.0',
            contribution: 12,
            effect: 'SUPPORTING',
            explanation: 'Shares identical normalized UPI handle with INC-0002.'
          }
        ]
      }
    };
  },

  async createIncident(payload: any): Promise<IncidentDetail> {
    return this.getIncident(1);
  },

  async getGraph(): Promise<GraphData> {
    try {
      const res = await fetch('/demo-data/graph.json');
      if (res.ok) return await res.json();
    } catch (e) {}

    return {
      nodes: [
        {
          id: 'incident_1',
          type: 'incident',
          label: 'INC-0001: Digital Arrest Call',
          risk_band: 'HIGH',
          details: { incident_id: 1, title: 'Digital Arrest Call (CBI Impersonation)', risk_score: 78 }
        },
        {
          id: 'incident_2',
          type: 'incident',
          label: 'INC-0002: Customs Parcel Demand',
          risk_band: 'HIGH',
          details: { incident_id: 2, title: 'Customs Contraband Parcel Demand', risk_score: 72 }
        },
        {
          id: 'incident_3',
          type: 'incident',
          label: 'INC-0003: Branch Notification',
          risk_band: 'LOW',
          details: { incident_id: 3, title: 'Legitimate Branch Notification', risk_score: 10 }
        },
        {
          id: 'entity_100',
          type: 'upi_handle',
          label: 've•••@okhdfcbank',
          details: { canonical_value: 'verify-cbi@okhdfcbank', display_value: 've•••@okhdfcbank', type: 'UPI_HANDLE' }
        }
      ],
      edges: [
        {
          id: 'struct_1_100',
          source: 'incident_1',
          target: 'entity_100',
          type: 'structural',
          label: 'mentions'
        },
        {
          id: 'struct_2_100',
          source: 'incident_2',
          target: 'entity_100',
          type: 'structural',
          label: 'mentions'
        },
        {
          id: 'assoc_1',
          source: 'incident_1',
          target: 'incident_2',
          type: 'OBSERVED_MATCH',
          label: 'observed match',
          confidence: 0.75,
          status: 'OBSERVED_MATCH',
          explanation: "Exact normalized UPI_HANDLE 've•••@okhdfcbank' observed in evidence of both incidents."
        }
      ]
    };
  },

  async getAssociationInspector(assocId: number): Promise<AssociationInspectorData> {
    return {
      id: assocId,
      status: 'OBSERVED_MATCH',
      match_type: 'EXACT_IDENTIFIER',
      incidents: [
        { id: 1, title: 'Digital Arrest Call (CBI Impersonation)' },
        { id: 2, title: 'Customs Contraband Parcel Demand' }
      ],
      base_confidence: 0.75,
      adjusted_confidence: 0.75,
      component_scores: { exact_identifier_match: 1.0 },
      shared_entities: [
        {
          entity_id: 100,
          type: 'UPI_HANDLE',
          canonical_value: 'verify-cbi@okhdfcbank',
          display_value: 've•••@okhdfcbank',
          norm_method: 'lower_case'
        }
      ],
      evidence: [
        {
          evidence_id: 11,
          incident_id: 1,
          entity_id: 100,
          entity_type: 'UPI_HANDLE',
          canonical_value: 'verify-cbi@okhdfcbank',
          display_value: 've•••@okhdfcbank',
          excerpt: 'Main CBI officer bol raha hoon. Pay verification fee to verify-cbi@okhdfcbank immediately or face FIR.'
        },
        {
          evidence_id: 12,
          incident_id: 2,
          entity_id: 100,
          entity_type: 'UPI_HANDLE',
          canonical_value: 'verify-cbi@okhdfcbank',
          display_value: 've•••@okhdfcbank',
          excerpt: 'Your parcel contains contraband. Send security deposit to verify-cbi@okhdfcbank within 30 minutes.'
        }
      ],
      counter_evidence: [],
      explanation: "Exact normalized UPI_HANDLE 've•••@okhdfcbank' observed in evidence of both incidents.",
      versions: { algorithm: 'vigil@3.1.0', extractor: 'regex_gazetteer@3.1.0' },
      review: { state: 'OBSERVED_MATCH', history: [] }
    };
  },

  async clearAllData(): Promise<void> {}
};
