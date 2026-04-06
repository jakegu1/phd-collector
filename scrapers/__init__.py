"""PhD project scrapers."""

from scrapers.euraxess import EuraxessScraper
from scrapers.scholarshipdb import ScholarshipDbScraper
from scrapers.findaphd import FindAPhDScraper
from scrapers.academics_de import AcademicsDeScraper

__all__ = ["EuraxessScraper", "ScholarshipDbScraper", "FindAPhDScraper", "AcademicsDeScraper"]
