#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Directory Scraper Module

This module provides an abstract base class for scraping public business directories.
"""
import logging
import time
import random
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class DirectoryScraper(BaseScraper, ABC):
    """
    Abstract base class for public directory scrapers.
    Extends BaseScraper to share common functionality.
    """
    def __init__(self,
                 request_delay: float = 2.0,
                 random_delay_range: Optional[Tuple[float, float]] = (1.0, 3.0),
                 max_results: int = 100):
        super().__init__(
            request_delay=request_delay,
            random_delay_range=random_delay_range,
            max_results=max_results
        )

    @abstractmethod
    def build_search_url(self, query: str, location: str = "") -> str:
        """
        Construct the URL for searching the directory with given query and location.

        Args:
            query: Search term (e.g., "restaurantes")
            location: Optional location to filter results
        Returns:
            Fully formed search URL
        """
        pass

    @abstractmethod
    def parse_listing(self, html_element) -> Optional[Dict[str, Any]]:
        """
        Parse a single listing element and extract business data.

        Args:
            html_element: Element object representing a listing
        Returns:
            Dictionary with business data or None if parsing fails
        """
        pass

    def scrape(self, query: str, location: str = "") -> List[Dict[str, Any]]:
        """
        Core scraping method for directory.
        Coordinates navigation, pagination and parsing.

        Args:
            query: Search term
            location: Location filter
        Returns:
            List of dictionaries with scraped data
        """
        self.results = []
        try:
            url = self.build_search_url(query, location)
            logger.info(f"Navigating to: {url}")
            if not self._ensure_driver():
                return []
            self.driver.get(url)
            time.sleep(random.uniform(*self.random_delay_range))

            listings = self.get_listings()
            for count, elem in enumerate(listings, 1):
                if count > self.max_results:
                    break
                data = self.parse_listing(elem)
                if data:
                    self.results.append(data)
                time.sleep(random.uniform(self.request_delay, self.request_delay + (self.random_delay_range[1] if self.random_delay_range else 0)))

            self.clean_results()
            return self.results

        except Exception as e:
            logger.error(f"Error scraping directory: {e}")
            return []

    def get_listings(self) -> List[Any]:
        """
        Retrieve the current page's listing elements.  
        Should be overridden if necessary.

        Returns:
            List of element objects representing listings
        """
        # Default implementation: find elements by common selector
        try:
            return self.driver.find_elements_by_css_selector('div.listing')  # placeholder
        except Exception:
            return []
