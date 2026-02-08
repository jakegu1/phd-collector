"""Scraper for EURAXESS - European researcher job portal."""

import logging
from typing import List, Dict

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Correct EURAXESS search URL for R1 (PhD) positions
EURAXESS_SEARCH_URL = (
    "https://euraxess.ec.europa.eu/jobs/search"
    "?keywords=&research_profiles=First+Stage+Researcher+%28R1%29"
    "&page={page}"
)


class EuraxessScraper(BaseScraper):
    """Scrape PhD/R1 positions from EURAXESS."""

    SOURCE_NAME = "euraxess"
    BASE_URL = "https://euraxess.ec.europa.eu"
    MAX_PAGES = 3

    def scrape(self) -> List[Dict]:
        """Scrape EURAXESS R1 (PhD) positions."""
        all_projects = []
        for page in range(self.MAX_PAGES):
            url = EURAXESS_SEARCH_URL.format(page=page)
            logger.info(f"[EURAXESS] Scraping page {page + 1}")
            soup = self.fetch_page(url)
            if not soup:
                break

            # Listings are div.ecl-content-item__content-block
            listings = soup.select("div.ecl-content-item__content-block")
            if not listings:
                logger.warning(f"[EURAXESS] No listings found on page {page + 1}")
                break

            for item in listings:
                project = self._parse_listing(item)
                if project:
                    all_projects.append(project)

            logger.info(f"[EURAXESS] Page {page + 1}: {len(listings)} listings")

        logger.info(f"[EURAXESS] Total found: {len(all_projects)} projects")
        return all_projects

    def _parse_listing(self, item) -> Dict:
        """Parse a single EURAXESS listing."""
        try:
            # Title: h3.ecl-content-block__title > a > span
            title_el = item.select_one("h3.ecl-content-block__title a")
            if not title_el:
                return {}
            title = title_el.get_text(strip=True)
            url = title_el.get("href", "")
            if url and not url.startswith("http"):
                url = self.BASE_URL + url

            # Organization: first li in primary meta container
            org_el = item.select_one("ul.ecl-content-block__primary-meta-container li a")
            university = org_el.get_text(strip=True) if org_el else ""

            # Work Location: div.id-Work-Locations
            country = ""
            location_div = item.select_one("div.id-Work-Locations")
            if location_div:
                loc_text = location_div.get_text(" ", strip=True)
                # Extract country and university from location text
                # Format: "Work Locations: Number of offers: 1, Country, University, City..."
                loc_text = loc_text.replace("Work Locations:", "").replace("Number of offers:", "").strip()
                parts = [p.strip() for p in loc_text.split(",") if p.strip()]
                if len(parts) >= 2:
                    country = parts[1]  # Country is typically second part (after offer count)
                if len(parts) >= 3 and not university:
                    university = parts[2]  # University is typically third

            # Research field: div.id-Research-Field
            discipline = ""
            field_div = item.select_one("div.id-Research-Field")
            if field_div:
                field_links = field_div.select("a")
                disciplines = list(set(a.get_text(strip=True) for a in field_links))
                discipline = ", ".join(disciplines[:3])

            # Deadline: div.id-Application-Deadline > time[datetime]
            deadline = ""
            deadline_div = item.select_one("div.id-Application-Deadline")
            if deadline_div:
                time_el = deadline_div.select_one("time")
                if time_el:
                    deadline = time_el.get_text(strip=True)

            # Description: div.ecl-content-block__description
            desc_el = item.select_one("div.ecl-content-block__description")
            description = desc_el.get_text(strip=True)[:2000] if desc_el else ""

            full_text = f"{title} {description} {deadline}"
            funding_type = self.detect_funding_type(full_text)

            return {
                "title": title,
                "university": university,
                "department": "",
                "supervisor": "",
                "region": "europe",
                "region_cn": "欧陆",
                "country": country,
                "funding_type": funding_type,
                "discipline": discipline,
                "deadline": deadline,
                "description": description,
                "url": url,
                "source": self.SOURCE_NAME,
            }
        except Exception as e:
            logger.error(f"[EURAXESS] Error parsing listing: {e}")
            return {}
