from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.models import Source, Service
from schemas.schemas import SourceResponse

router = APIRouter(prefix="/api/sources", tags=["Sources"])

@router.get("", response_model=List[SourceResponse])
def get_sources(db: Session = Depends(get_db)):
    """Retrieve all official government source adapters with operational status and metrics."""
    sources = db.query(Source).all()
    results = []
    for s in sources:
        srv_count = db.query(Service).filter(Service.source_id == s.id).count()
        results.append(SourceResponse(
            id=s.id,
            name=s.name,
            code=s.code,
            base_url=s.base_url,
            source_type=s.source_type,
            description=s.description,
            is_active=s.is_active,
            last_scraped_at=s.last_scraped_at,
            status=s.status,
            total_services=srv_count
        ))
    return results

@router.get("/{source_id}", response_model=SourceResponse)
def get_source_detail(source_id: int, db: Session = Depends(get_db)):
    """Retrieve details for a single government source."""
    s = db.query(Source).filter(Source.id == source_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Government source not found")

    srv_count = db.query(Service).filter(Service.source_id == s.id).count()
    return SourceResponse(
        id=s.id,
        name=s.name,
        code=s.code,
        base_url=s.base_url,
        source_type=s.source_type,
        description=s.description,
        is_active=s.is_active,
        last_scraped_at=s.last_scraped_at,
        status=s.status,
        total_services=srv_count
    )
