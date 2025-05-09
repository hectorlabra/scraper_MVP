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
from typing import List, Dict, Any, Optional, Union
from selenium.webdriver.chrome.webdriver import WebDriver

# Import browser pool manager
from utils.browser_pool import get_browser_pool, ManagedBrowser, BrowserConfig
from utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base abstract class that all scrapers should inherit from."""
    
    # Version for cache tracking
    VERSION = '1.1'
    
    def __init__(self, 
                 request_delay: float = 2.0,
                 random_delay_range: Optional[tuple] = (1.0, 3.0),
                 max_results: int = 100,
                 headless: bool = True,
                 use_browser_pool: bool = True,
                 use_cache: bool = True):
        """
        Initialize the base scraper with common configuration.
        
        Args:
            request_delay: Base delay between requests in seconds
            random_delay_range: Tuple of (min, max) additional random delay
            max_results: Maximum number of results to scrape
            headless: Whether to run the browser in headless mode
            use_browser_pool: Whether to use the browser pool (recommended for efficiency)
            use_cache: Whether to use caching system
        """
        self.request_delay = request_delay
        self.random_delay_range = random_delay_range
        self.max_results = max_results
        self.headless = headless
        self.use_browser_pool = use_browser_pool
        self.use_cache = use_cache
        self.results = []
        self.used_cache = False
        
        # For browser pool usage
        self.driver = None
        self.managed_browser = None
        
    def rate_limit(self, scale: float = 1.0) -> None:
        """
        Add a smarter delay between requests based on context.
        
        Args:
            scale: Scale factor to apply to the delay (0.5 = half, 2.0 = double)
        """
        # Base delay from configuration
        delay = self.request_delay * scale
        
        # Add randomness to appear more human-like
        if self.random_delay_range:
            min_extra, max_extra = self.random_delay_range
            # Scale the random component as well
            scaled_min = min_extra * scale
            scaled_max = max_extra * scale
            delay += random.uniform(scaled_min, scaled_max)
        
        # Apply further randomization occasionally to simulate human behavior
        if random.random() < 0.1:  # 10% chance
            # Add an extra random pause (human distraction simulation)
            delay += random.uniform(0.5, 2.0)
        
        logger.debug(f"Rate limiting: waiting {delay:.2f} seconds")
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
        
    def get_driver(self) -> Optional[WebDriver]:
        """
        Get a WebDriver instance, either from the browser pool or by creating a new one.
        This method should be called by subclasses that need a browser.
        
        Returns:
            WebDriver instance or None if failed
        """
        if self.driver:
            return self.driver
            
        if self.use_browser_pool:
            # Get browser from pool
            browser_pool = get_browser_pool()
            
            # Configure browser for this scraper
            browser_config = BrowserConfig(
                headless=self.headless,
                page_load_strategy="eager"  # Faster page loading
            )
            
            # Get managed browser from pool
            self.managed_browser = browser_pool.get_browser(browser_config)
            
            if self.managed_browser:
                self.driver = self.managed_browser.driver
                return self.driver
            else:
                logger.error("Failed to get browser from pool")
                return None
        else:
            # Subclasses should implement their own driver creation if not using pool
            raise NotImplementedError("Direct browser creation should be implemented by subclass")
    
    def close(self) -> None:
        """
        Close the browser and free resources.
        Should be called when scraping is complete.
        """
        if self.managed_browser:
            # Release browser back to the pool
            browser_pool = get_browser_pool()
            browser_pool.release_browser(self.managed_browser)
            self.managed_browser = None
            self.driver = None
        elif self.driver:
            # Direct cleanup if not using pool
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error closing browser: {str(e)}")
            finally:
                self.driver = None
    
    def get_cache_key_components(self) -> Dict[str, str]:
        """
        Get the components needed to generate a cache key for this scraper.
        Override this in subclasses if needed for more specific caching.
        
        Returns:
            Dictionary with components for cache key generation
        """
        return {
            'scraper_name': self.__class__.__name__
        }
    
    def try_cache_first(self, query: str, location: str = "") -> Optional[List[Dict[str, Any]]]:
        """
        Try to get results from cache before scraping.
        
        Args:
            query: Search query
            location: Location filter
            
        Returns:
            Cached results if available, None otherwise
        """
        cache_components = self.get_cache_key_components()
        scraper_name = cache_components.get('scraper_name')
        
        cache_manager = get_cache_manager()
        cached_results = cache_manager.get_cached_data(scraper_name, query, location)
        
        if cached_results:
            logger.info(f"Using cached results for {scraper_name} query='{query}', location='{location}'")
            self.results = cached_results
            self.used_cache = True
        else:
            self.used_cache = False
            
        return cached_results
    
    def save_to_cache(self, query: str, location: str, results: List[Dict[str, Any]]) -> bool:
        """
        Save scraped results to cache.
        
        Args:
            query: Search query
            location: Location filter
            results: Scraped results to cache
            
        Returns:
            True if successfully saved, False otherwise
        """
        if not results:
            return False
            
        cache_components = self.get_cache_key_components()
        scraper_name = cache_components.get('scraper_name')
        
        # Add metadata for cache optimization
        metadata = {
            "scraper_version": getattr(self, 'VERSION', '1.0'),
            "timestamp_utc": time.time(),
            "result_count": len(results),
            "query_info": {
                "original_query": query,
                "location": location
            }
        }
        
        cache_manager = get_cache_manager()
        return cache_manager.save_to_cache(scraper_name, query, location, results, metadata)
    
    def save_results_to_cache(self, query: str, location: str = "") -> bool:
        """
        Save the current scraped results to cache using existing save_to_cache logic.
        """
        return self.save_to_cache(query, location, self.results)
    
    def process_data_in_batches(self, data_list: List[Dict[str, Any]], batch_size: int = 50) -> List[Dict[str, Any]]:
        """
        Process large datasets in batches to optimize memory usage.
        
        Args:
            data_list: List of data items to process
            batch_size: Number of items to process in each batch
            
        Returns:
            Processed list of data items
        """
        if not data_list:
            return []
            
        result = []
        total_items = len(data_list)
        
        # Process in batches to save memory
        for i in range(0, total_items, batch_size):
            batch = data_list[i:i+batch_size]
            processed_batch = self._process_batch(batch)
            result.extend(processed_batch)
            
            # Log progress for large datasets
            logger.debug(f"Processed batch {i//batch_size + 1}/{(total_items+batch_size-1)//batch_size} ({len(processed_batch)} items)")
            
        return result
        
    def _process_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a single batch of data. Override in subclasses for specific processing.
        
        Args:
            batch: Batch of data items to process
            
        Returns:
            Processed batch
        """
        # Default implementation just returns the batch
        # Subclasses should override this for specific processing
        return batch
        
    def incremental_update(self, query: str, location: str, 
                           force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Perform an incremental update by comparing with cached data.
        Only fetch what has changed or is missing.
        
        Args:
            query: Search query
            location: Location filter
            force_refresh: Whether to force a full refresh
            
        Returns:
            Updated list of results
        """
        if not self.use_cache or force_refresh:
            # If cache is disabled or forced refresh, just do a full scrape
            return self.scrape(query, location)
            
        # Try to get cached data
        cached_results = self.try_cache_first(query, location)
        
        if not cached_results:
            # No cache available, do a full scrape
            return self.scrape(query, location)
            
        # We have cached results, try incremental update
        # This is a base implementation - subclasses may override with more
        # sophisticated incremental update logic
        
        # For base implementation, we'll use the cached results but update the timestamp
        self.results = cached_results
        
        # Save with updated timestamp
        self.save_to_cache(query, location, self.results)
        
        return self.results
        
    def get_cached_results(self, query: str, location: str = "") -> Optional[List[Dict[str, Any]]]:
        """
        Get results from cache without marking them as used.
        Useful for checking if cache exists without using it.
        
        Args:
            query: Search query
            location: Location filter
            
        Returns:
            Cached results if available, None otherwise
        """
        if not self.use_cache:
            return None
            
        cache_components = self.get_cache_key_components()
        scraper_name = cache_components.get('scraper_name')
        
        cache_manager = get_cache_manager()
        return cache_manager.get_cached_data(scraper_name, query, location)
        
    def has_valid_cache(self, query: str, location: str = "") -> bool:
        """
        Check if a valid (non-expired) cache exists for this query.
        
        Args:
            query: Search query
            location: Location filter
            
        Returns:
            True if valid cache exists, False otherwise
        """
        return self.get_cached_results(query, location) is not None
