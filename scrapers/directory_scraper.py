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
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from scrapers.base_scraper import BaseScraper
from utils.browser_pool import get_browser_pool, BrowserConfig
from utils.helpers import wait_for_element, wait_for_elements

logger = logging.getLogger(__name__)


class DirectoryScraper(BaseScraper, ABC):
    def init_browser(self) -> bool:
        """
        Initialize browser session.
        
        Returns:
            True if browser was initialized successfully, False otherwise
        """
        self.driver = self.get_driver()
        return self.driver is not None

    """
    Abstract base class for public directory scrapers.
    Extends BaseScraper to share common functionality.
    """
    def __init__(self,
                 request_delay: float = 2.0,
                 random_delay_range: Optional[Tuple[float, float]] = (1.0, 3.0),
                 max_results: int = 100,
                 headless: bool = True,
                 use_browser_pool: bool = True,
                 use_cache: bool = True,
                 **kwargs):
        super().__init__(
            request_delay=request_delay,
            random_delay_range=random_delay_range,
            max_results=max_results,
            headless=headless,
            use_browser_pool=use_browser_pool,
            use_cache=use_cache,
            **kwargs
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

    def _ensure_driver(self) -> bool:
        """
        Ensure browser driver is initialized.
        This implementation uses the browser pool from BaseScraper.
        
        Returns:
            True if driver is ready, False otherwise
        """
        try:
            if not self.driver:
                self.driver = self.get_driver()
            return self.driver is not None
        except Exception as e:
            logger.error(f"Failed to get driver: {e}")
            return False

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
        # First, try to get results from cache
        cached_results = self.try_cache_first(query, location)
        if cached_results is not None:
            logger.info(f"Using cached results for query: {query}, location: {location}")
            self.results = cached_results
            return self.results
            
        # No cache hit, proceed with scraping
        self.results = []
        try:
            url = self.build_search_url(query, location)
            logger.info(f"Navigating to: {url}")
            if not self._ensure_driver():
                return []
                
            # Navigate to the search URL
            self.driver.get(url)
            
            # Page content has loaded - now wait for listings
            page_loaded = wait_for_element(
                self.driver, 
                'body', 
                timeout=15, 
                condition='presence'
            )
            
            if not page_loaded:
                logger.warning(f"Page didn't load properly for URL: {url}")
            
            # Get listings with intelligent waiting
            listings = self.get_listings()
            
            # Process listings
            for count, elem in enumerate(listings, 1):
                if count > self.max_results:
                    logger.info(f"Reached maximum results limit: {self.max_results}")
                    break
                    
                data = self.parse_listing(elem)
                if data:
                    self.results.append(data)
                    
                # Add intelligent delay between processing items
                # Varied delay to appear more human-like
                time.sleep(random.uniform(
                    self.request_delay * 0.7,  # Slightly faster minimum 
                    self.request_delay + (self.random_delay_range[1] if self.random_delay_range else 0)
                ))

            self.clean_results()
            logger.info(f"Successfully scraped {len(self.results)} listings")
            
            # Save results to cache
            if self.results:
                self.save_to_cache(query, location, self.results)
                
            return self.results

        except Exception as e:
            logger.error(f"Error scraping directory: {e}")
            return []
        finally:
            # Release driver back to pool instead of quitting
            self.close()

    def get_listings(self) -> List[Any]:
        """
        Retrieve the current page's listing elements.  
        Should be overridden if necessary.

        Returns:
            List of element objects representing listings
        """
        # Default implementation using intelligent waiting
        try:
            # Common selectors for business listings
            selectors = [
                'div.listing', 
                '.business-listing', 
                '.business-item',
                '.search-result',
                '.result-item',
                'div.company'
            ]
            
            # Try each selector with intelligent waiting
            for selector in selectors:
                # Wait for elements with the current selector
                elements = wait_for_elements(
                    self.driver, 
                    selector, 
                    timeout=10, 
                    condition='presence'
                )
                
                if elements:
                    logger.info(f"Found {len(elements)} listings with selector: {selector}")
                    return elements
            
            # If no matches with common selectors, log warning and try a generic approach
            logger.warning("No listings found with common selectors, trying generic approach")
            
            # Try to find any repeating patterns that might be listings
            elements = wait_for_elements(
                self.driver, 
                'div[class*="list"], div[class*="result"], article, div[class^="card"]', 
                timeout=5
            )
            
            return elements or []
            
        except Exception as e:
            logger.debug(f"Failed to get listings: {e}")
            return []
        
    def handle_pagination(self) -> bool:
        """
        Handle pagination to load more results.
        This is a generic implementation that tries common patterns.
        Subclasses can override this for directory-specific pagination.
        
        Returns:
            True if successfully moved to next page, False otherwise
        """
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
        from utils.helpers import wait_for_element, wait_for_page_change
        
        try:
            # Store a reference element for stale checking
            reference_elements = self.driver.find_elements(By.CSS_SELECTOR, 'body')
            reference_element = reference_elements[0] if reference_elements else None
            
            # Store initial URL for change detection
            initial_url = self.driver.current_url
            
            # Common selectors for pagination "next" buttons
            pagination_selectors = [
                ".pagination .next a", 
                ".pagination a[rel='next']",
                "a.next-page", 
                "li.next a",
                ".next a",
                "a.pager-next",
                "a[aria-label='Next']",
                "a[aria-label='Siguiente']",
                "a > span.next",
                ".pager-next",
                "a[title='Next page']",
                "[data-role='next']",
                "a:contains('Next')",
                "a:contains('Siguiente')"
            ]
            
            # Try each selector
            for selector in pagination_selectors:
                try:
                    # First check if the selector exists
                    next_button = wait_for_element(
                        self.driver, 
                        selector, 
                        timeout=3, 
                        condition='visibility'
                    )
                    
                    if next_button and next_button.is_displayed() and next_button.is_enabled():
                        logger.info(f"Found pagination next button with selector: {selector}")
                        
                        # Scroll into view for better click reliability
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", 
                            next_button
                        )
                        
                        # Small wait after scrolling
                        time.sleep(0.5)
                        
                        # Click the button
                        next_button.click()
                        
                        # Wait for page change using intelligent detection
                        if wait_for_page_change(
                            self.driver, 
                            timeout=10, 
                            reference_element=reference_element,
                            url_change=(initial_url != self.driver.current_url)
                        ):
                            logger.info("Successfully navigated to next page")
                            
                            # Apply rate limiting to be polite to the server
                            self.rate_limit()
                            
                            return True
                except NoSuchElementException:
                    continue
                except ElementNotInteractableException:
                    logger.debug(f"Element not interactable: {selector}")
                    continue
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
                    
            # If we reach here, we couldn't find/click any pagination elements
            logger.info("No more pages available or couldn't find pagination controls")
            return False
            
        except Exception as e:
            logger.error(f"Error handling pagination: {e}")
            return False
