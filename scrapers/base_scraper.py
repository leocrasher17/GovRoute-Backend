import hashlib
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup

class BaseScraper(ABC):
    """
    Standard Base Scraper for all CivicPath Government Sources.
    Follows: FETCH -> PARSE -> EXTRACT -> NORMALIZE -> VALIDATE -> PIPELINE
    """

    def __init__(self, source_name: str, source_code: str, base_url: str, source_type: str = "portal"):
        self.source_name = source_name
        self.source_code = source_code
        self.base_url = base_url
        self.source_type = source_type
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, application/xhtml+xml, */*",
            "Accept-Language": "en-US,en;q=0.9"
        }

    @abstractmethod
    def fetch(self, limit: int = 10, **kwargs) -> Any:
        """Fetch raw data from government source/API/portal."""
        pass

    @abstractmethod
    def parse(self, raw_data: Any) -> List[Any]:
        """Parse raw response into individual record items."""
        pass

    @abstractmethod
    def extract(self, item: Any) -> Dict[str, Any]:
        """Extract domain attributes from an item."""
        pass

    @abstractmethod
    def normalize(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize extracted fields into CivicPath standard data model."""
        pass

    def validate(self, normalized: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate required fields according to CivicPath data model."""
        errors = []
        if not normalized.get("service_name"):
            errors.append("Missing service_name")
        if not normalized.get("source_url"):
            errors.append("Missing source_url")
        if not normalized.get("source_name"):
            errors.append("Missing source_name")
        return (len(errors) == 0, errors)

    def clean_html(self, text: Optional[str]) -> Optional[str]:
        """Strips HTML tags cleanly while preserving text."""
        if not text:
            return None
        clean = BeautifulSoup(text, "html.parser").get_text(separator=" ").strip()
        clean = re.sub(r'\s+', ' ', clean)
        return clean if clean else None

    def hash_content(self, content: Any) -> str:
        """Computes SHA-256 hash for provenance and change detection."""
        if isinstance(content, (dict, list)):
            dumped = json.dumps(content, sort_keys=True, default=str)
        else:
            dumped = str(content)
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

    def run(self, limit: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Executes end-to-end scraper pipeline.
        Returns:
            - records: List[Dict] normalized records
            - raw_records: List[Dict] raw source content with hashes
            - stats: Dict with run metrics
        """
        started_at = datetime.utcnow()
        records_found = 0
        records_added = 0
        records_failed = 0
        normalized_records = []
        raw_records = []
        error_message = None

        try:
            raw_data = self.fetch(limit=limit, **kwargs)
            items = self.parse(raw_data)
            records_found = len(items)

            for item in items:
                try:
                    # Raw provenance capture
                    item_str = json.dumps(item, default=str) if isinstance(item, (dict, list)) else str(item)
                    content_hash = self.hash_content(item)

                    extracted = self.extract(item)
                    normalized = self.normalize(extracted)
                    normalized["source_hash"] = content_hash
                    normalized["scraped_at"] = datetime.utcnow()

                    is_valid, val_errors = self.validate(normalized)
                    if is_valid:
                        raw_records.append({
                            "source_name": self.source_name,
                            "source_url": normalized.get("source_url", self.base_url),
                            "page_title": normalized.get("source_page_title", self.source_name),
                            "raw_content": item_str,
                            "content_hash": content_hash,
                            "retrieved_at": datetime.utcnow()
                        })
                        normalized_records.append(normalized)
                        records_added += 1
                    else:
                        records_failed += 1
                except Exception as ex:
                    records_failed += 1

        except Exception as e:
            error_message = str(e)
            status = "failed"
        else:
            status = "successful" if records_failed == 0 else "partial"

        completed_at = datetime.utcnow()

        return {
            "source_name": self.source_name,
            "source_code": self.source_code,
            "status": status,
            "started_at": started_at,
            "completed_at": completed_at,
            "records_found": records_found,
            "records_added": records_added,
            "records_updated": 0,
            "records_failed": records_failed,
            "error_message": error_message,
            "records": normalized_records,
            "raw_records": raw_records
        }
