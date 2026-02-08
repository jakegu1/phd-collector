"""Scraper for ScholarshipDb.net."""

import logging
import re
from typing import List, Dict

from scrapers.base import BaseScraper
from config import SCHOLARSHIPDB_URLS

logger = logging.getLogger(__name__)


class ScholarshipDbScraper(BaseScraper):
    """Scrape PhD scholarships from ScholarshipDb.net."""

    SOURCE_NAME = "scholarshipdb"
    BASE_URL = "https://scholarshipdb.net"
    MAX_PAGES = 3

    def scrape(self) -> List[Dict]:
        """Scrape all configured regions."""
        all_projects = []
        seen_urls = set()
        for region, urls in SCHOLARSHIPDB_URLS.items():
            logger.info(f"[ScholarshipDb] Scraping region: {region}")
            region_projects = []
            for base_url in urls:
                projects = self._scrape_region(region, base_url)
                for p in projects:
                    if p.get("url") not in seen_urls:
                        seen_urls.add(p.get("url"))
                        region_projects.append(p)
            all_projects.extend(region_projects)
            logger.info(f"[ScholarshipDb] Found {len(region_projects)} projects in {region}")
        return all_projects

    def _scrape_region(self, region: str, base_url: str) -> List[Dict]:
        """Scrape a single URL source with pagination."""
        projects = []
        for page in range(1, self.MAX_PAGES + 1):
            sep = "&" if "?" in base_url else "?"
            url = f"{base_url}{sep}page={page}" if page > 1 else base_url
            soup = self.fetch_page(url)
            if not soup:
                break

            # Listings are <li> elements that contain <h4><a>
            all_lis = soup.find_all("li")
            listings = [li for li in all_lis if li.find("h4")]
            if not listings:
                logger.warning(f"[ScholarshipDb] No listings found on page {page} for {region}")
                break

            for item in listings:
                project = self._parse_listing(item, region)
                if project:
                    projects.append(project)

            logger.info(f"[ScholarshipDb] Page {page}: {len(listings)} listings")

        return projects

    def _parse_listing(self, item, region: str) -> Dict:
        """Parse a single ScholarshipDb listing."""
        try:
            # Title and URL: h4 > a
            title_el = item.select_one("h4 a")
            if not title_el:
                return {}
            title = title_el.get_text(strip=True)
            url = title_el.get("href", "")
            if url and not url.startswith("http"):
                url = self.BASE_URL + url

            # Try to extract university from URL (often encoded in URL slug)
            university = ""
            url_match = re.search(r"[-/]([A-Z][a-z]+-University[^=/]*)", url)
            if url_match:
                university = url_match.group(1).replace("-", " ")
            else:
                # Try other URL patterns like "University-of-XXX"
                url_match = re.search(r"(University[- ]of[- ][A-Za-z-]+)", url.replace("-", " "))
                if url_match:
                    university = url_match.group(1)

            # Description: any <p> or <small> text in the listing
            desc_el = item.select_one("p") or item.select_one("small")
            description = desc_el.get_text(strip=True)[:2000] if desc_el else ""

            # Country: try to extract from the listing text or nearby elements
            country = ""
            country_el = item.select_one("span.country") or item.select_one("small.text-muted")
            if country_el:
                country = country_el.get_text(strip=True)

            full_text = f"{title} {description}"
            funding_type = self.detect_funding_type(full_text)

            return {
                "title": title,
                "university": university,
                "department": "",
                "supervisor": "",
                "region": region,
                "region_cn": self.get_region_cn(region),
                "country": country,
                "funding_type": funding_type,
                "discipline": "",
                "deadline": "",
                "description": description,
                "url": url,
                "source": self.SOURCE_NAME,
            }
        except Exception as e:
            logger.error(f"[ScholarshipDb] Error parsing listing: {e}")
            return {}
