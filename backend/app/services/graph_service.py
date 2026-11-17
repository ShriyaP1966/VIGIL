import networkx as nx
from sqlalchemy.orm import Session
from backend.app.models.models import Incident, Entity, Mention, Evidence, Association, Analysis
from backend.app.schemas.schemas import GraphResponse, GraphNode, GraphEdge


def build_investigation_graph(
    db: Session,
    min_confidence: float = 0.0,
    include_rejected: bool = False,
    status: str | None = None,
) -> GraphResponse:
    """
    Construct cross-channel bipartite graph of incidents, extracted entities,
    structural links, and cross-incident associations (§4, §12.5).
    """
    g = nx.MultiGraph()
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    # 1. Add Incident Nodes
    incidents = db.query(Incident).all()
    for inc in incidents:
        analysis = db.query(Analysis).filter(Analysis.incident_id == inc.id).order_by(Analysis.id.desc()).first()
        risk_score = analysis.risk_score if analysis else 0
        risk_band = analysis.risk_band if analysis else "LOW"
        node_id = f"incident_{inc.id}"

        node = GraphNode(
            id=node_id,
            type="incident",
            label=f"INC-{inc.id:04d}: {inc.title[:24]}",
            risk_band=risk_band,
            details={
                "incident_id": inc.id,
                "title": inc.title,
                "channel": inc.source_channel,
                "language": inc.language,
                "status": inc.status,
                "risk_score": risk_score,
                "created_at": inc.created_at.isoformat() if inc.created_at else None
            }
        )
        nodes.append(node)
        g.add_node(node_id, **node.details)

    # 2. Add Entity Nodes and Structural Edges (Incident -> Entity)
    mentions = db.query(Mention).all()
    added_entities = set()
    added_structural = set()

    for m in mentions:
        entity = db.query(Entity).filter(Entity.id == m.entity_id).first()
        evidence = db.query(Evidence).filter(Evidence.id == m.evidence_id).first()
        if not entity or not evidence:
            continue

        ent_node_id = f"entity_{entity.id}"
        if ent_node_id not in added_entities:
            added_entities.add(ent_node_id)
            node = GraphNode(
                id=ent_node_id,
                type=entity.type.lower(),
                label=entity.display_value,
                details={
                    "entity_id": entity.id,
                    "type": entity.type,
                    "canonical_value": entity.canonical_value,
                    "display_value": entity.display_value,
                    "norm_method": entity.norm_method
                }
            )
            nodes.append(node)
            g.add_node(ent_node_id, **node.details)

        # Structural edge from Incident to Entity (one per incident/entity pair)
        edge_id = f"struct_{evidence.incident_id}_{entity.id}"
        if edge_id in added_structural:
            continue
        added_structural.add(edge_id)
        edge = GraphEdge(
            id=edge_id,
            source=f"incident_{evidence.incident_id}",
            target=ent_node_id,
            type="structural",
            label="mentions",
            confidence=m.extraction_confidence
        )
        edges.append(edge)
        g.add_edge(edge.source, edge.target, key=edge_id, type="structural")

    # 3. Add Cross-Incident Associations (Incident <-> Incident)
    associations = db.query(Association).all()
    for assoc in associations:
        if assoc.status == "REJECTED_ASSOCIATION" and not include_rejected:
            continue
        if assoc.adjusted_confidence < min_confidence:
            continue
        if status and assoc.status != status:
            continue

        edge_id = f"assoc_{assoc.id}"
        edge = GraphEdge(
            id=edge_id,
            source=f"incident_{assoc.incident_a_id}",
            target=f"incident_{assoc.incident_b_id}",
            type=assoc.status,
            label="observed match" if assoc.status == "OBSERVED_MATCH" else f"{int((assoc.similarity or 0) * 100)}%",
            similarity=assoc.similarity,
            confidence=assoc.adjusted_confidence,
            status=assoc.status,
            explanation=assoc.explanation
        )
        edges.append(edge)
        g.add_edge(edge.source, edge.target, key=edge_id, type=assoc.status)

    return GraphResponse(nodes=nodes, edges=edges)
