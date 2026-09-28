import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import engine, Base, SessionLocal
from models.models import Source, Service
from routers import (
    services_router,
    sources_router,
    extractions_router,
    admin_router
)
from services.extraction_service import ExtractionService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist
    print("Initializing CivicPath database tables...")
    Base.metadata.create_all(bind=engine)

    # Initial seed check
    db = SessionLocal()
    try:
        source_count = db.query(Source).count()
        if source_count == 0:
            print("Seeding official primary government sources...")
            initial_sources = [
                Source(name="National Single Window System", code="NSWS", base_url="https://www.nsws.gov.in", source_type="portal", description="Central portal for national business approvals, licenses, clearances and KYA module."),
                Source(name="API Setu Directory", code="APISETU", base_url="https://directory.apisetu.gov.in", source_type="api", description="National API gateway directory powered by MeitY/NeGD for verifiable certificates and departmental integrations."),
                Source(name="eDistrict Citizen Services", code="EDISTRICT", base_url="https://edistrict.gov.in", source_type="portal", description="Decentralized state & municipal citizen service delivery system for certificates, revenue and welfare."),
                Source(name="Open Government Data Platform", code="DATAGOV", base_url="https://data.gov.in", source_type="dataset", description="Government of India open datasets and API catalogs for public data and municipal statistics."),
                Source(name="Ministry of Housing and Urban Affairs", code="MOHUA", base_url="https://mohua.gov.in", source_type="portal", description="Apex authority for urban administration, municipal guidelines, Smart Cities, AMRUT and PMAY schemes.")
            ]
            db.add_all(initial_sources)
            db.commit()

        service_count = db.query(Service).count()
        if service_count == 0:
            print("Performing initial live extraction run for primary sources (NSWS, eDistrict, MoHUA, API Setu)...")
            extractor = ExtractionService(db)
            extractor.run_all_extractions(limit=3, auto_verify=True)
            print("Initial extraction complete! Database populated with verified government procedures.")
    except Exception as e:
        print(f"Notice during startup initialization: {e}")
    finally:
        db.close()

    yield
    print("CivicPath backend shutdown.")

app = FastAPI(
    title="CivicPath — Government Procedure & Dependency Roadmap Visualizer",
    description="Official API for PSWB02 Municipal Bureaucracy Path Visualizer. Implements real government data extraction, normalization, provenance tracking, admin verification, and dependency roadmap visualization.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(services_router)
app.include_router(sources_router)
app.include_router(extractions_router)
app.include_router(admin_router)

@app.get("/")
def root():
    return {
        "project": "CivicPath — Government Procedure & Dependency Roadmap Visualizer",
        "problem_statement": "PSWB02 Municipal Bureaucracy Path Visualizer",
        "status": "Operational",
        "documentation": "/docs",
        "sources_supported": ["NSWS", "APISETU", "EDISTRICT", "DATAGOV", "MOHUA"],
        "pipeline": "Government Sources -> Extraction -> Normalization -> Provenance -> Verification -> MySQL -> Dependency Engine -> Visual Roadmap"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
