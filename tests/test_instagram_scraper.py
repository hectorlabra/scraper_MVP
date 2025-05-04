#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Instagram Scraper

This module contains tests for the Instagram Scraper.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import logging

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scrapers.instagram_scraper import InstagramScraper

# Disable logging during tests
logging.disable(logging.CRITICAL)

class TestInstagramScraper(unittest.TestCase):
    """Test cases for the Instagram Scraper."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use temporary paths for testing
        self.test_session_path = '/tmp/instagram_test_session'
        self.test_cache_path = '/tmp/instagram_test_cache'
        
        # Create a scraper instance with mock credentials
        self.scraper = InstagramScraper(
            username='test_user',
            password='test_password',
            session_path=self.test_session_path,
            cache_path=self.test_cache_path,
            request_delay=0.01,  # Use minimal delay for testing
            max_results=10
        )
        
        # Mock the Instaloader instance
        self.scraper.loader = MagicMock()
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove test files if they exist
        for path in [f"{self.test_session_path}_test_user"]:
            if os.path.exists(path):
                os.remove(path)
    
    def test_initialization(self):
        """Test that the scraper initializes correctly."""
        self.assertEqual(self.scraper.username, 'test_user')
        self.assertEqual(self.scraper.password, 'test_password')
        self.assertEqual(self.scraper.session_path, self.test_session_path)
        self.assertEqual(self.scraper.cache_path, self.test_cache_path)
        self.assertEqual(self.scraper.request_delay, 0.01)
        self.assertEqual(self.scraper.max_results, 10)
        self.assertEqual(len(self.scraper.results), 0)
    
    @patch('instaloader.Instaloader')
    def test_login_success(self, mock_instaloader):
        """Test successful login."""
        # Set up the mock
        self.scraper.loader.login.return_value = None  # Successful login returns None
        
        # Test login
        result = self.scraper.login()
        
        # Verify
        self.assertTrue(result)
        self.assertTrue(self.scraper.is_logged_in())
        self.scraper.loader.login.assert_called_once_with('test_user', 'test_password')
        self.scraper.loader.save_session_to_file.assert_called_once()
    
    @patch('instaloader.Instaloader')
    def test_login_failure(self, mock_instaloader):
        """Test failed login."""
        # Set up the mock to raise an exception
        self.scraper.loader.login.side_effect = Exception("Login failed")
        
        # Test login
        result = self.scraper.login()
        
        # Verify
        self.assertFalse(result)
        self.assertFalse(self.scraper.is_logged_in())
        self.scraper.loader.login.assert_called_once_with('test_user', 'test_password')
        self.scraper.loader.save_session_to_file.assert_not_called()
    
    def test_search_by_hashtag(self):
        """Test searching by hashtag."""
        # Mock the get_hashtag_posts method
        mock_post1 = MagicMock()
        mock_post1.owner_username = "business1"
        mock_post1.caption = "This is a test post #business #latam"
        
        mock_post2 = MagicMock()
        mock_post2.owner_username = "business2"
        mock_post2.caption = "Another test post #entrepreneur"
        
        self.scraper.loader.get_hashtag_posts.return_value = [mock_post1, mock_post2]
        
        # Mock the profile extraction
        mock_profile1 = MagicMock()
        mock_profile1.username = "business1"
        mock_profile1.full_name = "Business One"
        mock_profile1.biography = "We are a business. Contact: business1@example.com"
        mock_profile1.is_business_account = True
        mock_profile1.business_category_name = "Local Business"
        mock_profile1.external_url = "https://business1.example.com"
        mock_profile1.followers = 1000
        mock_profile1.followees = 500
        mock_profile1.mediacount = 50
        mock_profile1.is_verified = False
        
        mock_profile2 = MagicMock()
        mock_profile2.username = "business2"
        mock_profile2.full_name = "Business Two"
        mock_profile2.biography = "Another business. Call +1234567890"
        mock_profile2.is_business_account = True
        mock_profile2.business_category_name = "Shopping & Retail"
        mock_profile2.external_url = "https://business2.example.com"
        mock_profile2.followers = 2000
        mock_profile2.followees = 800
        mock_profile2.mediacount = 80
        mock_profile2.is_verified = True
        
        # Return the appropriate profile based on username
        def mock_from_username(context, username):
            if username == "business1":
                return mock_profile1
            elif username == "business2":
                return mock_profile2
            raise ValueError(f"Unknown username: {username}")
            
        # Patch the Profile.from_username method
        with patch('instaloader.Profile.from_username', side_effect=mock_from_username):
            # Call the method
            results = self.scraper.search_by_hashtag("business", post_limit=5)
            
            # Verify
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].get('name'), "Business Two")  # Sorted by followers
            self.assertEqual(results[1].get('name'), "Business One")
            
            # Check that the loader was called correctly
            self.scraper.loader.get_hashtag_posts.assert_called_once_with("business")
    
    def test_is_likely_business(self):
        """Test business profile detection."""
        # Create a mock profile
        mock_profile = MagicMock()
        mock_profile.is_business_account = True
        mock_profile.business_category_name = "Local Business"
        mock_profile.biography = "We are a business. Contact us at contact@example.com"
        mock_profile.external_url = "https://example.com"
        mock_profile.followers = 1000
        mock_profile.mediacount = 50
        
        mock_post = MagicMock()
        
        # Test with a clear business profile
        result = self.scraper._is_likely_business(mock_profile, mock_post)
        self.assertTrue(result)
        
        # Test with ambiguous profile
        mock_profile.is_business_account = False
        mock_profile.business_category_name = None
        mock_profile.biography = "Just a personal account"
        result = self.scraper._is_likely_business(mock_profile, mock_post)
        self.assertFalse(result)
        
        # Test with some business indicators
        mock_profile.biography = "I sell handmade crafts. DM to order."
        mock_profile.external_url = "https://etsy.com/shop/example"
        result = self.scraper._is_likely_business(mock_profile, mock_post)
        self.assertTrue(result)
    
    def test_extract_profile_data(self):
        """Test profile data extraction."""
        # Create a mock profile with business data
        mock_profile = MagicMock()
        mock_profile.username = "test_business"
        mock_profile.full_name = "Test Business"
        mock_profile.biography = "Local business. Contact: test@example.com or +1234567890"
        mock_profile.external_url = "https://example.com"
        mock_profile.business_category_name = "Local Business"
        mock_profile.is_business_account = True
        mock_profile.is_verified = False
        mock_profile.followers = 1000
        mock_profile.followees = 500
        mock_profile.mediacount = 50
        
        # Create a mock post with location
        mock_post = MagicMock()
        mock_post.caption = "Check out our new products! #business #local"
        mock_post.location = MagicMock()
        mock_post.location.name = "Test Location"
        mock_post.location.lat = 12.345
        mock_post.location.lng = -67.890
        
        # Extract profile data
        result = self.scraper._extract_profile_data(mock_profile, mock_post)
        
        # Verify the extracted data
        self.assertIsNotNone(result)
        self.assertEqual(result.get('name'), "Test Business")
        self.assertEqual(result.get('username'), "test_business")
        self.assertEqual(result.get('phone'), "+1234567890")
        self.assertEqual(result.get('email'), "test@example.com")
        self.assertEqual(result.get('website'), "https://example.com")
        self.assertEqual(result.get('category'), "Local Business")
        self.assertEqual(result.get('followers'), 1000)
        self.assertEqual(result.get('location_name'), "Test Location")
        self.assertEqual(result.get('location_lat'), 12.345)
        self.assertEqual(result.get('location_lng'), -67.890)
        self.assertTrue('business' in result.get('hashtags', []))
        self.assertTrue('local' in result.get('hashtags', []))
    
    def test_clean_results(self):
        """Test results cleaning."""
        # Create some test results
        test_results = [
            {
                'name': 'Business A',
                'phone': '+1234567890',
                'website': 'https://example.com',
                'followers': 2000
            },
            {
                'name': 'Business B',
                'email': 'business@example.com',
                'followers': 1000
            },
            {
                'name': 'Business C',
                'followers': 3000
                # No contact info, should be removed
            }
        ]
        
        self.scraper.results = test_results
        self.scraper.clean_results()
        
        # Verify
        self.assertEqual(len(self.scraper.results), 2)  # Business C should be removed
        self.assertEqual(self.scraper.results[0].get('name'), 'Business A')  # Sorted by followers
        self.assertEqual(self.scraper.results[1].get('name'), 'Business B')


if __name__ == '__main__':
    unittest.main()
