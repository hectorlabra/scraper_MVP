#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Directory Scrapers

This module contains test cases for the directory scrapers.
"""

import os
import sys
import unittest
import logging
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the scrapers
from scrapers.paginas_amarillas_scraper import PaginasAmarillasScraper
from scrapers.cylex_scraper import CylexScraper
from scrapers.guialocal_scraper import GuiaLocalScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_directory_scrapers.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TestDirectoryScrapers(unittest.TestCase):
    """Test cases for directory scrapers."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_query = "restaurantes"
        self.test_location = "CDMX"

    def test_paginas_amarillas_build_search_url(self):
        """Test PaginasAmarillasScraper's build_search_url method."""
        scraper = PaginasAmarillasScraper(country="mx")
        url = scraper.build_search_url(self.test_query, self.test_location)
        self.assertTrue(url.startswith("https://www.paginasamarillas.com.mx"))
        self.assertIn("restaurantes", url)
        self.assertIn("CDMX", url)
        
        # Test URL without location
        url_no_location = scraper.build_search_url(self.test_query, "")
        self.assertTrue(url_no_location.startswith("https://www.paginasamarillas.com.mx"))
        self.assertIn("restaurantes", url_no_location)
        
        # Test different country
        scraper_ar = PaginasAmarillasScraper(country="ar")
        url_ar = scraper_ar.build_search_url(self.test_query)
        self.assertTrue(url_ar.startswith("https://www.paginasamarillas.com.ar"))

    def test_cylex_build_search_url(self):
        """Test CylexScraper's build_search_url method."""
        scraper = CylexScraper(country="mx")
        url = scraper.build_search_url(self.test_query, self.test_location)
        self.assertTrue(url.startswith("https://www.cylex.com.mx"))
        self.assertIn("q=restaurantes", url)
        self.assertIn("loc=CDMX", url)
        
        # Test URL without location
        url_no_location = scraper.build_search_url(self.test_query, "")
        self.assertTrue(url_no_location.startswith("https://www.cylex.com.mx"))
        self.assertIn("q=restaurantes", url_no_location)
        self.assertNotIn("loc=", url_no_location)
        
        # Test different country
        scraper_cl = CylexScraper(country="cl")
        url_cl = scraper_cl.build_search_url(self.test_query)
        self.assertTrue(url_cl.startswith("https://www.cylex.cl"))

    def test_guialocal_build_search_url(self):
        """Test GuiaLocalScraper's build_search_url method."""
        scraper = GuiaLocalScraper(country="mx")
        url = scraper.build_search_url(self.test_query, self.test_location)
        self.assertTrue(url.startswith("https://www.guialocal.com.mx"))
        self.assertIn("q=restaurantes", url)
        self.assertIn("qc=CDMX", url)
        
        # Test URL without location
        url_no_location = scraper.build_search_url(self.test_query, "")
        self.assertTrue(url_no_location.startswith("https://www.guialocal.com.mx"))
        self.assertIn("q=restaurantes", url_no_location)
        self.assertNotIn("qc=", url_no_location)
        
        # Test different country
        scraper_co = GuiaLocalScraper(country="co")
        url_co = scraper_co.build_search_url(self.test_query)
        self.assertTrue(url_co.startswith("https://www.guialocal.com.co"))

    @patch('scrapers.paginas_amarillas_scraper.webdriver.Chrome')
    def test_paginas_amarillas_parse_listing(self, mock_chrome):
        """Test PaginasAmarillasScraper's parse_listing method with a mock listing."""
        # Create a mock webdriver and element
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Create a mock listing element with business data
        mock_listing = MagicMock()
        
        # Mock the find_element method to return elements with text
        def mock_find_element(by, selector):
            if ".business-name" in selector or ".listing-title" in selector or "h2" in selector:
                mock_name = MagicMock()
                mock_name.text = "Test Restaurant"
                return mock_name
            elif ".address" in selector or ".location" in selector:
                mock_address = MagicMock()
                mock_address.text = "123 Main St, CDMX"
                return mock_address
            elif ".phone" in selector or ".telefono" in selector:
                mock_phone = MagicMock()
                mock_phone.text = "+52 55 1234 5678"
                return mock_phone
            elif ".website" in selector or ".web" in selector or "a[href^='http']" in selector:
                mock_website = MagicMock()
                mock_website.get_attribute.return_value = "http://testrestaurant.com"
                return mock_website
            elif ".category" in selector:
                mock_category = MagicMock()
                mock_category.text = "Restaurantes"
                return mock_category
            raise Exception(f"No mock for selector: {selector}")
        
        mock_listing.find_element = mock_find_element
        mock_listing.text = "Test Restaurant +52 55 1234 5678 123 Main St, CDMX contact@testrestaurant.com"
        
        # Create the scraper and test parsing
        scraper = PaginasAmarillasScraper(country="mx")
        scraper.driver = mock_driver  # Set the mock driver
        
        result = scraper.parse_listing(mock_listing)
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Test Restaurant")
        self.assertEqual(result["address"], "123 Main St, CDMX")
        self.assertEqual(result["phone"], "+52 55 1234 5678")
        self.assertEqual(result["website"], "http://testrestaurant.com")
        self.assertEqual(result["category"], "Restaurantes")
        self.assertEqual(result["source"], "paginas_amarillas_mx")
    
    @patch('utils.helpers.wait_for_elements')
    def test_paginas_amarillas_get_listings_fallback(self, mock_wait):
        """Test PaginasAmarillasScraper.get_listings fallback to CSS selectors."""
        # Simulate no dynamic analysis by setting skip_dynamic
        # First selector returns empty, second returns two items
        mock_elem1 = MagicMock()
        mock_elem2 = MagicMock()
        mock_wait.side_effect = [
            [],  # ".listing"
            [mock_elem1, mock_elem2]  # ".search-results__item"
        ]
        scraper = PaginasAmarillasScraper(skip_dynamic=True)
        scraper.driver = MagicMock()
        listings = scraper.get_listings()
        # Should return the two elements from the second selector
        self.assertEqual(listings, [mock_elem1, mock_elem2])

    @patch('scrapers.cylex_scraper.webdriver.Chrome')
    def test_cylex_parse_listing(self, mock_chrome):
        """Test CylexScraper's parse_listing method with a mock listing."""
        # Create a mock webdriver and element
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Create a mock listing element with business data
        mock_listing = MagicMock()
        
        # Mock the find_element method to return elements with text
        def mock_find_element(by, selector):
            if ".company-name" in selector or ".name" in selector or "h2" in selector:
                mock_name = MagicMock()
                mock_name.text = "Test Hotel"
                return mock_name
            elif ".company-address" in selector or ".address" in selector:
                mock_address = MagicMock()
                mock_address.text = "456 Beach Dr, Cancun"
                return mock_address
            elif ".company-phone" in selector or ".phone" in selector:
                mock_phone = MagicMock()
                mock_phone.text = "+52 998 123 4567"
                return mock_phone
            elif ".company-website" in selector or ".website" in selector or "a[href^='http']" in selector:
                mock_website = MagicMock()
                mock_website.get_attribute.return_value = "http://testhotel.com"
                return mock_website
            elif ".company-category" in selector or ".category" in selector:
                mock_category = MagicMock()
                mock_category.text = "Hoteles"
                return mock_category
            elif ".company-rating" in selector or ".rating" in selector:
                mock_rating = MagicMock()
                mock_rating.text = "4.5 stars"
                return mock_rating
            raise Exception(f"No mock for selector: {selector}")
        
        mock_listing.find_element = mock_find_element
        mock_listing.text = "Test Hotel +52 998 123 4567 456 Beach Dr, Cancun info@testhotel.com Hoteles 4.5 stars"
        
        # Create the scraper and test parsing
        scraper = CylexScraper(country="mx")
        scraper.driver = mock_driver  # Set the mock driver
        
        result = scraper.parse_listing(mock_listing)
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Test Hotel")
        self.assertEqual(result["address"], "456 Beach Dr, Cancun")
        self.assertEqual(result["phone"], "+52 998 123 4567")
        self.assertEqual(result["website"], "http://testhotel.com")
        self.assertEqual(result["category"], "Hoteles")
        self.assertEqual(result["source"], "cylex_mx")
        self.assertEqual(result["rating"], 4.5)

    @patch('scrapers.guialocal_scraper.webdriver.Chrome')
    def test_guialocal_parse_listing(self, mock_chrome):
        """Test GuiaLocalScraper's parse_listing method with a mock listing."""
        # Create a mock webdriver and element
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Create a mock listing element with business data
        mock_listing = MagicMock()
        
        # Mock the find_element method to return elements with text
        def mock_find_element(by, selector):
            if ".company-name" in selector or ".name" in selector or "h2" in selector:
                mock_name = MagicMock()
                mock_name.text = "Test Dental Clinic"
                return mock_name
            elif ".company-address" in selector or ".address" in selector:
                mock_address = MagicMock()
                mock_address.text = "789 Centro Ave, Guadalajara"
                return mock_address
            elif ".company-phone" in selector or ".phone" in selector:
                mock_phone = MagicMock()
                mock_phone.text = "+52 33 9876 5432"
                return mock_phone
            elif ".company-website" in selector or ".website" in selector or "a[href^='http']" in selector:
                mock_website = MagicMock()
                mock_website.get_attribute.return_value = "http://testdentalclinic.com"
                return mock_website
            elif ".company-category" in selector or ".category" in selector:
                mock_category = MagicMock()
                mock_category.text = "Dentistas"
                return mock_category
            elif ".company-description" in selector or ".description" in selector:
                mock_desc = MagicMock()
                mock_desc.text = "Servicio dental profesional"
                return mock_desc
            raise Exception(f"No mock for selector: {selector}")
        
        mock_listing.find_element = mock_find_element
        mock_listing.text = "Test Dental Clinic +52 33 9876 5432 789 Centro Ave, Guadalajara contact@testdental.com Dentistas Servicio dental profesional"
        
        # Create the scraper and test parsing
        scraper = GuiaLocalScraper(country="mx")
        scraper.driver = mock_driver  # Set the mock driver
        
        result = scraper.parse_listing(mock_listing)
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Test Dental Clinic")
        self.assertEqual(result["address"], "789 Centro Ave, Guadalajara")
        self.assertEqual(result["phone"], "+52 33 9876 5432")
        self.assertEqual(result["website"], "http://testdentalclinic.com")
        self.assertEqual(result["category"], "Dentistas")
        self.assertEqual(result["description"], "Servicio dental profesional")
        self.assertEqual(result["source"], "guialocal_mx")


if __name__ == '__main__':
    unittest.main()
