import requests
import json
from typing import Dict, Any, List
from scrapers.base_scraper import BaseScraper

class APISetuClient(BaseScraper):
    """
    API Setu Directory Adapter.
    Uses official API discovery layer under MeitY / Digital India Corporation (DIC) / NeGD.
    Extracts legitimately accessible government API specifications, publisher metadata,
    and verifiable digital certificates.
    Official URL: https://directory.apisetu.gov.in
    """

    def __init__(self):
        super().__init__(
            source_name="API Setu Directory",
            source_code="APISETU",
            base_url="https://directory.apisetu.gov.in",
            source_type="api"
        )
        self.auth_url = "https://directory.apisetu.gov.in/api/auth/generate-headers"
        self.list_url = "https://directory.apisetu.gov.in/api/list"

    def fetch(self, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """Consumes API Setu public directory using legitimate token generation."""
        headers = dict(self.headers)
        headers["Origin"] = "https://directory.apisetu.gov.in"
        headers["Referer"] = "https://directory.apisetu.gov.in/"

        try:
            # 1. Fetch dynamic session credentials
            auth_res = requests.get(self.auth_url, headers=headers, timeout=10)
            if auth_res.status_code != 200:
                print(f"API Setu token generation returned {auth_res.status_code}")
                return []

            auth_data = auth_res.json()
            headers["Authorization"] = auth_data.get("authorization")
            headers["ts"] = str(auth_data.get("ts"))
            headers["x-nonce"] = auth_data.get("nonce")

            # 2. Query published government API collections
            q_payload = {"query": "certificate", "hitsPerPage": limit}
            res = requests.get(self.list_url, params={"q": json.dumps(q_payload)}, headers=headers, timeout=12)

            if res.status_code == 200:
                data = res.json()
                return data.get("result", {}).get("hits", [])
            else:
                # Fallback to general query if specific query returned non-200
                q_fallback = {"query": "", "hitsPerPage": limit}
                res2 = requests.get(self.list_url, params={"q": json.dumps(q_fallback)}, headers=headers, timeout=12)
                if res2.status_code == 200:
                    return res2.json().get("result", {}).get("hits", [])

        except Exception as e:
            print(f"API Setu Client extraction error: {e}")

        return []

    def parse(self, raw_data: Any) -> List[Any]:
        if isinstance(raw_data, list):
            return raw_data
        return []

    def extract(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts government API and verifiable service metadata."""
        org_name = item.get("orgName") or "Government Authority"
        org_desc = item.get("orgDescription") or "Government API Integration Service"
        org_state = item.get("orgState") or "Central"
        ministry = item.get("centralMinistry") or org_name
        categories = [c.get("catName") for c in item.get("categories", []) if c.get("catName")]
        category_str = ", ".join(categories) if categories else "Public & Citizen Services"
        subdomain = item.get("subdomainName") or ""

        # Extract first API endpoint specification
        collections = item.get("Collections", [])
        api_list = []
        for coll in collections:
            for api in coll.get("Apis", []):
                api_list.append({
                    "api_name": api.get("apiName") or api.get("spec_code"),
                    "endpoint": api.get("endpoint"),
                    "spec_code": api.get("spec_code"),
                    "modified_on": api.get("modified_on"),
                    "available_docs": api.get("available_docs")
                })

        primary_api = api_list[0] if api_list else {}
        service_name = primary_api.get("api_name") or f"{org_name} Verification Service"

        source_url = f"https://directory.apisetu.gov.in/api-collection/{subdomain}" if subdomain else self.base_url

        return {
            "org_name": org_name,
            "org_desc": org_desc,
            "org_state": org_state,
            "ministry": ministry,
            "category": category_str,
            "service_name": service_name,
            "subdomain": subdomain,
            "source_url": source_url,
            "primary_api": primary_api,
            "all_apis": api_list
        }

    def normalize(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Maps extracted API Setu record into CivicPath standard data model."""
        state = extracted.get("org_state")
        gov_level = "State" if state and state.lower() != "central" else "Central"
        primary = extracted.get("primary_api", {})

        service_id = f"APISETU-{extracted.get('subdomain', '0')}-{primary.get('spec_code', 'API')}"

        documents = []
        if primary.get("spec_code"):
            documents.append({
                "name": f"Verifiable {extracted.get('service_name')}",
                "description": f"Digitally signed, machine-verifiable digital credential issued via API Setu endpoint {primary.get('endpoint')}.",
                "issuing_authority": extracted.get("org_name"),
                "document_type": "Digital Credential",
                "is_mandatory": True
            })

        steps = [
            {
                "step_number": 1,
                "title": "Identity Verification",
                "description": "Authenticate citizen identity via DigiLocker / Aadhaar OTP verification.",
                "step_type": "eligibility",
                "estimated_days": "Instant",
                "is_online": True,
                "action_url": extracted.get("source_url")
            },
            {
                "step_number": 2,
                "title": "Document Authentication",
                "description": f"Fetch official records from {extracted.get('org_name')}.",
                "step_type": "documents",
                "estimated_days": "Real-time",
                "is_online": True,
                "action_url": None
            },
            {
                "step_number": 3,
                "title": "API Handshake & Verification",
                "description": f"Query official government endpoint: {primary.get('endpoint', 'N/A')}.",
                "step_type": "verification",
                "estimated_days": "Real-time",
                "is_online": True,
                "action_url": None
            },
            {
                "step_number": 4,
                "title": "Digitally Signed Certificate Issuance",
                "description": f"Issued verifiable digital certificate: {extracted.get('service_name')}.",
                "step_type": "certificate",
                "estimated_days": "Immediate",
                "is_online": True,
                "action_url": extracted.get("source_url")
            }
        ]

        return {
            "service_id": service_id,
            "service_name": f"{extracted.get('service_name')} (API Setu Verifiable)",
            "service_category": extracted.get("category"),
            "description": extracted.get("org_desc"),
            "department": extracted.get("org_name"),
            "ministry": extracted.get("ministry"),
            "government_level": gov_level,
            "state": state if gov_level == "State" else "National / All States",
            "district": None,
            "city": None,
            "office": extracted.get("org_name"),
            "eligibility": "Indian citizen or registered entity possessing valid identity credentials and registry identifier.",
            "prerequisites": f"Digital API Gateway integration under MeitY / Digital India Corporation.",
            "required_information": "Registration number, Certificate identifier, Aadhaar / DigiLocker authorization",
            "fees": "Nil / Free Government API Service",
            "fee_type": "FREE",
            "processing_time": "Real-time / Instant",
            "processing_time_unit": "Instant",
            "renewal_required": False,
            "renewal_period": None,
            "application_url": extracted.get("source_url"),
            "tracking_url": "https://consume.apisetu.gov.in",
            "official_contact": f"API Administrator, {extracted.get('org_name')}",
            "source_name": self.source_name,
            "source_url": extracted.get("source_url"),
            "source_page_title": f"{extracted.get('org_name')} API Collection | API Setu",
            "source_type": self.source_type,
            "data_status": "pending_verification",
            "verification_status": "unverified",
            "is_demo_data": False,
            "documents": documents,
            "steps": steps,
            "dependencies": [],
            "fees_detail": [{
                "fee_category": "Official API Query",
                "amount": 0.0,
                "currency": "INR",
                "payment_mode": "Digital Public Infrastructure",
                "description": "Public Digital Good"
            }]
        }
