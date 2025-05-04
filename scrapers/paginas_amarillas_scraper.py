#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Páginas Amarillas Scraper Module

This module provides a scraper class for extracting business data from Páginas Amarillas (Yellow Pages).
"""

import time
import random
import logging
import re
import os
from typing import List, Dict, Any, Optional, Union, Tuple
from urllib.parse import quote_plus
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

class PaginasAmarillasScraper(DirectoryScraper):
    """
    Scraper class for extracting business data from Páginas Amarillas (Yellow Pages)
    across Latin America.
    """
    
    def __init__(self, 
                 request_delay: float = 2.0,
                 random_delay_range: Optional[Tuple[float, float]] = (1.0, 3.0),
                 max_results: int = 100,
                 headless: bool = False,
                 country: str = "mx"):  # Default to Mexico
        """
        Initialize the Páginas Amarillas scraper.
        
        Args:
            request_delay: Base delay between requests in seconds
            random_delay_range: Tuple of (min, max) additional random delay
            max_results: Maximum number of results to scrape
            headless: Whether to run the browser in headless mode
            country: Country code for the specific Páginas Amarillas website (mx, ar, cl, co, etc.)
        """
        super().__init__(
            request_delay=request_delay,
            random_delay_range=random_delay_range,
            max_results=max_results
        )
        
        self.headless = headless
        self.country = country.lower()
        self._set_base_url()
        
    def _set_base_url(self) -> None:
        """Set the base URL based on the selected country."""
        country_urls = {
            "mx": "https://www.paginasamarillas.com.mx",
            "ar": "https://www.paginasamarillas.com.ar",
            "cl": "https://www.amarillas.cl",
            "co": "https://www.paginasamarillas.com.co",
            "pe": "https://www.paginasamarillas.com.pe",
            # Add more country URLs as needed
        }
        
        self.base_url = country_urls.get(self.country, country_urls["mx"])
        logger.info(f"Using Páginas Amarillas URL for {self.country.upper()}: {self.base_url}")
    
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
        encoded_location = quote_plus(location) if location else ""
        
        # Different countries might have slightly different URL structures
        if self.country == "mx":
            if location:
                search_url = f"{self.base_url}/buscar/{encoded_query}/{encoded_location}"
            else:
                search_url = f"{self.base_url}/buscar/{encoded_query}"
        elif self.country == "ar":
            if location:
                search_url = f"{self.base_url}/buscar/{encoded_query}/{encoded_location}"
            else:
                search_url = f"{self.base_url}/buscar/{encoded_query}"
        # Add more country-specific URL formats as needed
        else:
            # Default format
            if location:
                search_url = f"{self.base_url}/buscar/{encoded_query}/{encoded_location}"
            else:
                search_url = f"{self.base_url}/buscar/{encoded_query}"
        
        return search_url
    
    def _ensure_driver(self) -> bool:
        """Ensure the browser driver is initialized."""
        if self.driver is None:
            try:
                options = webdriver.ChromeOptions()
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-infobars")
                options.add_argument("--disable-notifications")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument(f"--user-agent={get_random_user_agent()}")
                
                if self.headless:
                    options.add_argument("--headless")
                
                self.driver = webdriver.Chrome(options=options)
                self.driver.set_page_load_timeout(30)
                return True
            except Exception as e:
                logger.error(f"Failed to initialize Chrome driver: {e}")
                return False
        return True
    
    def get_listings(self) -> List[Any]:
        """
        Retrieve the current page's listing elements.
        
        Returns:
            List of WebElement objects representing business listings
        """
        try:
            # Wait for listings to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".listing, .business-listing, .result-item"))
            )
            
            # Get all listings using multiple possible selectors (sites change often)
            # Try different selectors that might be used in different country versions
            selectors = [
                ".listing", 
                ".business-listing", 
                ".result-item",
                ".empresa",
                "[data-testid='listing-item']"
            ]
            
            for selector in selectors:
                listings = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if listings:
                    logger.info(f"Found {len(listings)} listings using selector: {selector}")
                    return listings
            
            # If no listings found with the primary selectors, try alternative ones
            logger.warning("No listings found with primary selectors, trying alternatives")
            alternative_selector = "div[class*='listing'], div[class*='result'], div[class*='business'], .empresa"
            listings = self.driver.find_elements(By.CSS_SELECTOR, alternative_selector)
            
            return listings
        except Exception as e:
            logger.error(f"Error getting listings: {e}")
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
                "source": f"paginas_amarillas_{self.country}",
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
            # Try different possible selectors
            name_selectors = [
                ".business-name", ".listing-title", ".title", "h2", 
                "[data-testid='listing-name']", ".empresa-nombre"
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
                ".address", ".location", ".direccion",
                "[data-testid='listing-address']", ".empresa-direccion"
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
                ".phone", ".telefono", "[data-testid='listing-phone']",
                ".empresa-telefono"
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
                ".website", ".web", "a.web-link", "[data-testid='listing-website']",
                ".empresa-web", "a[href^='http']"
            ]
            
            for selector in website_selectors:
                try:
                    website_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    business_data["website"] = website_elem.get_attribute("href")
                    break
                except NoSuchElementException:
                    continue
            
            # Extract email from text or elements
            email_selectors = [
                ".email", "[data-testid='listing-email']", ".empresa-email"
            ]
            
            for selector in email_selectors:
                try:
                    email_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    email_text = email_elem.text
                    emails = extract_emails(email_text)
                    if emails:
                        business_data["email"] = emails[0]
                    break
                except NoSuchElementException:
                    continue
            
            # If no explicit email element, try to extract from all text
            if not business_data["email"]:
                all_text = html_element.text
                emails = extract_emails(all_text)
                if emails:
                    business_data["email"] = emails[0]
            
            # Extract category
            category_selectors = [
                ".category", ".categoria", "[data-testid='listing-category']",
                ".empresa-categoria"
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
                ".description", ".descripcion", "[data-testid='listing-description']",
                ".empresa-descripcion"
            ]
            
            for selector in description_selectors:
                try:
                    desc_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    business_data["description"] = clean_text(desc_elem.text)
                    break
                except NoSuchElementException:
                    continue
            
            # Return only if we have at least a name or a phone
            if business_data["name"] or business_data["phone"]:
                return business_data
            else:
                logger.warning("Skipping listing - could not extract name or phone")
                return None
            
        except Exception as e:
            logger.error(f"Error parsing listing: {e}")
            return None
            
    def handle_pagination(self) -> bool:
        """
        Go to the next page of results if available.
        
        Returns:
            True if successfully navigated to next page, False otherwise
        """
        try:
            # Look for pagination controls
            pagination_selectors = [
                "a.next", ".pagination a[rel='next']", 
                ".pagination-next", "[data-testid='pagination-next']",
                "a[aria-label='Next page']", ".siguiente"
            ]
            
            for selector in pagination_selectors:
                try:
                    next_page = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_page.is_displayed() and next_page.is_enabled():
                        logger.info("Navigating to next page")
                        next_page.click()
                        # Wait for the new page to load
                        time.sleep(random.uniform(*self.random_delay_range))
                        return True
                except NoSuchElementException:
                    continue
                except ElementNotInteractableException:
                    logger.warning("Next page button is not interactive")
                    continue
            
            logger.info("No more pages available or next button not found")
            return False
            
        except Exception as e:
            logger.error(f"Error handling pagination: {e}")
            return False
    
    def scrape(self, query: str, location: str = "") -> List[Dict[str, Any]]:
        """
        Core scraping method for Páginas Amarillas.
        Overrides the base method to add pagination handling.
        
        Args:
            query: Search term (e.g., "restaurantes")
            location: Location filter (e.g., "CDMX")
            
        Returns:
            List of dictionaries with scraped data
        """
        self.results = []
        try:
            url = self.build_search_url(query, location)
            logger.info(f"Navigating to: {url}")
            if not self._ensure_driver():
                return []
            
            # Navigate to the search URL
            self.driver.get(url)
            time.sleep(random.uniform(*self.random_delay_range))
            
            # Check for CAPTCHA
            if detect_captcha(self.driver.page_source):
                logger.warning("CAPTCHA detected on initial page load")
                # Here you could implement CAPTCHA handling or notify the user
                # For now, we'll just return an empty result
                return []
            
            # Process first page
            page = 1
            max_pages = 10  # Limit to prevent infinite loops
            
            while page <= max_pages and len(self.results) < self.max_results:
                logger.info(f"Processing page {page}")
                
                # Get and process listings
                listings = self.get_listings()
                if not listings:
                    logger.warning(f"No listings found on page {page}")
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
                    
                    # Add random delay between processing listings
                    time.sleep(random.uniform(0.5, 1.5))
                
                # Try to go to next page if we haven't reached the max results
                if len(self.results) < self.max_results:
                    if not self.handle_pagination():
                        logger.info("No more pages available")
                        break
                    page += 1
                    # Add delay between pages
                    time.sleep(random.uniform(*self.random_delay_range))
            
            # Clean the results
            self.clean_results()
            logger.info(f"Scraped {len(self.results)} listings from Páginas Amarillas {self.country.upper()}")
            return self.results
            
        except Exception as e:
            logger.error(f"Error scraping Páginas Amarillas: {e}")
            return []
        finally:
            # Close the driver when done
            if self.driver:
                self.driver.quit()
                self.driver = None
