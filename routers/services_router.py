from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from database import get_db
from models.models import Service, Department, ServiceDocument, ServiceStep, Dependency, Document
from schemas.schemas import (
    ServiceSummaryResponse,
    ServiceDetailResponse,
    ServiceRoadmapResponse,
    ServiceDocumentResponse,
    DependencyResponse
)
from services.dependency_engine import DependencyEngine

router = APIRouter(prefix="/api/services", tags=["Services"])

@router.get("", response_model=List[ServiceSummaryResponse])
def get_services(
    category: Optional[str] = None,
    level: Optional[str] = None,
    state: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieve all published government services with summary metrics."""
    query = db.query(Service)

    # By default, show published services, or filter by status if specified
    if status:
        query = query.filter(Service.data_status == status)
    else:
        query = query.filter(Service.data_status.in_(["published", "pending_verification"]))

    if category:
        query = query.filter(Service.service_category == category)
    if level:
        query = query.filter(Service.government_level == level)
    if state:
        query = query.filter(Service.state.ilike(f"%{state}%"))

    services = query.order_by(Service.id.desc()).all()

    results = []
    for s in services:
        doc_count = db.query(ServiceDocument).filter(ServiceDocument.service_id == s.id).count()
        step_count = db.query(ServiceStep).filter(ServiceStep.service_id == s.id).count()
        dep_count = db.query(Dependency).filter(Dependency.dependent_service_id == s.id).count()

        results.append(ServiceSummaryResponse(
            id=s.id,
            service_id=s.service_id,
            service_name=s.service_name,
            service_category=s.service_category,
            department_name=s.department.name if s.department else s.office,
            government_level=s.government_level,
            state=s.state,
            city=s.city,
            processing_time=s.processing_time,
            processing_time_unit=s.processing_time_unit,
            fees=s.fees,
            fee_type=s.fee_type,
            source_name=s.source_name,
            source_url=s.source_url,
            data_status=s.data_status,
            verification_status=s.verification_status,
            is_demo_data=s.is_demo_data,
            step_count=step_count,
            document_count=doc_count,
            dependency_count=dep_count
        ))

    return results

@router.get("/search", response_model=List[ServiceSummaryResponse])
def search_services(
    q: Optional[str] = Query(None, description="Search query string"),
    department: Optional[str] = None,
    category: Optional[str] = None,
    level: Optional[str] = None,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Search services by name, department, category, keywords or jurisdiction."""
    query = db.query(Service)

    if q:
        search_filter = or_(
            Service.service_name.ilike(f"%{q}%"),
            Service.description.ilike(f"%{q}%"),
            Service.eligibility.ilike(f"%{q}%"),
            Service.service_category.ilike(f"%{q}%")
        )
        query = query.filter(search_filter)

    if department:
        query = query.join(Department, Service.department_id == Department.id, isouter=True).filter(
            Department.name.ilike(f"%{department}%")
        )

    if category:
        query = query.filter(Service.service_category.ilike(f"%{category}%"))

    if level:
        query = query.filter(Service.government_level == level)

    if state:
        query = query.filter(Service.state.ilike(f"%{state}%"))

    services = query.order_by(Service.id.asc()).all()

    results = []
    for s in services:
        doc_count = db.query(ServiceDocument).filter(ServiceDocument.service_id == s.id).count()
        step_count = db.query(ServiceStep).filter(ServiceStep.service_id == s.id).count()
        dep_count = db.query(Dependency).filter(Dependency.dependent_service_id == s.id).count()

        results.append(ServiceSummaryResponse(
            id=s.id,
            service_id=s.service_id,
            service_name=s.service_name,
            service_category=s.service_category,
            department_name=s.department.name if s.department else s.office,
            government_level=s.government_level,
            state=s.state,
            city=s.city,
            processing_time=s.processing_time,
            processing_time_unit=s.processing_time_unit,
            fees=s.fees,
            fee_type=s.fee_type,
            source_name=s.source_name,
            source_url=s.source_url,
            data_status=s.data_status,
            verification_status=s.verification_status,
            is_demo_data=s.is_demo_data,
            step_count=step_count,
            document_count=doc_count,
            dependency_count=dep_count
        ))

    return results

@router.get("/{service_id}", response_model=ServiceDetailResponse)
def get_service_detail(service_id: int, db: Session = Depends(get_db)):
    """Retrieve full detail of a specific government service with provenance tracking."""
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Government service not found")

    # Fetch documents
    s_docs = db.query(ServiceDocument).filter(ServiceDocument.service_id == s.id).all()
    doc_responses = []
    for sd in s_docs:
        doc_responses.append(ServiceDocumentResponse(
            id=sd.id,
            document_id=sd.document.id,
            document_name=sd.document.name,
            description=sd.document.description,
            issuing_authority=sd.document.issuing_authority,
            document_type=sd.document.document_type,
            is_mandatory=sd.is_mandatory,
            remarks=sd.remarks
        ))

    # Fetch steps
    steps = db.query(ServiceStep).filter(ServiceStep.service_id == s.id).order_by(ServiceStep.step_number).all()

    # Fetch dependencies
    deps = db.query(Dependency).filter(Dependency.dependent_service_id == s.id).all()
    dep_responses = []
    for d in deps:
        dep_responses.append(DependencyResponse(
            id=d.id,
            dependent_service_id=d.dependent_service_id,
            prerequisite_service_id=d.prerequisite_service_id,
            prerequisite_service_name=d.prerequisite_service.service_name if d.prerequisite_service else None,
            prerequisite_document_id=d.prerequisite_document_id,
            prerequisite_document_name=d.prerequisite_document.name if d.prerequisite_document else None,
            dependency_type=d.dependency_type,
            description=d.description,
            is_mandatory=d.is_mandatory
        ))

    return ServiceDetailResponse(
        id=s.id,
        service_id=s.service_id,
        service_name=s.service_name,
        service_category=s.service_category,
        description=s.description,
        department_id=s.department_id,
        department_name=s.department.name if s.department else s.office,
        sub_department=s.sub_department,
        government_level=s.government_level,
        state=s.state,
        district=s.district,
        city=s.city,
        office=s.office,
        eligibility=s.eligibility,
        prerequisites=s.prerequisites,
        required_information=s.required_information,
        fees=s.fees,
        fee_type=s.fee_type,
        processing_time=s.processing_time,
        processing_time_unit=s.processing_time_unit,
        renewal_required=s.renewal_required,
        renewal_period=s.renewal_period,
        application_url=s.application_url,
        tracking_url=s.tracking_url,
        official_contact=s.official_contact,
        source_id=s.source_id,
        source_name=s.source_name,
        source_url=s.source_url,
        source_page_title=s.source_page_title,
        source_type=s.source_type,
        scraped_at=s.scraped_at,
        last_verified_at=s.last_verified_at,
        data_status=s.data_status,
        verification_status=s.verification_status,
        source_hash=s.source_hash,
        is_demo_data=s.is_demo_data,
        documents=doc_responses,
        steps=steps,
        dependencies=dep_responses,
        fee_details=s.fee_details
    )

@router.get("/{service_id}/roadmap", response_model=ServiceRoadmapResponse)
def get_service_roadmap(service_id: int, db: Session = Depends(get_db)):
    """Generate visual step-by-step dependency roadmap for the requested service."""
    engine = DependencyEngine(db)
    roadmap = engine.generate_roadmap(service_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Service not found for roadmap generation")
    return roadmap

@router.get("/{service_id}/documents", response_model=List[ServiceDocumentResponse])
def get_service_documents(service_id: int, db: Session = Depends(get_db)):
    """Retrieve all documents required for a service."""
    s_docs = db.query(ServiceDocument).filter(ServiceDocument.service_id == service_id).all()
    results = []
    for sd in s_docs:
        results.append(ServiceDocumentResponse(
            id=sd.id,
            document_id=sd.document.id,
            document_name=sd.document.name,
            description=sd.document.description,
            issuing_authority=sd.document.issuing_authority,
            document_type=sd.document.document_type,
            is_mandatory=sd.is_mandatory,
            remarks=sd.remarks
        ))
    return results

@router.get("/{service_id}/dependencies", response_model=List[DependencyResponse])
def get_service_dependencies(service_id: int, db: Session = Depends(get_db)):
    """Retrieve all prerequisite dependencies for a service."""
    deps = db.query(Dependency).filter(Dependency.dependent_service_id == service_id).all()
    results = []
    for d in deps:
        results.append(DependencyResponse(
            id=d.id,
            dependent_service_id=d.dependent_service_id,
            prerequisite_service_id=d.prerequisite_service_id,
            prerequisite_service_name=d.prerequisite_service.service_name if d.prerequisite_service else None,
            prerequisite_document_id=d.prerequisite_document_id,
            prerequisite_document_name=d.prerequisite_document.name if d.prerequisite_document else None,
            dependency_type=d.dependency_type,
            description=d.description,
            is_mandatory=d.is_mandatory
        ))
    return results
