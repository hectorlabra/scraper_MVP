#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Scraper Module

This module provides a base class for all scrapers with common functionality.
"""

import logging
import time
import random
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base abstract class that all scrapers should inherit from."""
    
    def __init__(self, 
                 request_delay: float = 2.0,
                 random_delay_range: Optional[tuple] = (1.0, 3.0),
                 max_results: int = 100):
        """
        Initialize the base scraper with common configuration.
        
        Args:
            request_delay: Base delay between requests in seconds
            random_delay_range: Tuple of (min, max) additional random delay
            max_results: Maximum number of results to scrape
        """
        self.request_delay = request_delay
        self.random_delay_range = random_delay_range
        self.max_results = max_results
        self.results = []
        
    def delay_request(self):
        """Add a delay between requests to avoid rate limiting."""
        delay = self.request_delay
        if self.random_delay_range:
            min_extra, max_extra = self.random_delay_range
            delay += random.uniform(min_extra, max_extra)
        
        logger.debug(f"Delaying for {delay:.2f} seconds")
        time.sleep(delay)
    
    @abstractmethod
    def scrape(self, query: str, location: str = "") -> List[Dict[str, Any]]:
        """
        Abstract method to scrape data based on query and location.
        
        Args:
            query: Search term to scrape
            location: Location to search within (if applicable)
            
        Returns:
            List of dictionaries containing scraped data
        """
        pass
    
    def clean_results(self) -> None:
        """Clean the scraped results (basic cleaning, can be overridden)."""
        # Basic cleaning that applies to all scrapers
        cleaned_results = []
        for result in self.results:
            # Remove empty values
            cleaned_result = {k: v for k, v in result.items() if v}
            if cleaned_result:
                cleaned_results.append(cleaned_result)
        
        self.results = cleaned_results
        
    def get_results(self) -> List[Dict[str, Any]]:
        """
        Get the scraped and cleaned results.
        
        Returns:
            List of dictionaries containing scraped data
        """
        return self.results
