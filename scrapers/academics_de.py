"""Scraper for academics.de - Germany's largest academic job platform."""

import logging
import re
from typing import List, Dict

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# PhD (Doktorand) positions search page
ACADEMICS_DE_URL = (
    "https://www.academics.de/stellenanzeigen/position-doktorand/UQ==?page={page}"
)


class AcademicsDeScraper(BaseScraper):
    """Scrape PhD positions from academics.de (German academic jobs)."""

    SOURCE_NAME = "academics.de"
    BASE_URL = "https://www.academics.de"
    MAX_PAGES = 3

    def scrape(self) -> List[Dict]:
        """Scrape PhD positions from academics.de."""
        all_projects = []
        seen_urls = set()
        for page in range(1, self.MAX_PAGES + 1):
            url = ACADEMICS_DE_URL.format(page=page)
            logger.info(f"[academics.de] Scraping page {page}")
            soup = self.fetch_page(url)
            if not soup:
                break

            # Listings are <a> tags linking to /jobs/ pages
            listings = soup.select("a[href*='/jobs/']")
            if not listings:
                logger.warning(f"[academics.de] No listings found on page {page}")
                break

            for item in listings:
                href = item.get("href", "")
                if href in seen_urls or not href:
                    continue
                project = self._parse_listing(item)
                if project and project.get("url"):
                    if project["url"] not in seen_urls:
                        seen_urls.add(project["url"])
                        all_projects.append(project)

            logger.info(f"[academics.de] Page {page}: found {len(listings)} links")

        logger.info(f"[academics.de] Total found: {len(all_projects)} projects")
        return all_projects

    def _parse_listing(self, item) -> Dict:
        """Parse a single academics.de listing link element."""
        try:
            href = item.get("href", "")
            if not href or "/jobs/" not in href:
                return {}
            url = href if href.startswith("http") else self.BASE_URL + href

            # Extract text content - academics.de puts title, university, city, date
            # as text nodes within the <a> block
            full_text = item.get_text(" ", strip=True)
            if not full_text or len(full_text) < 10:
                return {}

            # Title is typically the first significant text block
            # Look for heading elements inside the link
            title_el = item.select_one("h2, h3, h4, strong, span")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                # Fallback: use first line of text
                lines = [l.strip() for l in item.stripped_strings]
                title = lines[0] if lines else ""

            if not title or len(title) < 5:
                return {}

            # University: often the second text block
            lines = [l.strip() for l in item.stripped_strings if l.strip()]
            university = ""
            city = ""
            deadline = ""
            # Skip the title line, look for university/city/date
            for i, line in enumerate(lines):
                if line == title:
                    continue
                # Date pattern: DD.MM.YYYY
                if re.match(r"\d{2}\.\d{2}\.\d{4}", line):
                    deadline = line
                elif not university:
                    university = line
                elif not city:
                    city = line

            # Detect discipline from title
            discipline = self._detect_discipline(f"{title} {university}")

            funding_type = self.detect_funding_type(full_text)

            return {
                "title": title,
                "university": university,
                "department": "",
                "supervisor": "",
                "region": "europe",
                "region_cn": "欧陆",
                "country": "Germany",
                "funding_type": funding_type,
                "discipline": discipline,
                "deadline": deadline,
                "description": "",
                "url": url,
                "source": self.SOURCE_NAME,
            }
        except Exception as e:
            logger.error(f"[academics.de] Error parsing listing: {e}")
            return {}

    @staticmethod
    def _detect_discipline(text: str) -> str:
        """Detect discipline from text using keyword matching."""
        text_lower = text.lower()
        disciplines = {
            "Computer Science": ["computer science", "machine learning", "artificial intelligence", "software", "informatik", "data science"],
            "Engineering": ["engineering", "ingenieur", "mechanical", "electrical", "maschinenbau", "elektrotechnik", "robotics"],
            "Biology": ["biology", "biolog", "genomic", "molecular", "neuroscience", "biomedical"],
            "Physics": ["physics", "physik", "quantum", "astrophysics", "photonic"],
            "Chemistry": ["chemistry", "chemie", "chemical", "katalyse", "catalysis", "polymer"],
            "Mathematics": ["mathematics", "mathematik", "statistics", "statistik"],
            "Medicine": ["medicine", "medizin", "clinical", "klinisch", "cancer", "pharma", "health", "gesundheit"],
            "Environmental Science": ["environment", "umwelt", "climate", "klima", "sustainability", "nachhaltig", "energy", "energie"],
            "Social Sciences": ["social", "sozial", "psychology", "psychologie", "education", "bildung", "pädagog", "political", "politik"],
            "Business": ["business", "management", "finance", "wirtschaft", "ökonomie"],
            "Law": ["law", "recht", "jura", "legal"],
        }
        found = []
        for disc, keywords in disciplines.items():
            if any(kw in text_lower for kw in keywords):
                found.append(disc)
        return ", ".join(found[:2]) if found else ""
