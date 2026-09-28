from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
from decimal import Decimal

# Base and Document schemas
class DocumentBase(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    issuing_authority: Optional[str] = None
    document_type: Optional[str] = "Identity/Certificate"
    sample_url: Optional[str] = None

    class Config:
        from_attributes = True

class ServiceDocumentResponse(BaseModel):
    id: int
    document_id: int
    document_name: str
    description: Optional[str] = None
    issuing_authority: Optional[str] = None
    document_type: Optional[str] = None
    is_mandatory: bool = True
    remarks: Optional[str] = None

# Step Schema
class ServiceStepResponse(BaseModel):
    id: int
    step_number: int
    title: str
    description: Optional[str] = None
    step_type: str
    estimated_days: Optional[str] = None
    is_online: bool = True
    action_url: Optional[str] = None

    class Config:
        from_attributes = True

# Dependency Schema
class DependencyResponse(BaseModel):
    id: int
    dependent_service_id: int
    prerequisite_service_id: Optional[int] = None
    prerequisite_service_name: Optional[str] = None
    prerequisite_document_id: Optional[int] = None
    prerequisite_document_name: Optional[str] = None
    dependency_type: str
    description: Optional[str] = None
    is_mandatory: bool = True

# Fee Schema
class FeeResponse(BaseModel):
    id: int
    fee_category: Optional[str] = None
    amount: float
    currency: str = "INR"
    payment_mode: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True

# Service Summary Schema (for search and list)
class ServiceSummaryResponse(BaseModel):
    id: int
    service_id: str
    service_name: str
    service_category: Optional[str] = None
    department_name: Optional[str] = None
    government_level: str = "Central"
    state: Optional[str] = None
    city: Optional[str] = None
    processing_time: Optional[str] = None
    processing_time_unit: Optional[str] = None
    fees: Optional[str] = None
    fee_type: Optional[str] = None
    source_name: str
    source_url: str
    data_status: str
    verification_status: str
    is_demo_data: bool = False
    step_count: int = 0
    document_count: int = 0
    dependency_count: int = 0

    class Config:
        from_attributes = True

# Service Detail Schema
class ServiceDetailResponse(BaseModel):
    id: int
    service_id: str
    service_name: str
    service_category: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    sub_department: Optional[str] = None
    government_level: str = "Central"
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    office: Optional[str] = None
    eligibility: Optional[str] = None
    prerequisites: Optional[str] = None
    required_information: Optional[str] = None
    fees: Optional[str] = None
    fee_type: Optional[str] = None
    processing_time: Optional[str] = None
    processing_time_unit: Optional[str] = None
    renewal_required: bool = False
    renewal_period: Optional[str] = None
    application_url: Optional[str] = None
    tracking_url: Optional[str] = None
    official_contact: Optional[str] = None
    source_id: Optional[int] = None
    source_name: str
    source_url: str
    source_page_title: Optional[str] = None
    source_type: Optional[str] = None
    scraped_at: datetime
    last_verified_at: Optional[datetime] = None
    data_status: str
    verification_status: str
    source_hash: str
    is_demo_data: bool = False
    documents: List[ServiceDocumentResponse] = []
    steps: List[ServiceStepResponse] = []
    dependencies: List[DependencyResponse] = []
    fee_details: List[FeeResponse] = []

    class Config:
        from_attributes = True

# Roadmap Node & Graph Schema
class RoadmapNode(BaseModel):
    id: str
    type: str # 'start', 'eligibility', 'document', 'prerequisite_service', 'application', 'payment', 'verification', 'approval', 'complete'
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    category: str
    step_number: int
    is_mandatory: bool = True
    estimated_days: Optional[str] = None
    action_url: Optional[str] = None
    document_id: Optional[int] = None
    prerequisite_service_id: Optional[int] = None
    source_reference: Optional[str] = None

class RoadmapEdge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None
    edge_type: str = "direct" # direct, prerequisite, document_input

class ServiceRoadmapResponse(BaseModel):
    service_id: int
    service_name: str
    department_name: Optional[str] = None
    government_level: str
    source_name: str
    source_url: str
    last_verified_at: Optional[datetime] = None
    is_demo_data: bool
    total_steps: int
    estimated_total_days: Optional[str] = None
    nodes: List[RoadmapNode]
    edges: List[RoadmapEdge]

# Verification Queue Schema
class VerificationQueueResponse(BaseModel):
    id: int
    service_id: int
    service_name: str
    field_name: str
    old_value: Optional[str] = None
    extracted_value: Optional[str] = None
    source_url: str
    confidence_score: float
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None

    class Config:
        from_attributes = True

class VerificationActionRequest(BaseModel):
    action: str # approve, reject, edit
    edited_value: Optional[str] = None
    notes: Optional[str] = None
    reviewed_by: Optional[str] = "Admin"

# Source Schema
class SourceResponse(BaseModel):
    id: int
    name: str
    code: str
    base_url: str
    source_type: str
    description: Optional[str] = None
    is_active: bool
    last_scraped_at: Optional[datetime] = None
    status: str
    total_services: int = 0

    class Config:
        from_attributes = True

# Extraction Run Schema
class ExtractionRunResponse(BaseModel):
    id: int
    source_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    records_found: int
    records_updated: int
    records_added: int
    records_failed: int
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class ExtractionTriggerRequest(BaseModel):
    source_code: Optional[str] = "ALL" # NSWS, APISETU, EDISTRICT, DATAGOV, MOHUA, ALL
    limit: Optional[int] = 10

# Admin Stats Schema
class AdminStatsResponse(BaseModel):
    total_sources: int
    total_services: int
    pending_verification: int
    published_services: int
    rejected_services: int
    failed_extractions: int
    total_documents: int
    total_dependencies: int
    last_extraction_run: Optional[datetime] = None
