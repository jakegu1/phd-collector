"""Scraper for FindAPhD.com - the primary data source."""

import logging
import re
from typing import List, Dict

from scrapers.base import BaseScraper
from config import FINDAPHD_URLS

logger = logging.getLogger(__name__)


class FindAPhDScraper(BaseScraper):
    """Scrape PhD listings from FindAPhD.com."""

    SOURCE_NAME = "findaphd"
    BASE_URL = "https://www.findaphd.com"
    MAX_PAGES = 5  # Per region, ~15 results per page

    def scrape(self) -> List[Dict]:
        """Scrape all configured regions."""
        all_projects = []
        for region, url in FINDAPHD_URLS.items():
            logger.info(f"[FindAPhD] Scraping region: {region}")
            projects = self._scrape_region(region, url)
            all_projects.extend(projects)
            logger.info(f"[FindAPhD] Found {len(projects)} projects in {region}")
        return all_projects

    def _scrape_region(self, region: str, base_url: str) -> List[Dict]:
        """Scrape a single region with pagination."""
        projects = []
        for page in range(1, self.MAX_PAGES + 1):
            url = f"{base_url}&PageNo={page}" if page > 1 else base_url
            soup = self.fetch_page(url)
            if not soup:
                break

            listings = soup.select("div.phd-result")
            if not listings:
                # Try alternative selector
                listings = soup.select("div.card.phd-result")
            if not listings:
                listings = soup.select("div[class*='result']")
            if not listings:
                logger.warning(f"[FindAPhD] No listings found on page {page} for {region}")
                break

            for item in listings:
                project = self._parse_listing(item, region)
                if project:
                    projects.append(project)

        return projects

    def _parse_listing(self, item, region: str) -> Dict:
        """Parse a single PhD listing."""
        try:
            # Title and URL
            title_el = item.select_one("h4 a") or item.select_one("a.phd-result__title") or item.select_one("a[href*='/phds/project/']")
            if not title_el:
                return {}
            title = title_el.get_text(strip=True)
            url = title_el.get("href", "")
            if url and not url.startswith("http"):
                url = self.BASE_URL + url

            # University
            uni_el = item.select_one("a.phd-result__dept-inst") or item.select_one("span.phd-result__dept-inst") or item.select_one("a[href*='/institutions/']")
            university = uni_el.get_text(strip=True) if uni_el else ""

            # Department
            dept_el = item.select_one("a.phd-result__dept") or item.select_one("span.phd-result__dept")
            department = dept_el.get_text(strip=True) if dept_el else ""

            # Supervisor
            sup_el = item.select_one("a[href*='/supervisors/']") or item.select_one("span.phd-result__supervisor")
            supervisor = sup_el.get_text(strip=True) if sup_el else ""

            # Deadline
            deadline = ""
            deadline_el = item.select_one("span.phd-result__key-info__deadline") or item.select_one("div.phd-result__deadline")
            if deadline_el:
                deadline = deadline_el.get_text(strip=True)

            # Country
            country = ""
            country_el = item.select_one("span.phd-result__dept-country") or item.select_one("img.phd-result__flag")
            if country_el:
                country = country_el.get("title", "") or country_el.get_text(strip=True)

            # Description snippet
            desc_el = item.select_one("div.phd-result__description") or item.select_one("div.descFrag")
            description = desc_el.get_text(strip=True) if desc_el else ""

            # Funding type detection
            full_text = f"{title} {description} {deadline}"
            funding_type = self.detect_funding_type(full_text)

            # Discipline
            disc_el = item.select_one("a.phd-result__subject")
            discipline = disc_el.get_text(strip=True) if disc_el else ""

            return {
                "title": title,
                "university": university,
                "department": department,
                "supervisor": supervisor,
                "region": region,
                "region_cn": self.get_region_cn(region),
                "country": country,
                "funding_type": funding_type,
                "discipline": discipline,
                "deadline": deadline,
                "description": description[:2000],
                "url": url,
                "source": self.SOURCE_NAME,
            }
        except Exception as e:
            logger.error(f"[FindAPhD] Error parsing listing: {e}")
            return {}
