"""Main collector engine - orchestrates scraping, cleaning, and storage."""

import logging
from datetime import datetime
from typing import List, Dict

from sqlalchemy.exc import IntegrityError

from models import PhDProject, get_session, init_db
from scrapers import EuraxessScraper, ScholarshipDbScraper

logger = logging.getLogger(__name__)


class PhDCollector:
    """Orchestrates the PhD project collection pipeline."""

    def __init__(self):
        init_db()
        self.scrapers = [
            EuraxessScraper(),
            ScholarshipDbScraper(),
        ]

    def run(self) -> Dict:
        """Run full collection pipeline. Returns stats dict."""
        logger.info("=" * 60)
        logger.info(f"Collection started at {datetime.now().isoformat()}")
        logger.info("=" * 60)

        stats = {"total_scraped": 0, "new_saved": 0, "duplicates": 0, "errors": 0}

        for scraper in self.scrapers:
            source = scraper.SOURCE_NAME
            logger.info(f"Running scraper: {source}")
            try:
                raw_projects = scraper.scrape()
                stats["total_scraped"] += len(raw_projects)

                cleaned = self._clean_projects(raw_projects)
                saved, dupes = self._save_projects(cleaned)
                stats["new_saved"] += saved
                stats["duplicates"] += dupes

                logger.info(f"[{source}] Scraped: {len(raw_projects)}, Saved: {saved}, Dupes: {dupes}")
            except Exception as e:
                stats["errors"] += 1
                logger.error(f"[{source}] Scraper failed: {e}", exc_info=True)

        logger.info(f"Collection complete. Stats: {stats}")
        return stats

    def _clean_projects(self, projects: List[Dict]) -> List[Dict]:
        """Clean and validate project data."""
        cleaned = []
        for p in projects:
            if not p:
                continue
            if not p.get("title") or not p.get("url"):
                continue
            # Strip whitespace from all string fields
            for key, val in p.items():
                if isinstance(val, str):
                    p[key] = val.strip()
            # Normalize URL
            p["url"] = p["url"].split("?utm")[0]  # Remove tracking params
            cleaned.append(p)
        return cleaned

    def _save_projects(self, projects: List[Dict]) -> tuple:
        """Save projects to database with deduplication. Returns (saved_count, dupe_count)."""
        session = get_session()
        saved = 0
        dupes = 0

        try:
            for p in projects:
                # Check if URL already exists
                existing = session.query(PhDProject).filter_by(url=p["url"]).first()
                if existing:
                    # Update if data changed
                    changed = False
                    for field in ["deadline", "funding_type", "description"]:
                        new_val = p.get(field, "")
                        if new_val and getattr(existing, field) != new_val:
                            setattr(existing, field, new_val)
                            changed = True
                    if changed:
                        existing.updated_at = datetime.utcnow()
                    dupes += 1
                    continue

                project = PhDProject(
                    title=p.get("title", ""),
                    university=p.get("university", ""),
                    department=p.get("department", ""),
                    supervisor=p.get("supervisor", ""),
                    region=p.get("region", ""),
                    region_cn=p.get("region_cn", ""),
                    country=p.get("country", ""),
                    funding_type=p.get("funding_type", "unknown"),
                    discipline=p.get("discipline", ""),
                    deadline=p.get("deadline", ""),
                    description=p.get("description", ""),
                    url=p.get("url", ""),
                    source=p.get("source", ""),
                    is_new=True,
                    collected_at=datetime.utcnow(),
                )
                session.add(project)
                saved += 1

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
        finally:
            session.close()

        return saved, dupes


def run_collection():
    """Entry point for scheduled collection."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    collector = PhDCollector()
    return collector.run()


if __name__ == "__main__":
    run_collection()
