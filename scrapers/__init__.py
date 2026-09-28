from scrapers.base_scraper import BaseScraper
from scrapers.nsws_scraper import NSWSScraper
from scrapers.apisetu_client import APISetuClient
from scrapers.edistrict_scraper import EDistrictScraper
from scrapers.datagov_scraper import DataGovScraper
from scrapers.mohua_scraper import MoHUAScraper

SCRAPER_REGISTRY = {
    "NSWS": NSWSScraper,
    "APISETU": APISetuClient,
    "EDISTRICT": EDistrictScraper,
    "DATAGOV": DataGovScraper,
    "MOHUA": MoHUAScraper
}
