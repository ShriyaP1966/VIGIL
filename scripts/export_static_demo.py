#!/usr/bin/env python3
"""
Precomputed Synthetic Demo Data Exporter (§14).
Exports seeded benchmark scenarios, graph structures, and inspector payloads into
frontend/public/demo-data/ so that the public static web link operates seamlessly
even when the free Render backend is asleep.
"""

import json
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

output_dir = root_dir / "frontend" / "public" / "demo-data"


def export():
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Exporting precomputed static demo data to {output_dir}...")

    # 1. Incidents list
    incidents = [
        {
            "id": 1,
            "title": "Digital Arrest Threat — CBI Officer Impersonation",
            "source_channel": "call",
            "language": "hi-Latn",
            "status": "open",
            "risk_score": 78,
            "risk_band": "HIGH",
            "created_at": "2026-11-17T08:00:00Z"
        },
        {
            "id": 2,
            "title": "Customs Contraband Parcel Demand",
            "source_channel": "call",
            "language": "en",
            "status": "open",
            "risk_score": 72,
            "risk_band": "HIGH",
            "created_at": "2026-11-17T08:15:00Z"
        },
        {
            "id": 3,
            "title": "HDFC Official Branch Alert",
            "source_channel": "sms",
            "language": "en",
            "status": "reviewed",
            "risk_score": 10,
            "risk_band": "LOW",
            "created_at": "2026-11-17T08:30:00Z"
        }
    ]
    (output_dir / "incidents.json").write_text(json.dumps(incidents, indent=2), encoding="utf-8")

    # 2. Graph topology
    graph = {
        "nodes": [
            {
                "id": "incident_1",
                "type": "incident",
                "label": "INC-0001: Digital Arrest Call",
                "risk_band": "HIGH",
                "details": {
                    "incident_id": 1,
                    "title": "Digital Arrest Threat — CBI Officer Impersonation",
                    "channel": "call",
                    "language": "hi-Latn",
                    "status": "open",
                    "risk_score": 78
                }
            },
            {
                "id": "incident_2",
                "type": "incident",
                "label": "INC-0002: Customs Parcel Demand",
                "risk_band": "HIGH",
                "details": {
                    "incident_id": 2,
                    "title": "Customs Contraband Parcel Demand",
                    "channel": "call",
                    "language": "en",
                    "status": "open",
                    "risk_score": 72
                }
            },
            {
                "id": "incident_3",
                "type": "incident",
                "label": "INC-0003: Official Branch Alert",
                "risk_band": "LOW",
                "details": {
                    "incident_id": 3,
                    "title": "HDFC Official Branch Alert",
                    "channel": "sms",
                    "language": "en",
                    "status": "reviewed",
                    "risk_score": 10
                }
            },
            {
                "id": "entity_100",
                "type": "upi_handle",
                "label": "ve•••@okhdfcbank",
                "details": {
                    "entity_id": 100,
                    "type": "UPI_HANDLE",
                    "canonical_value": "verify-cbi@okhdfcbank",
                    "display_value": "ve•••@okhdfcbank",
                    "norm_method": "lower_case"
                }
            },
            {
                "id": "entity_101",
                "type": "organisation",
                "label": "Central Bureau of Investigation",
                "details": {
                    "entity_id": 101,
                    "type": "ORGANISATION",
                    "canonical_value": "Central Bureau of Investigation",
                    "display_value": "Central Bureau of Investigation",
                    "norm_method": "gazetteer_alias"
                }
            }
        ],
        "edges": [
            {
                "id": "struct_1_100",
                "source": "incident_1",
                "target": "entity_100",
                "type": "structural",
                "label": "mentions"
            },
            {
                "id": "struct_2_100",
                "source": "incident_2",
                "target": "entity_100",
                "type": "structural",
                "label": "mentions"
            },
            {
                "id": "struct_1_101",
                "source": "incident_1",
                "target": "entity_101",
                "type": "structural",
                "label": "mentions"
            },
            {
                "id": "assoc_1",
                "source": "incident_1",
                "target": "incident_2",
                "type": "OBSERVED_MATCH",
                "label": "observed match",
                "confidence": 0.75,
                "status": "OBSERVED_MATCH",
                "explanation": "Exact normalized UPI_HANDLE 've•••@okhdfcbank' observed in evidence of both incidents."
            }
        ]
    }
    (output_dir / "graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")

    # 3. Incident 1 detail
    inc1_detail = {
        "id": 1,
        "title": "Digital Arrest Threat — CBI Officer Impersonation",
        "source_channel": "call",
        "language": "hi-Latn",
        "status": "open",
        "is_synthetic": True,
        "created_at": "2026-11-17T08:00:00Z",
        "evidence_items": [
            {
                "id": 10,
                "type": "transcript",
                "original_text": "Main CBI officer Rajesh Sharma bol raha hoon. Aapke Aadhaar card par illegal parcel Mumbai customs ne pakda hai. Is parcel mein drugs aur money laundering ke documents hain. Agar aap turant arrest warrant se bachna chahte hain to apni verification deposit 50000 rupees verify-cbi@okhdfcbank par transfer kijiye. Kisi ko mat batana, aap video call surveillance par hain.",
                "normalised_text": "Main CBI officer Rajesh Sharma bol raha hoon. Aapke Aadhaar card par illegal parcel Mumbai customs ne pakda hai. Is parcel mein drugs aur money laundering ke documents hain. Agar aap turant arrest warrant se bachna chahte hain to apni verification deposit 50000 rupees verify-cbi@okhdfcbank par transfer kijiye. Kisi ko mat batana, aap video call surveillance par hain.",
                "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
                "provenance": "seed:scenario_01",
                "timestamp": "2026-11-17T08:00:00Z",
                "entities": [
                    {
                        "id": 100,
                        "type": "UPI_HANDLE",
                        "canonical_value": "verify-cbi@okhdfcbank",
                        "display_value": "ve•••@okhdfcbank",
                        "norm_method": "lower_case",
                        "span_start": 255,
                        "span_end": 277,
                        "confidence": 0.95
                    },
                    {
                        "id": 101,
                        "type": "ORGANISATION",
                        "canonical_value": "Central Bureau of Investigation",
                        "display_value": "Central Bureau of Investigation",
                        "norm_method": "gazetteer_alias",
                        "span_start": 5,
                        "span_end": 8,
                        "confidence": 0.92
                    }
                ]
            }
        ],
        "analysis": {
            "id": 1,
            "incident_id": 1,
            "extractor": "RuleMLExtractor",
            "extractor_version": "3.1.0",
            "fallback_used": False,
            "risk_score": 78,
            "risk_band": "HIGH",
            "risk_version": "risk@3.1.0",
            "injection_flags": [],
            "fingerprint": {
                "stage_sequence": ["AUTHORITY", "ALLEGATION", "THREAT", "ISOLATION", "URGENCY", "DEMAND"]
            },
            "contributions": [
                {
                    "factor": "F1 tactic presence (Financial Demand via UPI)",
                    "evidence_ref": "evidence:10",
                    "rule_version": "risk@3.1.0",
                    "contribution": 18,
                    "effect": "SUPPORTING",
                    "explanation": "Direct UPI payment handle identified in communication."
                },
                {
                    "factor": "F1 tactic presence (Authority Impersonation)",
                    "evidence_ref": "evidence:10",
                    "rule_version": "risk@3.1.0",
                    "contribution": 14,
                    "effect": "SUPPORTING",
                    "explanation": "Claimed representation of law enforcement or regulatory agency."
                },
                {
                    "factor": "F1 tactic presence (Threat & Intimidation)",
                    "evidence_ref": "evidence:10",
                    "rule_version": "risk@3.1.0",
                    "contribution": 14,
                    "effect": "SUPPORTING",
                    "explanation": "Threats of criminal prosecution, legal arrest, or asset freezing."
                },
                {
                    "factor": "F1 tactic presence (Urgency / Coercion)",
                    "evidence_ref": "evidence:10",
                    "rule_version": "risk@3.1.0",
                    "contribution": 8,
                    "effect": "SUPPORTING",
                    "explanation": "Artificial urgency applied to force immediate compliance."
                },
                {
                    "factor": "F2 canonical order observed",
                    "evidence_ref": "evidence:10",
                    "rule_version": "risk@3.1.0",
                    "contribution": 12,
                    "effect": "SUPPORTING",
                    "explanation": "Progresses through canonical stages (Authority -> Threat -> Demand)."
                },
                {
                    "factor": "F3 OBSERVED_MATCH cross-incident link",
                    "evidence_ref": "assoc:1",
                    "rule_version": "risk@3.1.0",
                    "contribution": 12,
                    "effect": "SUPPORTING",
                    "explanation": "Shares identical normalized identifier with INC-0002."
                }
            ]
        }
    }
    (output_dir / "incident_1.json").write_text(json.dumps(inc1_detail, indent=2), encoding="utf-8")

    # 4. Association 1 inspector payload
    assoc1_detail = {
        "id": 1,
        "status": "OBSERVED_MATCH",
        "match_type": "EXACT_IDENTIFIER",
        "incidents": [
            {"id": 1, "title": "Digital Arrest Threat — CBI Officer Impersonation"},
            {"id": 2, "title": "Customs Contraband Parcel Demand"}
        ],
        "similarity": None,
        "base_confidence": 0.75,
        "adjusted_confidence": 0.75,
        "component_scores": {"exact_identifier_match": 1.0},
        "shared_entities": [
            {
                "entity_id": 100,
                "type": "UPI_HANDLE",
                "canonical_value": "verify-cbi@okhdfcbank",
                "display_value": "ve•••@okhdfcbank",
                "norm_method": "lower_case"
            }
        ],
        "evidence": [
            {
                "evidence_id": 10,
                "incident_id": 1,
                "entity_id": 100,
                "entity_type": "UPI_HANDLE",
                "canonical_value": "verify-cbi@okhdfcbank",
                "display_value": "ve•••@okhdfcbank",
                "excerpt": "Main CBI officer Rajesh Sharma bol raha hoon. Pay verification fee to verify-cbi@okhdfcbank immediately..."
            },
            {
                "evidence_id": 20,
                "incident_id": 2,
                "entity_id": 100,
                "entity_type": "UPI_HANDLE",
                "canonical_value": "verify-cbi@okhdfcbank",
                "display_value": "ve•••@okhdfcbank",
                "excerpt": "This is Mumbai Customs Department. You are directed to transfer clearance charges immediately to verify-cbi@okhdfcbank within 30 minutes."
            }
        ],
        "counter_evidence": [],
        "explanation": "Exact normalized UPI_HANDLE 've•••@okhdfcbank' observed in evidence of both incidents.",
        "versions": {
            "algorithm": "vigil@3.1.0",
            "extractor": "regex_gazetteer@3.1.0"
        },
        "review": {
            "state": "OBSERVED_MATCH",
            "history": []
        }
    }
    (output_dir / "association_1.json").write_text(json.dumps(assoc1_detail, indent=2), encoding="utf-8")

    print("Static demo data bundle exported successfully.")


if __name__ == "__main__":
    export()
