"""Scheduler for daily PhD collection tasks."""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import SCRAPE_HOUR, SCRAPE_MINUTE
from collector import run_collection

logger = logging.getLogger(__name__)


def create_scheduler() -> BackgroundScheduler:
    """Create and configure the background scheduler."""
    scheduler = BackgroundScheduler()

    # Daily scrape job
    scheduler.add_job(
        run_collection,
        trigger=CronTrigger(hour=SCRAPE_HOUR, minute=SCRAPE_MINUTE),
        id="daily_phd_scrape",
        name="Daily PhD Project Collection",
        replace_existing=True,
        misfire_grace_time=3600,  # Allow 1 hour grace period
    )

    logger.info(f"Scheduler configured: daily at {SCRAPE_HOUR:02d}:{SCRAPE_MINUTE:02d}")
    return scheduler


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started. Press Ctrl+C to exit.")
    try:
        import time
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped.")
