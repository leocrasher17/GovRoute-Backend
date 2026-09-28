import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from models.models import (
    Source, Department, Office, Document, Service,
    ServiceDocument, Requirement, ServiceStep, Dependency, Fee,
    RawSourceRecord, ExtractionRun, VerificationQueue
)
from scrapers import SCRAPER_REGISTRY

class ExtractionService:
    """
    CivicPath Core Extraction & Normalization Service.
    Orchestrates:
    SOURCE -> FETCH -> PARSE -> EXTRACT -> NORMALIZE -> VALIDATE ->
    DEDUPLICATE -> STORE RAW SOURCE -> STORE STRUCTURED DATA ->
    ADMIN VERIFICATION QUEUE -> PUBLISH
    """

    def __init__(self, db: Session):
        self.db = db

    def run_extraction_for_source(self, source_code: str, limit: int = 10, auto_verify: bool = True) -> Dict[str, Any]:
        """Runs the extraction pipeline for a single source adapter."""
        scraper_cls = SCRAPER_REGISTRY.get(source_code)
        if not scraper_cls:
            raise ValueError(f"Unknown scraper source code: {source_code}")

        scraper = scraper_cls()

        # 1. Log extraction run start
        run_record = ExtractionRun(
            source_name=scraper.source_name,
            started_at=datetime.utcnow(),
            status="running",
            records_found=0,
            records_updated=0,
            records_added=0,
            records_failed=0
        )
        self.db.add(run_record)
        self.db.commit()
        self.db.refresh(run_record)

        try:
            # 2. Run extraction
            result = scraper.run(limit=limit)

            records = result.get("records", [])
            raw_records = result.get("raw_records", [])

            run_record.records_found = result.get("records_found", 0)
            run_record.records_failed = result.get("records_failed", 0)

            # 3. Store Raw Source Records
            for raw in raw_records:
                existing_raw = self.db.query(RawSourceRecord).filter(
                    RawSourceRecord.content_hash == raw["content_hash"]
                ).first()
                if not existing_raw:
                    raw_entry = RawSourceRecord(
                        source_name=raw["source_name"],
                        source_url=raw["source_url"],
                        page_title=raw.get("page_title"),
                        raw_content=raw["raw_content"],
                        content_hash=raw["content_hash"],
                        retrieved_at=raw["retrieved_at"]
                    )
                    self.db.add(raw_entry)

            # 4. Ingest Normalized Services
            records_added = 0
            records_updated = 0

            # Find or create source DB entity
            source_db = self.db.query(Source).filter(Source.code == source_code).first()
            if not source_db:
                source_db = Source(
                    name=scraper.source_name,
                    code=source_code,
                    base_url=scraper.base_url,
                    source_type=scraper.source_type,
                    status="operational"
                )
                self.db.add(source_db)
                self.db.commit()
                self.db.refresh(source_db)

            source_db.last_scraped_at = datetime.utcnow()
            source_db.status = "operational"

            for record in records:
                # Find or create Department
                dept_name = record.get("department") or record.get("ministry") or "General Administration"
                dept = self.db.query(Department).filter(Department.name == dept_name).first()
                if not dept:
                    dept = Department(
                        name=dept_name,
                        ministry=record.get("ministry"),
                        government_level=record.get("government_level", "Central"),
                        state=record.get("state")
                    )
                    self.db.add(dept)
                    self.db.commit()
                    self.db.refresh(dept)

                # Check if Service exists
                service_id_str = record["service_id"]
                existing_service = self.db.query(Service).filter(Service.service_id == service_id_str).first()

                data_status = "published" if auto_verify else "pending_verification"
                verif_status = "verified" if auto_verify else "unverified"

                if not existing_service:
                    new_service = Service(
                        service_id=service_id_str,
                        service_name=record["service_name"],
                        service_category=record.get("service_category"),
                        description=record.get("description"),
                        department_id=dept.id,
                        sub_department=record.get("sub_department"),
                        government_level=record.get("government_level", "Central"),
                        state=record.get("state"),
                        district=record.get("district"),
                        city=record.get("city"),
                        office=record.get("office"),
                        eligibility=record.get("eligibility"),
                        prerequisites=record.get("prerequisites"),
                        required_information=record.get("required_information"),
                        fees=record.get("fees"),
                        fee_type=record.get("fee_type"),
                        processing_time=record.get("processing_time"),
                        processing_time_unit=record.get("processing_time_unit"),
                        renewal_required=record.get("renewal_required", False),
                        renewal_period=record.get("renewal_period"),
                        application_url=record.get("application_url"),
                        tracking_url=record.get("tracking_url"),
                        official_contact=record.get("official_contact"),
                        source_id=source_db.id,
                        source_name=record["source_name"],
                        source_url=record["source_url"],
                        source_page_title=record.get("source_page_title"),
                        source_type=record.get("source_type"),
                        scraped_at=record["scraped_at"],
                        last_verified_at=datetime.utcnow() if auto_verify else None,
                        data_status=data_status,
                        verification_status=verif_status,
                        source_hash=record["source_hash"],
                        is_demo_data=False
                    )
                    self.db.add(new_service)
                    self.db.commit()
                    self.db.refresh(new_service)
                    target_service = new_service
                    records_added += 1

                    # Add verification queue items for admin review demo
                    fields_to_queue = [
                        ("eligibility", record.get("eligibility")),
                        ("fees", record.get("fees")),
                        ("processing_time", record.get("processing_time"))
                    ]
                    for fname, fval in fields_to_queue:
                        if fval and fval != "Not specified in source":
                            vq = VerificationQueue(
                                service_id=target_service.id,
                                field_name=fname,
                                old_value=None,
                                extracted_value=str(fval),
                                source_url=record["source_url"],
                                confidence_score=0.98 if auto_verify else 0.85,
                                status="approved" if auto_verify else "pending"
                            )
                            self.db.add(vq)

                else:
                    # Record changed fields to verification queue if hash differs
                    target_service = existing_service
                    if existing_service.source_hash != record["source_hash"]:
                        records_updated += 1
                        existing_service.source_hash = record["source_hash"]
                        existing_service.scraped_at = record["scraped_at"]
                        existing_service.description = record.get("description")
                        existing_service.fees = record.get("fees")
                        existing_service.processing_time = record.get("processing_time")

                # Ingest Documents
                for doc_data in record.get("documents", []):
                    dname = doc_data["name"]
                    doc = self.db.query(Document).filter(Document.name == dname).first()
                    if not doc:
                        doc = Document(
                            name=dname,
                            description=doc_data.get("description"),
                            issuing_authority=doc_data.get("issuing_authority"),
                            document_type=doc_data.get("document_type", "Identity/Certificate")
                        )
                        self.db.add(doc)
                        self.db.commit()
                        self.db.refresh(doc)

                    # Map to service
                    sdoc = self.db.query(ServiceDocument).filter(
                        ServiceDocument.service_id == target_service.id,
                        ServiceDocument.document_id == doc.id
                    ).first()
                    if not sdoc:
                        sdoc = ServiceDocument(
                            service_id=target_service.id,
                            document_id=doc.id,
                            is_mandatory=doc_data.get("is_mandatory", True),
                            remarks=doc_data.get("description")
                        )
                        self.db.add(sdoc)

                # Ingest Steps
                existing_steps = self.db.query(ServiceStep).filter(ServiceStep.service_id == target_service.id).all()
                if not existing_steps:
                    for step_data in record.get("steps", []):
                        step = ServiceStep(
                            service_id=target_service.id,
                            step_number=step_data["step_number"],
                            title=step_data["title"],
                            description=step_data.get("description"),
                            step_type=step_data.get("step_type", "application"),
                            estimated_days=step_data.get("estimated_days"),
                            is_online=step_data.get("is_online", True),
                            action_url=step_data.get("action_url")
                        )
                        self.db.add(step)

                # Ingest Fees
                existing_fees = self.db.query(Fee).filter(Fee.service_id == target_service.id).all()
                if not existing_fees:
                    for fee_data in record.get("fees_detail", []):
                        f_entry = Fee(
                            service_id=target_service.id,
                            fee_category=fee_data.get("fee_category"),
                            amount=fee_data.get("amount", 0.0),
                            currency=fee_data.get("currency", "INR"),
                            payment_mode=fee_data.get("payment_mode"),
                            description=fee_data.get("description")
                        )
                        self.db.add(f_entry)

            self.db.commit()

            # Finalize run
            run_record.status = result.get("status", "successful")
            run_record.completed_at = datetime.utcnow()
            run_record.records_added = records_added
            run_record.records_updated = records_updated
            self.db.commit()

            # Auto-link inter-service dependencies
            self._link_known_dependencies()

            return {
                "source_code": source_code,
                "status": run_record.status,
                "records_found": run_record.records_found,
                "records_added": records_added,
                "records_updated": records_updated,
                "records_failed": run_record.records_failed
            }

        except Exception as e:
            self.db.rollback()
            run_record.status = "failed"
            run_record.completed_at = datetime.utcnow()
            run_record.error_message = str(e)
            self.db.commit()
            raise e

    def run_all_extractions(self, limit: int = 10, auto_verify: bool = True) -> List[Dict[str, Any]]:
        """Runs all 5 source adapters in sequence."""
        results = []
        for code in ["NSWS", "APISETU", "EDISTRICT", "DATAGOV", "MOHUA"]:
            try:
                res = self.run_extraction_for_source(code, limit=limit, auto_verify=auto_verify)
                results.append(res)
            except Exception as e:
                results.append({
                    "source_code": code,
                    "status": "failed",
                    "error": str(e)
                })
        return results

    def _link_known_dependencies(self):
        """
        Cross-connects verified dependencies between services and documents:
        e.g., Water Connection depends on Building Sanction (OBPS);
        Trade License depends on Property Ownership & Fire NOC;
        Declaration of Commencement depends on Incorporation.
        """
        try:
            water_service = self.db.query(Service).filter(Service.service_id.like("%WATER%")).first()
            obps_service = self.db.query(Service).filter(Service.service_id.like("%OBPS%")).first()
            trade_service = self.db.query(Service).filter(Service.service_id.like("%TRADE%")).first()
            fire_service = self.db.query(Service).filter(Service.service_id.like("%6540%")).first()

            # 1. Water Connection -> OBPS Building Sanction
            if water_service and obps_service:
                dep_exists = self.db.query(Dependency).filter(
                    Dependency.dependent_service_id == water_service.id,
                    Dependency.prerequisite_service_id == obps_service.id
                ).first()
                if not dep_exists:
                    dep = Dependency(
                        dependent_service_id=water_service.id,
                        prerequisite_service_id=obps_service.id,
                        dependency_type="service",
                        description="Permanent municipal water tap sanction requires a prior Sanctioned Building Plan from the Online Building Permission System (OBPS).",
                        is_mandatory=True
                    )
                    self.db.add(dep)

            # 2. Trade License -> Fire NOC
            if trade_service and fire_service:
                dep_exists = self.db.query(Dependency).filter(
                    Dependency.dependent_service_id == trade_service.id,
                    Dependency.prerequisite_service_id == fire_service.id
                ).first()
                if not dep_exists:
                    dep = Dependency(
                        dependent_service_id=trade_service.id,
                        prerequisite_service_id=fire_service.id,
                        dependency_type="service",
                        description="High-risk and industrial commercial establishments must obtain preliminary Fire Fighting Clearance before final Trade License grant.",
                        is_mandatory=False
                    )
                    self.db.add(dep)

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Notice during dependency linking: {e}")
