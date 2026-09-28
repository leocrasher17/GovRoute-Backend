from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum, Numeric, Index
from sqlalchemy.orm import relationship
from database import Base

class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    base_url = Column(String(500), nullable=False)
    source_type = Column(String(50), default="portal")
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    last_scraped_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="operational")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    services = relationship("Service", back_populates="source")

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    ministry = Column(String(255), nullable=True)
    code = Column(String(50), nullable=True)
    government_level = Column(String(50), default="Central")
    state = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    services = relationship("Service", back_populates="department")
    offices = relationship("Office", back_populates="department")

class Office(Base):
    __tablename__ = "offices"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    city = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    contact_info = Column(String(255), nullable=True)

    department = relationship("Department", back_populates="offices")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    issuing_authority = Column(String(255), nullable=True)
    document_type = Column(String(100), default="Identity/Certificate")
    sample_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    service_documents = relationship("ServiceDocument", back_populates="document")

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(String(100), unique=True, nullable=False, index=True)
    service_name = Column(String(500), nullable=False, index=True)
    service_category = Column(String(150), nullable=True, index=True)
    description = Column(Text, nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    sub_department = Column(String(255), nullable=True)
    government_level = Column(String(50), default="Central")
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    office = Column(String(255), nullable=True)

    eligibility = Column(Text, nullable=True)
    prerequisites = Column(Text, nullable=True)
    required_information = Column(Text, nullable=True)

    fees = Column(String(255), nullable=True)
    fee_type = Column(String(100), nullable=True)

    processing_time = Column(String(100), nullable=True)
    processing_time_unit = Column(String(50), nullable=True)

    renewal_required = Column(Boolean, default=False)
    renewal_period = Column(String(100), nullable=True)

    application_url = Column(String(700), nullable=True)
    tracking_url = Column(String(700), nullable=True)
    official_contact = Column(Text, nullable=True)

    source_id = Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    source_name = Column(String(100), nullable=False)
    source_url = Column(String(700), nullable=False)
    source_page_title = Column(String(500), nullable=True)
    source_type = Column(String(50), nullable=True)

    scraped_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_verified_at = Column(DateTime, nullable=True)
    data_status = Column(String(50), default="pending_verification")
    verification_status = Column(String(50), default="unverified")
    source_hash = Column(String(64), nullable=False)
    is_demo_data = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = relationship("Department", back_populates="services")
    source = relationship("Source", back_populates="services")
    documents = relationship("ServiceDocument", back_populates="service", cascade="all, delete-orphan")
    requirements = relationship("Requirement", back_populates="service", cascade="all, delete-orphan")
    steps = relationship("ServiceStep", back_populates="service", cascade="all, delete-orphan", order_by="ServiceStep.step_number")
    dependencies_as_dependent = relationship("Dependency", foreign_keys="[Dependency.dependent_service_id]", back_populates="dependent_service", cascade="all, delete-orphan")
    fee_details = relationship("Fee", back_populates="service", cascade="all, delete-orphan")
    verification_items = relationship("VerificationQueue", back_populates="service", cascade="all, delete-orphan")

class ServiceDocument(Base):
    __tablename__ = "service_documents"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    is_mandatory = Column(Boolean, default=True)
    remarks = Column(Text, nullable=True)

    service = relationship("Service", back_populates="documents")
    document = relationship("Document", back_populates="service_documents")

class Requirement(Base):
    __tablename__ = "requirements"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    requirement_type = Column(String(100), default="General")
    description = Column(Text, nullable=False)
    order_no = Column(Integer, default=1)

    service = relationship("Service", back_populates="requirements")

class ServiceStep(Base):
    __tablename__ = "service_steps"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    step_type = Column(String(50), default="application")  # goal, eligibility, documents, prerequisite, application, payment, verification, approval, certificate
    estimated_days = Column(String(50), nullable=True)
    is_online = Column(Boolean, default=True)
    action_url = Column(String(700), nullable=True)

    service = relationship("Service", back_populates="steps")

class Dependency(Base):
    __tablename__ = "dependencies"

    id = Column(Integer, primary_key=True, index=True)
    dependent_service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    prerequisite_service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=True)
    prerequisite_document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    dependency_type = Column(String(50), default="service") # service, document, external
    description = Column(Text, nullable=True)
    is_mandatory = Column(Boolean, default=True)

    dependent_service = relationship("Service", foreign_keys=[dependent_service_id], back_populates="dependencies_as_dependent")
    prerequisite_service = relationship("Service", foreign_keys=[prerequisite_service_id])
    prerequisite_document = relationship("Document", foreign_keys=[prerequisite_document_id])

class Fee(Base):
    __tablename__ = "fees"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    fee_category = Column(String(150), nullable=True)
    amount = Column(Numeric(10, 2), default=0.00)
    currency = Column(String(10), default="INR")
    payment_mode = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    service = relationship("Service", back_populates="fee_details")

class RawSourceRecord(Base):
    __tablename__ = "raw_source_records"

    raw_record_id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(100), nullable=False)
    source_url = Column(String(700), nullable=False)
    page_title = Column(String(500), nullable=True)
    raw_content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    retrieved_at = Column(DateTime, default=datetime.utcnow)

class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(100), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="running")
    records_found = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_added = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

class VerificationQueue(Base):
    __tablename__ = "verification_queue"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    extracted_value = Column(Text, nullable=True)
    source_url = Column(String(700), nullable=False)
    confidence_score = Column(Numeric(4, 2), default=1.00)
    status = Column(String(50), default="pending") # pending, approved, rejected, edited
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    review_notes = Column(Text, nullable=True)

    service = relationship("Service", back_populates="verification_items")
