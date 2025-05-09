#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cylex Scraper Module

This module provides a scraper class for extracting business data from Cylex directories
in Latin America.
"""

import time
import random
import logging
import re
import os
from typing import List, Dict, Any, Optional, Union, Tuple
from urllib.parse import quote_plus, urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementNotInteractableException,
    StaleElementReferenceException,
    WebDriverException
)
from selenium import webdriver

# Local imports
from scrapers.directory_scraper import DirectoryScraper
from utils.helpers import (
    get_random_user_agent,
    detect_captcha,
    simulate_human_behavior,
    clean_text,
    extract_phone_numbers,
    extract_emails,
    extract_urls
)

logger = logging.getLogger(__name__)

class CylexScraper(DirectoryScraper):
    """
    Scraper class for extracting business data from Cylex directories
    across Latin America.
    """
    
    def __init__(self, 
                 request_delay: float = 2.0,
                 random_delay_range: Optional[Tuple[float, float]] = (1.0, 3.0),
                 max_results: int = 100,
                 headless: bool = True,
                 use_browser_pool: bool = True,
                 country: str = "mx",  # Default to Mexico
                 **kwargs):  # Add **kwargs
        """
        Initialize the Cylex scraper.
        
        Args:
            request_delay: Base delay between requests in seconds
            random_delay_range: Tuple of (min, max) additional random delay
            max_results: Maximum number of results to scrape
            headless: Whether to run the browser in headless mode
            use_browser_pool: Whether to use the browser pool for better resource management
            country: Country code for the specific Cylex website (mx, ar, cl, co, etc.)
            **kwargs: Additional keyword arguments for the base class
        """
        super().__init__(
            request_delay=request_delay,
            random_delay_range=random_delay_range,
            max_results=max_results,
            headless=headless,
            use_browser_pool=use_browser_pool,
            **kwargs  # Pass **kwargs to super
        )
        
        self.country = country.lower()
        self._set_base_url()
        
    def get_cache_key_components(self) -> Dict[str, str]:
        """
        Get the components needed to generate a cache key for this scraper.
        
        Returns:
            Dictionary with components for cache key generation
        """
        return {
            'scraper_name': f"{self.__class__.__name__}_{self.country}"
        }
    
    def _set_base_url(self) -> None:
        """Set the base URL based on the selected country."""
        country_urls = {
            "mx": "https://www.cylex.com.mx",
            "ar": "https://www.cylex.com.ar",
            "cl": "https://www.cylex.cl",
            "co": "https://www.cylex.com.co",
            "pe": "https://www.cylex.com.pe",
            # Add more country URLs as needed
        }
        
        self.base_url = country_urls.get(self.country, country_urls["mx"])
        logger.info(f"Using Cylex URL for {self.country.upper()}: {self.base_url}")
    
    def build_search_url(self, query: str, location: str = "") -> str:
        """
        Construct the URL for searching the directory.
        
        Args:
            query: Search term (e.g., "restaurantes")
            location: Location to filter results (e.g., "CDMX")
            
        Returns:
            Fully formed search URL
        """
        # Encode the query and location for URL
        encoded_query = quote_plus(query)
        
        # Cylex typically uses different URL pattern
        if location:
            encoded_location = quote_plus(location)
            search_url = f"{self.base_url}/buscar?q={encoded_query}&loc={encoded_location}"
        else:
            search_url = f"{self.base_url}/buscar?q={encoded_query}"
        
        return search_url
    
    def get_listings(self) -> List[Any]:
        """
        Retrieve the current page's listing elements.
        
        Returns:
            List of WebElement objects representing business listings
        """
        try:
            # Wait for listings container to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".result-list, .searchresult, .resultlist"))
            )
            
            # Try different selectors for listing items
            listing_selectors = [
                ".result-list > .result-item",
                ".search-item",
                ".resultlist > .company",
                ".listing-item",
                "[data-testid='search-result-item']"
            ]
            
            for selector in listing_selectors:
                listings = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if listings:
                    logger.info(f"Found {len(listings)} listings using selector: {selector}")
                    return listings
            
            # If no listings found with the primary selectors, try more generic ones
            logger.warning("No listings found with primary selectors, trying alternatives")
            alternative_selector = "div[class*='result-item'], div[class*='company'], .item"
            listings = self.driver.find_elements(By.CSS_SELECTOR, alternative_selector)
            
            return listings
        except Exception as e:
            logger.error(f"Error getting Cylex listings: {e}")
            return []
    
    def parse_listing(self, html_element) -> Optional[Dict[str, Any]]:
        """
        Parse a single listing element and extract business data.
        
        Args:
            html_element: Selenium WebElement representing a listing
            
        Returns:
            Dictionary with business data or None if parsing fails
        """
        try:
            business_data = {
                "source": f"cylex_{self.country}",
                "scrape_date": time.strftime("%Y-%m-%d"),
                "name": None,
                "address": None,
                "phone": None,
                "website": None,
                "email": None,
                "category": None,
                "description": None,
                "rating": None,
                "review_count": None,
                "social_media": {}
            }
            
            # Extract business name
            name_selectors = [
                ".company-name", ".name", "h2", ".title",
                "[data-testid='company-name']", "a.companyname"
            ]
            
            for selector in name_selectors:
                try:
                    name_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    business_data["name"] = clean_text(name_elem.text)
                    break
                except NoSuchElementException:
                    continue
            
            # Extract address
            address_selectors = [
                ".company-address", ".address", ".location",
                "[data-testid='company-address']", ".companyaddress"
            ]
            
            for selector in address_selectors:
                try:
                    address_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    business_data["address"] = clean_text(address_elem.text)
                    break
                except NoSuchElementException:
                    continue
            
            # Extract phone
            phone_selectors = [
                ".company-phone", ".phone", ".tel",
                "[data-testid='company-phone']", ".companyphone"
            ]
            
            # Try explicit selectors first
            for selector in phone_selectors:
                try:
                    phone_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    business_data["phone"] = clean_text(phone_elem.text)
                    break
                except NoSuchElementException:
                    continue
            
            # If no explicit phone element, try to extract from all text
            if not business_data["phone"]:
                all_text = html_element.text
                phones = extract_phone_numbers(all_text)
                if phones:
                    business_data["phone"] = phones[0]  # Use the first extracted phone
            
            # Extract website
            website_selectors = [
                ".company-website", ".website", "a.web",
                "[data-testid='company-website']", ".companyweb",
                "a[href^='http']"
            ]
            
            for selector in website_selectors:
                try:
                    website_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    website_url = website_elem.get_attribute("href")
                    
                    # Some Cylex sites use redirects, check if it's an internal or external link
                    if website_url and not website_url.startswith(self.base_url):
                        business_data["website"] = website_url
                    elif website_url and "/redirect?" in website_url:
                        # This is likely a redirect URL, extract the actual URL if possible
                        # For simplicity, we'll use the redirect URL directly
                        business_data["website"] = website_url
                    break
                except NoSuchElementException:
                    continue
            
            # Extract email from text or elements
            email_selectors = [
                ".company-email", ".email", 
                "[data-testid='company-email']", ".companyemail"
            ]
            
            for selector in email_selectors:
                try:
                    email_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    email_text = email_elem.text
                    emails = extract_emails(email_text)
                    if emails:
                        business_data["email"] = emails[0]
                    break
                except Exception:
                    # Treat any exception as missing element
                    continue
            
            # If no explicit email element, try to extract from all text
            if not business_data["email"]:
                all_text = html_element.text
                emails = extract_emails(all_text)
                if emails:
                    business_data["email"] = emails[0]
            
            # Extract category
            category_selectors = [
                ".company-category", ".category", ".segment",
                "[data-testid='company-category']", ".companycategory"
            ]
            
            for selector in category_selectors:
                try:
                    category_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    business_data["category"] = clean_text(category_elem.text)
                    break
                except NoSuchElementException:
                    continue
            
            # Extract description (if available)
            description_selectors = [
                ".company-description", ".description", ".snippet",
                "[data-testid='company-description']", ".companydescription"
            ]
            for selector in description_selectors:
                try:
                    desc_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    business_data["description"] = clean_text(desc_elem.text)
                    break
                except Exception:
                    # Treat any exception as missing element
                    continue
            
            # Extract rating (if available)
            rating_selectors = [
                ".company-rating", ".rating", ".stars",
                "[data-testid='company-rating']", ".stars-container"
            ]
            
            for selector in rating_selectors:
                try:
                    rating_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    
                    # Try to extract numeric rating
                    rating_text = rating_elem.text
                    if rating_text:
                        # Extract numeric values from rating text
                        rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
                        if rating_match:
                            business_data["rating"] = float(rating_match.group(1))
                    
                    # Alternative: Try to extract from star class or attributes
                    if not business_data["rating"]:
                        # Some sites use class names or data attributes for ratings
                        rating_value = rating_elem.get_attribute("data-rating")
                        if rating_value:
                            try:
                                business_data["rating"] = float(rating_value)
                            except ValueError:
                                pass
                    
                    break
                except NoSuchElementException:
                    continue
            
            # Return only if we have at least a name or a phone
            if business_data["name"] or business_data["phone"]:
                return business_data
            else:
                logger.warning("Skipping Cylex listing - could not extract name or phone")
                return None
            
        except Exception as e:
            logger.error(f"Error parsing Cylex listing: {e}")
            return None
    
    def handle_pagination(self) -> bool:
        """
        Go to the next page of results if available.
        Uses intelligent waiting to detect page changes.
        
        Returns:
            True if successfully navigated to next page, False otherwise
        """
        from utils.helpers import wait_for_element, wait_for_page_change
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
        
        try:
            # Store a reference element for stale checking
            reference_elements = self.driver.find_elements(By.CSS_SELECTOR, 'body')
            reference_element = reference_elements[0] if reference_elements else None
            
            # Store initial URL for change detection
            initial_url = self.driver.current_url
            
            # Look for pagination controls
            pagination_selectors = [
                "a.next", ".pagination a[rel='next']", 
                ".next-page", "[data-testid='pagination-next']",
                "a[aria-label='Next']", ".pagenavigation a.next",
                "li.next a", "#pagination-next", 
                "a[title='Siguiente página']",
                ".pagination .arrow.next"
            ]
            
            for selector in pagination_selectors:
                try:
                    # Use intelligent waiting to find the element
                    next_page = wait_for_element(
                        self.driver,
                        selector,
                        timeout=5,
                        condition='clickable'
                    )
                    
                    if next_page and next_page.is_displayed() and next_page.is_enabled():
                        logger.info(f"Found next page button with selector: {selector}")
                        
                        # Scroll into view for better click reliability
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", 
                            next_page
                        )
                        
                        # Small wait after scrolling
                        time.sleep(0.5)
                        
                        # Click the button
                        next_page.click()
                        
                        # Use intelligent waiting to detect page change
                        if wait_for_page_change(
                            self.driver, 
                            timeout=10, 
                            reference_element=reference_element,
                            url_change=(initial_url != self.driver.current_url)
                        ):
                            logger.info("Successfully navigated to next page in Cylex")
                            
                            # Apply rate limiting to be polite to the server
                            self.rate_limit()
                            
                            return True
                except NoSuchElementException:
                    continue
                except ElementNotInteractableException:
                    logger.warning(f"Next page button with selector '{selector}' is not interactive")
                    continue
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            logger.info("No more Cylex pages available or next button not found")
            return False
            
        except Exception as e:
            logger.error(f"Error handling Cylex pagination: {e}")
            return False
    
    def scrape(self, query: str, location: str = "") -> List[Dict[str, Any]]:
        """
        Core scraping method for Cylex.
        Uses cache and intelligent waiting for optimized performance.
        
        Args:
            query: Search term (e.g., "restaurantes")
            location: Location filter (e.g., "CDMX")
            
        Returns:
            List of dictionaries with scraped data
        """
        from utils.helpers import wait_for_element, wait_for_elements
        
        # First check the cache
        cached_results = self.get_cached_results(query, location)
        if cached_results:
            logger.info(f"Using cached results for query='{query}', location='{location}'")
            return cached_results
            
        self.results = []
        try:
            url = self.build_search_url(query, location)
            logger.info(f"Navigating to Cylex: {url}")
            
            # Initialize browser if needed
            if not self.init_browser():
                logger.error("Failed to initialize browser")
                return []
            
            # Navigate to the search URL with error handling
            try:
                self.driver.get(url)
                # Use intelligent waiting for page load
                wait_for_element(self.driver, "body", timeout=10, condition='presence')
            except Exception as e:
                logger.error(f"Error navigating to Cylex search URL: {e}")
                return []
            
            # Apply rate limiting
            self.rate_limit()
            
            # Check for CAPTCHA
            if detect_captcha(self.driver.page_source):
                logger.warning("CAPTCHA detected on initial Cylex page load")
                return []
            
            # Process pages with intelligent pagination
            page = 1
            max_pages = 10  # Limit to prevent infinite loops
            
            while page <= max_pages and len(self.results) < self.max_results:
                logger.info(f"Processing Cylex page {page}")
                
                # Get and process listings with intelligent waiting
                listings = self.get_listings()
                if not listings:
                    logger.warning(f"No listings found on Cylex page {page}")
                    break
                
                # Process each listing on the current page
                for count, listing in enumerate(listings, 1):
                    if len(self.results) >= self.max_results:
                        logger.info(f"Reached maximum results limit ({self.max_results})")
                        break
                    
                    # Extract data from listing
                    data = self.parse_listing(listing)
                    if data:
                        self.results.append(data)
                    
                    # Use intelligent rate limiting between processing listings
                    # Smaller scale for intra-page requests
                    self.rate_limit(scale=0.3)
                
                # Try to go to next page if we haven't reached the max results
                if len(self.results) < self.max_results:
                    if not self.handle_pagination():
                        logger.info("No more Cylex pages available")
                        break
                    page += 1
                    # Apply a longer rate limit between pages (higher scale factor)
                    self.rate_limit(scale=1.5)
            
            # Clean the results
            self.clean_results()
            
            # Store results in cache for future use
            self.save_results_to_cache(query, location)
            
            logger.info(f"Scraped {len(self.results)} listings from Cylex {self.country.upper()}")
            return self.results
            
        except Exception as e:
            logger.error(f"Error scraping Cylex: {e}")
            return []
        finally:
            # Release browser back to pool instead of quitting
            self.close()
