"""Global configuration for PhD Collector."""

import os

# Database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "phd_projects.db")
DB_URL = f"sqlite:///{DB_PATH}"

# Scraper settings
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 2  # seconds between requests
MAX_RETRIES = 3

# Regions
REGIONS = {
    "europe": "欧陆",
    "australia": "澳洲",
    "north_america": "北美",
}

# Funding types keywords
FUNDING_KEYWORDS = {
    "fully_funded": ["fully funded", "full scholarship", "fully-funded", "full funding"],
    "csc": ["csc", "china scholarship council", "chinese government scholarship"],
    "rolling": ["rolling", "open until filled", "no deadline", "rolling basis"],
    "position": ["research position", "paid position", "employed", "salary", "岗位制"],
}

# FindAPhD region URLs
FINDAPHD_URLS = {
    "europe": "https://www.findaphd.com/phds/?Keywords=&Location=Europe&lg=&PFStatus=1",
    "australia": "https://www.findaphd.com/phds/?Keywords=&Location=Australia&lg=&PFStatus=1",
    "north_america": "https://www.findaphd.com/phds/?Keywords=&Location=North+America&lg=&PFStatus=1",
}

# EURAXESS (Europe focused)
EURAXESS_URL = "https://euraxess.ec.europa.eu/jobs/search/field_research_profile/first-stage-researcher-r1-446?page={page}"

# ScholarshipDb - use individual country URLs where regional ones fail
SCHOLARSHIPDB_URLS = {
    "europe": [
        "https://scholarshipdb.net/PhD-scholarships-in-Europe",
        "https://scholarshipdb.net/PhD-scholarships-in-Germany",
        "https://scholarshipdb.net/PhD-scholarships-in-Netherlands",
        "https://scholarshipdb.net/PhD-scholarships-in-Sweden",
        "https://scholarshipdb.net/PhD-scholarships-in-United-Kingdom",
    ],
    "australia": [
        "https://scholarshipdb.net/PhD-scholarships-in-Australia",
    ],
    "north_america": [
        "https://scholarshipdb.net/PhD-scholarships-in-Canada",
        "https://scholarshipdb.net/PhD-scholarships?q=PhD&l=United+States",
    ],
}

# Scheduler
SCRAPE_HOUR = 8  # Run daily at 8:00 AM
SCRAPE_MINUTE = 0
