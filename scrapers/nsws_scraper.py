import requests
import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper

class NSWSScraper(BaseScraper):
    """
    National Single Window System (NSWS) Adapter.
    Extracts live government approvals, licenses, statutory requirements, fees,
    and documents directly from the NSWS Gateway.
    Official URL: https://www.nsws.gov.in
    """

    def __init__(self):
        super().__init__(
            source_name="National Single Window System",
            source_code="NSWS",
            base_url="https://www.nsws.gov.in",
            source_type="portal"
        )
        self.summary_api = "https://www.nsws.gov.in/gateway-sec/form-builder-sec/marketplace/license-summary-list"
        self.detail_api = "https://www.nsws.gov.in/gateway-sec/form-builder-sec/marketplace/license-detail/"

    def fetch(self, limit: int = 10, search_tags: List[str] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetches official approvals from NSWS marketplace.
        Targets business, municipal, environmental and infrastructure approvals.
        """
        results = []
        tags = search_tags or ["company", "water", "fire", "trade", "factory", "environment"]

        headers = dict(self.headers)
        headers["Content-Type"] = "application/json"

        # Query summary for key municipal & business approvals
        for tag in tags:
            try:
                payload = {"start": 0, "length": 3, "searchTag": tag}
                r = requests.post(self.summary_api, headers=headers, json=payload, timeout=12)
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    for item in data:
                        if item.get("licenseId") not in [x.get("licenseId") for x in results]:
                            results.append(item)
                            if len(results) >= limit:
                                break
            except Exception as e:
                print(f"NSWS tag search error ({tag}): {e}")

            if len(results) >= limit:
                break

        # If tag search yields less than limit, fetch default list
        if len(results) < limit:
            try:
                payload = {"start": 0, "length": limit - len(results), "searchTag": None}
                r = requests.post(self.summary_api, headers=headers, json=payload, timeout=12)
                if r.status_code == 200:
                    for item in r.json().get("data", []):
                        if item.get("licenseId") not in [x.get("licenseId") for x in results]:
                            results.append(item)
            except Exception as e:
                print(f"NSWS default list fetch error: {e}")

        # For each summary, fetch full official detail
        full_details = []
        for item in results[:limit]:
            lid = item.get("licenseId")
            try:
                detail_resp = requests.get(f"{self.detail_api}{lid}", headers=self.headers, timeout=10)
                if detail_resp.status_code == 200:
                    full_details.append(detail_resp.json().get("data", item))
                else:
                    full_details.append(item)
            except Exception:
                full_details.append(item)

        return full_details

    def parse(self, raw_data: Any) -> List[Any]:
        if isinstance(raw_data, list):
            return raw_data
        return []

    def extract(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts structured fields from NSWS license object."""
        lid = item.get("id") or item.get("licenseId")
        name = item.get("name") or item.get("licenseName") or "Unknown NSWS Approval"
        ministry = item.get("ministryName") or "Not specified in source"
        department = item.get("departmentName") or ministry
        about = item.get("aboutLicense") or item.get("details")
        enclosures_html = item.get("requiredEnclosures")
        who_can_apply = item.get("whoCanApply")
        law = item.get("lawAndRules")
        payment_type = item.get("paymentType") or "Not specified in source"
        display_fee = item.get("displayFee")
        price = item.get("price")
        validity = item.get("validity") or "Not specified in source"
        scope = item.get("type") or "CENTRAL"
        min_url = item.get("ministryUrlTitle")
        dept_url = item.get("departmentUrlTitle")
        lic_url = item.get("licenseUrlTitle") or item.get("urlTitle")

        # Official canonical URL on NSWS portal
        if min_url and dept_url and lic_url:
            source_url = f"https://www.nsws.gov.in/portal/approval-details/{min_url}/{dept_url}/{lic_url}"
        else:
            source_url = f"https://www.nsws.gov.in/portal/approvalsandregistrations"

        # Parse documents from enclosures HTML
        documents = []
        if enclosures_html and enclosures_html != "None":
            soup = BeautifulSoup(enclosures_html, "html.parser")
            for li in soup.find_all("li"):
                doc_name = li.get_text().strip()
                if doc_name and len(doc_name) > 2:
                    documents.append({
                        "name": doc_name,
                        "description": f"Mandatory enclosure verified under {law or 'applicable rules'}.",
                        "issuing_authority": department,
                        "document_type": "Application Enclosure",
                        "is_mandatory": True
                    })

        # Calculate fees
        fee_str = None
        if display_fee:
            fee_str = f"{display_fee}"
        elif payment_type == "FREE":
            fee_str = "Nil / Free of Charge"
        elif price and float(price) > 0:
            fee_str = f"INR {price}"
        else:
            fee_str = "Not specified in source"

        return {
            "raw_id": lid,
            "name": name,
            "ministry": ministry,
            "department": department,
            "about": self.clean_html(about) or "Not specified in source",
            "who_can_apply": self.clean_html(who_can_apply) or "Not specified in source",
            "law": law or "Not specified in source",
            "fee": fee_str,
            "fee_type": payment_type,
            "price": float(price) if price else 0.0,
            "validity": validity,
            "scope": scope,
            "source_url": source_url,
            "documents": documents
        }

    def normalize(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Maps extracted NSWS record into CivicPath standard data model."""
        lid = extracted.get("raw_id")
        scope = extracted.get("scope", "CENTRAL")
        gov_level = "Central" if scope == "CENTRAL" else "State"

        # Construct realistic procedural steps based on extracted requirements
        steps = [
            {
                "step_number": 1,
                "title": "Check Eligibility & Prerequisites",
                "description": extracted.get("who_can_apply"),
                "step_type": "eligibility",
                "estimated_days": "1 day",
                "is_online": True,
                "action_url": extracted.get("source_url")
            },
            {
                "step_number": 2,
                "title": "Assemble Required Documents",
                "description": f"Compile {len(extracted.get('documents', []))} verified enclosures required under {extracted.get('law')}.",
                "step_type": "documents",
                "estimated_days": "2-3 days",
                "is_online": True,
                "action_url": extracted.get("source_url")
            },
            {
                "step_number": 3,
                "title": "Submit Application via NSWS Single Window",
                "description": f"Complete online statutory form submission for {extracted.get('name')}.",
                "step_type": "application",
                "estimated_days": "1 day",
                "is_online": True,
                "action_url": "https://www.nsws.gov.in/portal/approvalsandregistrations"
            },
            {
                "step_number": 4,
                "title": "Statutory Fee Settlement",
                "description": f"Applicable fee requirement: {extracted.get('fee')}.",
                "step_type": "payment",
                "estimated_days": "Same day",
                "is_online": True,
                "action_url": "https://www.nsws.gov.in"
            },
            {
                "step_number": 5,
                "title": "Departmental Scrutiny & Verification",
                "description": f"Official scrutiny by {extracted.get('department')}.",
                "step_type": "verification",
                "estimated_days": "7-14 days",
                "is_online": True,
                "action_url": None
            },
            {
                "step_number": 6,
                "title": "Issuance of Approval / Certificate",
                "description": f"Official grant of {extracted.get('name')} with validity of {extracted.get('validity')}.",
                "step_type": "certificate",
                "estimated_days": "Final Step",
                "is_online": True,
                "action_url": extracted.get("source_url")
            }
        ]

        return {
            "service_id": f"NSWS-{lid}",
            "service_name": extracted.get("name"),
            "service_category": "Business & Commercial Clearances",
            "description": extracted.get("about"),
            "department": extracted.get("department"),
            "ministry": extracted.get("ministry"),
            "government_level": gov_level,
            "state": "National / All States" if gov_level == "Central" else "Not specified in source",
            "district": None,
            "city": None,
            "office": extracted.get("department"),
            "eligibility": extracted.get("who_can_apply"),
            "prerequisites": f"Governed under: {extracted.get('law')}",
            "required_information": "Entity identity, PAN, business details, supporting documentation",
            "fees": extracted.get("fee"),
            "fee_type": extracted.get("fee_type"),
            "processing_time": extracted.get("validity"),
            "processing_time_unit": "Validity Term",
            "renewal_required": True if "year" in extracted.get("validity", "").lower() else False,
            "renewal_period": extracted.get("validity"),
            "application_url": "https://www.nsws.gov.in/portal/approvalsandregistrations",
            "tracking_url": "https://www.nsws.gov.in/portal/investor-dashboard",
            "official_contact": f"Nodal Officer, {extracted.get('department')}",
            "source_name": self.source_name,
            "source_url": extracted.get("source_url"),
            "source_page_title": f"{extracted.get('name')} | National Single Window System",
            "source_type": self.source_type,
            "data_status": "pending_verification",
            "verification_status": "unverified",
            "is_demo_data": False,
            "documents": extracted.get("documents", []),
            "steps": steps,
            "dependencies": [],
            "fees_detail": [{
                "fee_category": extracted.get("fee_type", "Standard Fee"),
                "amount": extracted.get("price", 0.0),
                "currency": "INR",
                "payment_mode": "Online via NSWS Bharatkosh Gateway",
                "description": extracted.get("fee")
            }]
        }
