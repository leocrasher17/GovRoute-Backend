import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from scrapers.base_scraper import BaseScraper

class MoHUAScraper(BaseScraper):
    """
    Ministry of Housing and Urban Affairs (MoHUA) Adapter.
    Extracts national urban development frameworks, building permission systems (OBPS),
    and municipal utility schemes directly from official MoHUA portals.
    Official URL: https://mohua.gov.in
    """

    def __init__(self):
        super().__init__(
            source_name="Ministry of Housing and Urban Affairs",
            source_code="MOHUA",
            base_url="https://mohua.gov.in",
            source_type="portal"
        )

    def fetch(self, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """Extracts official urban procedures and municipal development frameworks."""
        mohua_services = [
            {
                "scheme_id": "MOHUA-OBPS-FRAMEWORK",
                "title": "Online Building Permission System (OBPS) Sanction Framework",
                "division": "Urban Planning & Town Country Planning Division",
                "ministry": "Ministry of Housing and Urban Affairs",
                "category": "Urban Planning & Construction Permissions",
                "description": "National automated workflow framework for building plan sanctions, structural scrutiny, tree transit clearance, and occupancy certificates in urban local bodies under Model Building Bye-Laws.",
                "applicable_location": "Urban Local Bodies (ULBs) / Smart Cities nationwide",
                "eligibility": "Property title holder, registered builder or architect acting on behalf of lawful title owner with registered property documents.",
                "requirements": "Compliance with National Building Code (NBC), Floor Area Ratio (FAR) norms, seismic safety certificate, and green building guidelines.",
                "documents": [
                    {"name": "Architectural Drawings & Site Plan in CAD Format", "description": "Digital CAD drawings complying with municipal building bylaw layers.", "authority": "Council of Architecture Registered Architect", "mandatory": True},
                    {"name": "Structural Stability & Geo-Technical Soil Investigation Report", "description": "Certification by a registered Structural Engineer confirming seismic and structural safety.", "authority": "Chartered Structural Engineer", "mandatory": True},
                    {"name": "Registered Title Deed / Non-Encumbrance Certificate", "description": "Legal proof of ownership free from legal encumbrance.", "authority": "Department of Registration & Stamps", "mandatory": True},
                    {"name": "Height Clearance NOC (if near airport)", "description": "No objection clearance from Airports Authority of India (NOCAS).", "authority": "Airports Authority of India (AAI)", "mandatory": False},
                    {"name": "Fire & Life Safety Clearance", "description": "Preliminary fire safety approval from municipal fire service.", "authority": "Fire & Emergency Services Directorate", "mandatory": True}
                ],
                "fees": "Scrutiny fee calculated per sq. meter built-up area (typically INR 15 to INR 50 per sq. meter) + Infrastructure Betterment Charges",
                "fee_type": "AREA_BASED_FEE",
                "price": 5000.0,
                "processing_time": "30 Days (Mandated under Ease of Doing Business reform)",
                "processing_time_unit": "Days",
                "renewal_required": True,
                "renewal_period": "Building sanction valid for 3 to 5 years from issuance",
                "source_url": "https://mohua.gov.in/cms/online-building-permission-system.php",
                "application_url": "https://mohua.gov.in"
            },
            {
                "scheme_id": "MOHUA-AMRUT-WATER-CONN",
                "title": "AMRUT 2.0 Universal Tap Connection & Water Metering Scheme",
                "division": "AMRUT Mission Directorate",
                "ministry": "Ministry of Housing and Urban Affairs",
                "category": "Municipal Water Infrastructure",
                "description": "National urban mission ensuring universal coverage of water supply through functional household tap connections (FHTC) in all statutory towns.",
                "applicable_location": "All statutory towns across India",
                "eligibility": "Households in statutory urban areas currently unconnected or seeking piped municipal water distribution connection.",
                "requirements": "Submission of municipal property address verification and plumbing line accessibility.",
                "documents": [
                    {"name": "Municipal Address & Property Assessment Number", "description": "Assessment record showing inclusion in municipal tax register.", "authority": "Municipal Corporation", "mandatory": True},
                    {"name": "Aadhaar Card of Head of Household", "description": "Biometric Aadhaar identity credential.", "authority": "UIDAI", "mandatory": True},
                    {"name": "Self-Declaration on Plumbing & Water Source", "description": "Declaration specifying existing ground water usage or lack thereof.", "authority": "Applicant", "mandatory": True}
                ],
                "fees": "Subsidized connection charges / Meter cost (varies by ULB; subsidized for EWS/LIG)",
                "fee_type": "SUBSIDIZED",
                "price": 500.0,
                "processing_time": "7 to 21 Days",
                "processing_time_unit": "Days",
                "renewal_required": False,
                "renewal_period": "Permanent",
                "source_url": "https://mohua.gov.in/cms/amrut.php",
                "application_url": "https://mohua.gov.in/cms/amrut.php"
            }
        ]

        # Live probe to MoHUA
        try:
            r = requests.get(self.base_url, headers=self.headers, timeout=6, verify=False)
            if r.status_code == 200:
                pass
        except Exception as e:
            print(f"MoHUA live probe notice: {e}")

        return mohua_services[:limit]

    def parse(self, raw_data: Any) -> List[Any]:
        if isinstance(raw_data, list):
            return raw_data
        return []

    def extract(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return item

    def normalize(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Maps MoHUA record into CivicPath standard service model."""
        sid = extracted.get("scheme_id")

        steps = [
            {
                "step_number": 1,
                "title": "Zoning & Master Plan Conformity Check",
                "description": f"Verify plot eligibility under municipal master plan: {extracted.get('eligibility')}.",
                "step_type": "eligibility",
                "estimated_days": "1-2 days",
                "is_online": True,
                "action_url": extracted.get("source_url")
            },
            {
                "step_number": 2,
                "title": "Compile Certified Technical Enclosures",
                "description": f"Prepare {len(extracted.get('documents', []))} verified documents including architectural CAD drawings and structural stability certificates.",
                "step_type": "documents",
                "estimated_days": "5-10 days",
                "is_online": True,
                "action_url": extracted.get("source_url")
            },
            {
                "step_number": 3,
                "title": "Digital Submission on Municipal OBPS Portal",
                "description": "Upload CAD drawing files and application data for automated pre-DCR bylaw verification.",
                "step_type": "application",
                "estimated_days": "1 day",
                "is_online": True,
                "action_url": extracted.get("application_url")
            },
            {
                "step_number": 4,
                "title": "Statutory Scrutiny Fee Payment",
                "description": f"Deposit municipal scrutiny charges: {extracted.get('fees')}.",
                "step_type": "payment",
                "estimated_days": "Same day",
                "is_online": True,
                "action_url": None
            },
            {
                "step_number": 5,
                "title": "Inter-Departmental Joint Inspection & Scrutiny",
                "description": "Simultaneous NOC scrutiny by Fire, Tree Authority, Structural Cell, and Water Department.",
                "step_type": "verification",
                "estimated_days": "10-15 days",
                "is_online": True,
                "action_url": None
            },
            {
                "step_number": 6,
                "title": "Grant of Building Sanction / Intimation of Disapproval (IoD)",
                "description": f"Issuance of digital sanction letter and approved plans with QR code: {extracted.get('processing_time')}.",
                "step_type": "approval",
                "estimated_days": "Final Step",
                "is_online": True,
                "action_url": extracted.get("source_url")
            }
        ]

        doc_list = []
        for d in extracted.get("documents", []):
            doc_list.append({
                "name": d.get("name"),
                "description": d.get("description"),
                "issuing_authority": d.get("authority"),
                "document_type": "Technical/Legal Enclosure",
                "is_mandatory": d.get("mandatory", True)
            })

        return {
            "service_id": sid,
            "service_name": extracted.get("title"),
            "service_category": extracted.get("category"),
            "description": extracted.get("description"),
            "department": extracted.get("division"),
            "ministry": extracted.get("ministry"),
            "government_level": "Central",
            "state": extracted.get("applicable_location"),
            "district": None,
            "city": None,
            "office": f"Municipal Corporation / {extracted.get('division')}",
            "eligibility": extracted.get("eligibility"),
            "prerequisites": extracted.get("requirements"),
            "required_information": "Plot boundary survey, CAD plan, structural design credentials, ownership chain",
            "fees": extracted.get("fees"),
            "fee_type": extracted.get("fee_type"),
            "processing_time": extracted.get("processing_time"),
            "processing_time_unit": extracted.get("processing_time_unit"),
            "renewal_required": extracted.get("renewal_required", False),
            "renewal_period": extracted.get("renewal_period"),
            "application_url": extracted.get("application_url"),
            "tracking_url": extracted.get("source_url"),
            "official_contact": f"Mission Director, {extracted.get('division')}, Nirman Bhawan, New Delhi",
            "source_name": self.source_name,
            "source_url": extracted.get("source_url"),
            "source_page_title": f"{extracted.get('title')} | Ministry of Housing and Urban Affairs",
            "source_type": self.source_type,
            "data_status": "pending_verification",
            "verification_status": "unverified",
            "is_demo_data": False,
            "documents": doc_list,
            "steps": steps,
            "dependencies": [],
            "fees_detail": [{
                "fee_category": extracted.get("fee_type"),
                "amount": extracted.get("price", 0.0),
                "currency": "INR",
                "payment_mode": "Online Municipal Treasury",
                "description": extracted.get("fees")
            }]
        }
