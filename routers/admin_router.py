from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models.models import (
    VerificationQueue, Service, Source, ExtractionRun,
    Document, Dependency, Department
)
from schemas.schemas import (
    VerificationQueueResponse,
    VerificationActionRequest,
    AdminStatsResponse
)

router = APIRouter(prefix="/api/admin", tags=["Admin & Verification"])

@router.get("/verification", response_model=List[VerificationQueueResponse])
def get_verification_queue(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    db: Session = Depends(get_db)
):
    """Retrieve items from the Admin Verification Queue."""
    query = db.query(VerificationQueue)
    if status:
        query = query.filter(VerificationQueue.status == status)

    items = query.order_by(VerificationQueue.created_at.desc()).limit(100).all()

    results = []
    for item in items:
        results.append(VerificationQueueResponse(
            id=item.id,
            service_id=item.service_id,
            service_name=item.service.service_name if item.service else "Unknown Service",
            field_name=item.field_name,
            old_value=item.old_value,
            extracted_value=item.extracted_value,
            source_url=item.source_url,
            confidence_score=float(item.confidence_score) if item.confidence_score else 1.0,
            status=item.status,
            created_at=item.created_at,
            reviewed_at=item.reviewed_at,
            reviewed_by=item.reviewed_by,
            review_notes=item.review_notes
        ))
    return results

@router.put("/verification/{item_id}", response_model=VerificationQueueResponse)
def edit_verification_item(
    item_id: int,
    request: VerificationActionRequest,
    db: Session = Depends(get_db)
):
    """Allows admin to edit an extracted field before or after approval."""
    item = db.query(VerificationQueue).filter(VerificationQueue.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Verification item not found")

    if request.edited_value is not None:
        item.old_value = item.extracted_value
        item.extracted_value = request.edited_value

    item.status = "edited"
    item.reviewed_at = datetime.utcnow()
    item.reviewed_by = request.reviewed_by or "Admin"
    item.review_notes = request.notes

    # Update actual service record if linked
    if item.service and hasattr(item.service, item.field_name):
        setattr(item.service, item.field_name, item.extracted_value)

    db.commit()
    db.refresh(item)

    return VerificationQueueResponse(
        id=item.id,
        service_id=item.service_id,
        service_name=item.service.service_name if item.service else "Unknown Service",
        field_name=item.field_name,
        old_value=item.old_value,
        extracted_value=item.extracted_value,
        source_url=item.source_url,
        confidence_score=float(item.confidence_score) if item.confidence_score else 1.0,
        status=item.status,
        created_at=item.created_at,
        reviewed_at=item.reviewed_at,
        reviewed_by=item.reviewed_by,
        review_notes=item.review_notes
    )

@router.post("/verification/{item_id}/approve")
def approve_verification_item(
    item_id: int,
    request: Optional[VerificationActionRequest] = None,
    db: Session = Depends(get_db)
):
    """Approve extracted government requirement and publish to live citizen catalog."""
    item = db.query(VerificationQueue).filter(VerificationQueue.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Verification item not found")

    item.status = "approved"
    item.reviewed_at = datetime.utcnow()
    item.reviewed_by = request.reviewed_by if request else "Admin"
    item.review_notes = request.notes if request else "Approved verified requirement from official source."

    # Mark parent service as published & verified
    if item.service:
        item.service.data_status = "published"
        item.service.verification_status = "verified"
        item.service.last_verified_at = datetime.utcnow()

    db.commit()
    return {"message": "Verification item approved successfully", "item_id": item_id}

@router.post("/verification/{item_id}/reject")
def reject_verification_item(
    item_id: int,
    request: Optional[VerificationActionRequest] = None,
    db: Session = Depends(get_db)
):
    """Reject unreliable or non-conforming extracted requirement."""
    item = db.query(VerificationQueue).filter(VerificationQueue.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Verification item not found")

    item.status = "rejected"
    item.reviewed_at = datetime.utcnow()
    item.reviewed_by = request.reviewed_by if request else "Admin"
    item.review_notes = request.notes if request else "Rejected by admin audit."

    db.commit()
    return {"message": "Verification item rejected", "item_id": item_id}

@router.get("/stats", response_model=AdminStatsResponse)
def get_admin_stats(db: Session = Depends(get_db)):
    """Retrieve system overview metrics for the Admin Dashboard."""
    total_sources = db.query(Source).count()
    total_services = db.query(Service).count()
    pending_verif = db.query(VerificationQueue).filter(VerificationQueue.status == "pending").count()
    published_srv = db.query(Service).filter(Service.data_status == "published").count()
    rejected_srv = db.query(Service).filter(Service.data_status == "rejected").count()

    failed_runs = db.query(ExtractionRun).filter(ExtractionRun.status == "failed").count()
    total_docs = db.query(Document).count()
    total_deps = db.query(Dependency).count()

    last_run = db.query(ExtractionRun).order_by(ExtractionRun.id.desc()).first()

    return AdminStatsResponse(
        total_sources=total_sources,
        total_services=total_services,
        pending_verification=pending_verif,
        published_services=published_srv,
        rejected_services=rejected_srv,
        failed_extractions=failed_runs,
        total_documents=total_docs,
        total_dependencies=total_deps,
        last_extraction_run=last_run.completed_at if last_run else None
    )
