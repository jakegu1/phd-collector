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

            # Structure: <li> has multiple <div>s
            #   div1: h4 > a (title)
            #   div2: <a>University</a> | <a class="text-success">Region</a> | <span>time</span>
            #   div3: <p>description</p>
            divs = item.find_all("div", recursive=False)

            # University & Country from second div
            university = ""
            country = ""
            if len(divs) >= 2:
                meta_div = divs[1]
                # University: first <a> (links to ?em=University-Name)
                uni_link = meta_div.find("a")
                if uni_link:
                    university = uni_link.get_text(strip=True)
                # Country/Region: <a class="text-success">
                country_link = meta_div.select_one("a.text-success")
                if country_link:
                    country = country_link.get_text(strip=True)

            # Description from third div
            description = ""
            desc_el = item.select_one("p") or item.select_one("small")
            if desc_el:
                description = desc_el.get_text(strip=True)[:2000]

            # Try to extract discipline from description keywords
            discipline = self._detect_discipline(f"{title} {description}")

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
                "discipline": discipline,
                "deadline": "",
                "description": description,
                "url": url,
                "source": self.SOURCE_NAME,
            }
        except Exception as e:
            logger.error(f"[ScholarshipDb] Error parsing listing: {e}")
            return {}

    @staticmethod
    def _detect_discipline(text: str) -> str:
        """Try to detect discipline from text using keyword matching."""
        text_lower = text.lower()
        disciplines = {
            "Computer Science": ["computer science", "machine learning", "artificial intelligence", "deep learning", "software", "data science", "computing", "informatics"],
            "Engineering": ["engineering", "mechanical", "electrical", "civil", "chemical engineering", "robotics"],
            "Biology": ["biology", "biolog", "genomic", "molecular", "cell biology", "ecology", "neuroscience", "biomedical"],
            "Physics": ["physics", "quantum", "astrophysics", "particle", "optics", "photonic"],
            "Chemistry": ["chemistry", "chemical", "catalysis", "polymer", "organic chemistry"],
            "Mathematics": ["mathematics", "mathematical", "statistics", "probability", "algebra"],
            "Medicine": ["medicine", "medical", "clinical", "cancer", "oncology", "cardiology", "pharma", "health"],
            "Environmental Science": ["environment", "climate", "sustainability", "ecology", "marine", "ocean"],
            "Social Sciences": ["social", "sociology", "psychology", "political", "economics", "education", "law", "policy"],
            "Business": ["business", "management", "marketing", "finance", "accounting", "entrepreneurship"],
            "Arts & Humanities": ["history", "philosophy", "literature", "linguistics", "cultural", "arts"],
        }
        found = []
        for disc, keywords in disciplines.items():
            if any(kw in text_lower for kw in keywords):
                found.append(disc)
        return ", ".join(found[:2]) if found else ""
