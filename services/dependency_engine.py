from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from models.models import Service, ServiceStep, ServiceDocument, Document, Dependency

class DependencyEngine:
    """
    CivicPath Dependency Engine.
    Converts fragmented government procedures into an ordered, dependency-aware visual roadmap:
    User Goal -> Eligibility Check -> Required Document -> Prerequisite Certificate ->
    Application Submission -> Fee Payment -> Verification/Inspection -> Approval -> Final Certificate.
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_roadmap(self, service_id: int) -> Dict[str, Any]:
        """
        Builds graph nodes and directional edges representing the full dependency path.
        """
        service = self.db.query(Service).filter(Service.id == service_id).first()
        if not service:
            return None

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        # 1. Start / User Goal Node
        goal_id = f"node-goal-{service.id}"
        nodes.append({
            "id": goal_id,
            "type": "start",
            "title": f"Goal: {service.service_name}",
            "subtitle": f"{service.department.name if service.department else service.department_name or 'Government Department'} ({service.government_level})",
            "description": service.description or "Initiate formal bureaucratic application process.",
            "category": "Goal",
            "step_number": 0,
            "is_mandatory": True,
            "estimated_days": "Start",
            "action_url": service.application_url,
            "source_reference": f"Source: {service.source_name}"
        })

        current_node_id = goal_id

        # 2. Eligibility Verification Node
        if service.eligibility and service.eligibility.strip() != "Not specified in source":
            eligibility_id = f"node-eligibility-{service.id}"
            nodes.append({
                "id": eligibility_id,
                "type": "eligibility",
                "title": "Check Eligibility Criteria",
                "subtitle": "Statutory Eligibility Check",
                "description": service.eligibility,
                "category": "Prerequisite",
                "step_number": 1,
                "is_mandatory": True,
                "estimated_days": "1 Day",
                "action_url": service.source_url,
                "source_reference": f"Rule: {service.prerequisites or 'Statutory Regulations'}"
            })
            edges.append({
                "source": current_node_id,
                "target": eligibility_id,
                "label": "Verifies Eligibility",
                "edge_type": "direct"
            })
            current_node_id = eligibility_id

        # 3. Prerequisite Document Nodes
        service_docs = self.db.query(ServiceDocument).filter(ServiceDocument.service_id == service.id).all()
        doc_node_ids = []

        if service_docs:
            for idx, sdoc in enumerate(service_docs, start=1):
                doc = sdoc.document
                doc_node_id = f"node-doc-{service.id}-{doc.id}"
                doc_node_ids.append(doc_node_id)
                nodes.append({
                    "id": doc_node_id,
                    "type": "document",
                    "title": f"Document: {doc.name}",
                    "subtitle": f"Issuing: {doc.issuing_authority or 'Government Authority'}",
                    "description": doc.description or sdoc.remarks or "Mandatory proof required for submission.",
                    "category": "Required Document",
                    "step_number": 2,
                    "is_mandatory": sdoc.is_mandatory,
                    "estimated_days": "Preparation",
                    "action_url": doc.sample_url,
                    "document_id": doc.id,
                    "source_reference": f"Mandatory: {'Yes' if sdoc.is_mandatory else 'Optional'}"
                })
                edges.append({
                    "source": current_node_id,
                    "target": doc_node_id,
                    "label": "Requires Document",
                    "edge_type": "document_input"
                })

        # 4. Service-to-Service Dependencies (Prerequisite Services)
        deps = self.db.query(Dependency).filter(Dependency.dependent_service_id == service.id).all()
        for dep in deps:
            if dep.prerequisite_service:
                dep_node_id = f"node-prereq-serv-{dep.prerequisite_service.id}"
                nodes.append({
                    "id": dep_node_id,
                    "type": "prerequisite_service",
                    "title": f"Prior Clearance: {dep.prerequisite_service.service_name}",
                    "subtitle": f"Department: {dep.prerequisite_service.department.name if dep.prerequisite_service.department else dep.prerequisite_service.department_name}",
                    "description": dep.description or "Must be completed prior to proceeding with this application.",
                    "category": "Prerequisite Clearance",
                    "step_number": 2,
                    "is_mandatory": dep.is_mandatory,
                    "estimated_days": dep.prerequisite_service.processing_time or "Prior Step",
                    "action_url": dep.prerequisite_service.source_url,
                    "prerequisite_service_id": dep.prerequisite_service.id,
                    "source_reference": f"Source: {dep.prerequisite_service.source_name}"
                })
                edges.append({
                    "source": current_node_id,
                    "target": dep_node_id,
                    "label": "Prerequisite Approval",
                    "edge_type": "prerequisite"
                })

        # 5. Core Procedural Steps
        steps = self.db.query(ServiceStep).filter(ServiceStep.service_id == service.id).order_by(ServiceStep.step_number).all()

        step_node_ids = []
        for step in steps:
            # Skip eligibility and document steps if already synthesized above
            if step.step_type in ['eligibility', 'documents'] and (service.eligibility or service_docs):
                continue

            step_id = f"node-step-{service.id}-{step.step_number}"
            step_node_ids.append(step_id)

            nodes.append({
                "id": step_id,
                "type": step.step_type,
                "title": step.title,
                "subtitle": f"Step {step.step_number} • {step.step_type.capitalize()}",
                "description": step.description,
                "category": step.step_type.capitalize(),
                "step_number": step.step_number + 2,
                "is_mandatory": True,
                "estimated_days": step.estimated_days or "Standard Timeline",
                "action_url": step.action_url or service.application_url,
                "source_reference": f"Mode: {'Online Portal' if step.is_online else 'Department / Field Inspection'}"
            })

        # Link document/prerequisite convergence into application submission step
        if step_node_ids:
            first_step = step_node_ids[0]
            if doc_node_ids:
                for d_id in doc_node_ids:
                    edges.append({
                        "source": d_id,
                        "target": first_step,
                        "label": "Submitted In",
                        "edge_type": "direct"
                    })
            else:
                edges.append({
                    "source": current_node_id,
                    "target": first_step,
                    "label": "Proceed To",
                    "edge_type": "direct"
                })

            # Chain remaining steps sequentially
            for i in range(len(step_node_ids) - 1):
                edges.append({
                    "source": step_node_ids[i],
                    "target": step_node_ids[i + 1],
                    "label": "Next Stage",
                    "edge_type": "direct"
                })
            last_procedural_node = step_node_ids[-1]
        else:
            last_procedural_node = current_node_id

        # 6. Completion Node
        completion_id = f"node-complete-{service.id}"
        nodes.append({
            "id": completion_id,
            "type": "complete",
            "title": f"Approval Granted: {service.service_name}",
            "subtitle": f"Official Certificate / License Issued",
            "description": f"Successfully completed. Officially verified under {service.source_name}.",
            "category": "Completion",
            "step_number": 99,
            "is_mandatory": True,
            "estimated_days": "Completed",
            "action_url": service.tracking_url or service.source_url,
            "source_reference": f"Track at: {service.tracking_url or 'Official Portal'}"
        })
        edges.append({
            "source": last_procedural_node,
            "target": completion_id,
            "label": "Final Grant",
            "edge_type": "direct"
        })

        return {
            "service_id": service.id,
            "service_name": service.service_name,
            "department_name": service.department.name if service.department else service.department_name,
            "government_level": service.government_level,
            "source_name": service.source_name,
            "source_url": service.source_url,
            "last_verified_at": service.last_verified_at,
            "is_demo_data": service.is_demo_data,
            "total_steps": len(nodes),
            "estimated_total_days": service.processing_time or "15 to 30 Days",
            "nodes": nodes,
            "edges": edges
        }
