from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from database import get_db, SessionLocal
from models.models import ExtractionRun
from schemas.schemas import ExtractionRunResponse, ExtractionTriggerRequest
from services.extraction_service import ExtractionService

router = APIRouter(prefix="/api/extractions", tags=["Extractions"])

def execute_extraction_task(source_code: str, limit: int):
    """Background task runner for data extractions."""
    db = SessionLocal()
    try:
        service = ExtractionService(db)
        if source_code == "ALL":
            service.run_all_extractions(limit=limit, auto_verify=True)
        else:
            service.run_extraction_for_source(source_code, limit=limit, auto_verify=True)
    except Exception as e:
        print(f"Background extraction error for {source_code}: {e}")
    finally:
        db.close()

@router.get("", response_model=List[ExtractionRunResponse])
def get_extraction_runs(db: Session = Depends(get_db)):
    """Retrieve history of all automated extraction pipeline runs."""
    runs = db.query(ExtractionRun).order_by(ExtractionRun.id.desc()).limit(50).all()
    return runs

@router.post("/run")
def trigger_extraction(
    request: ExtractionTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger live data extraction pipeline.
    Runs synchronously if limit <= 5 for instant feedback, or in background.
    """
    service = ExtractionService(db)
    source_code = request.source_code.upper() if request.source_code else "ALL"
    limit = request.limit or 5

    try:
        if source_code == "ALL":
            results = service.run_all_extractions(limit=limit, auto_verify=True)
            return {
                "message": "Full multi-source extraction completed successfully",
                "results": results
            }
        else:
            res = service.run_extraction_for_source(source_code, limit=limit, auto_verify=True)
            return {
                "message": f"Extraction completed for {source_code}",
                "result": res
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
