"""Base scraper with shared utilities."""

import time
import logging
import hashlib
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, REQUEST_DELAY, MAX_RETRIES, FUNDING_KEYWORDS, REGIONS

logger = logging.getLogger(__name__)

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


class BaseScraper:
    """Base class for all PhD scrapers."""

    SOURCE_NAME = "base"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(BROWSER_HEADERS)

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page and return BeautifulSoup object."""
        for attempt in range(MAX_RETRIES):
            try:
                time.sleep(REQUEST_DELAY)
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
                if resp.status_code != 200:
                    logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES}: HTTP {resp.status_code} for {url}")
                    continue
                return BeautifulSoup(resp.text, "lxml")
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for {url}: {e}")
        logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts")
        return None

    def detect_funding_type(self, text: str) -> str:
        """Detect funding type from text content."""
        text_lower = text.lower()
        types = []
        for ftype, keywords in FUNDING_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    types.append(ftype)
                    break
        return ", ".join(types) if types else "unknown"

    def get_region_cn(self, region: str) -> str:
        """Get Chinese region name."""
        return REGIONS.get(region, region)

    def url_hash(self, url: str) -> str:
        """Generate hash for URL deduplication."""
        return hashlib.md5(url.encode()).hexdigest()

    def scrape(self) -> list:
        """Override in subclasses. Returns list of dicts."""
        raise NotImplementedError
