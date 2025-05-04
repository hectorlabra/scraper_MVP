#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram Scraper Module

This module provides functionality to scrape business profiles from Instagram
based on hashtags and locations.
"""

import logging
import time
import random
import re
import os
import json
import pickle
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from pathlib import Path

import instaloader
from instaloader import Instaloader, Profile, Post

from scrapers.base_scraper import BaseScraper
from utils.helpers import sanitize_text, extract_emails, extract_phone_numbers

logger = logging.getLogger(__name__)

# Define path for saving session cookies
DEFAULT_SESSION_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'instagram_session')
DEFAULT_CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache', 'instagram')


class InstagramScraper(BaseScraper):
    """
    Instagram scraper for extracting business profiles using hashtags and locations.
    Uses instaloader for Instagram API interactions.
    """
    
    def __init__(self,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 session_path: str = DEFAULT_SESSION_PATH,
                 cache_path: str = DEFAULT_CACHE_PATH,
                 request_delay: float = 2.0,
                 random_delay_range: Optional[Tuple[float, float]] = (1.0, 5.0),
                 max_results: int = 100):
        """
        Initialize the Instagram scraper.
        
        Args:
            username: Instagram username for login
            password: Instagram password for login
            session_path: Path to save session cookies
            cache_path: Path to store cache data
            request_delay: Base delay between requests in seconds
            random_delay_range: Tuple of (min, max) additional random delay
            max_results: Maximum number of results to scrape
        """
        super().__init__(
            request_delay=request_delay,
            random_delay_range=random_delay_range,
            max_results=max_results
        )
        
        self.username = username
        self.password = password
        self.session_path = session_path
        self.cache_path = cache_path
        self.loader = None
        self._is_logged_in = False
        self._processed_profiles: Set[str] = set()
        
        # Create cache directory if it doesn't exist
        os.makedirs(os.path.dirname(session_path), exist_ok=True)
        os.makedirs(cache_path, exist_ok=True)
        
        # Initialize instaloader
        self._initialize_loader()
        
    def _initialize_loader(self):
        """Initialize the Instaloader instance with appropriate settings."""
        self.loader = Instaloader(
            # Don't download any files
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            
            # Set a realistic user agent
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
            
            # Set a reasonable request delay
            request_timeout=30,
            max_connection_attempts=3
        )
        
        self._try_load_session()
        
    def _try_load_session(self) -> bool:
        """
        Try to load a saved Instagram session to avoid login.
        
        Returns:
            True if session loaded successfully, False otherwise
        """
        session_file = f"{self.session_path}_{self.username}" if self.username else None
        
        if session_file and os.path.exists(session_file):
            try:
                # Load session from file
                logger.info(f"Loading Instagram session from {session_file}")
                self.loader.load_session_from_file(self.username, session_file)
                
                # Verify session is still valid
                if self._verify_session():
                    logger.info("Instagram session loaded successfully")
                    self._is_logged_in = True
                    return True
                else:
                    logger.warning("Saved Instagram session is invalid or expired")
            except Exception as e:
                logger.error(f"Failed to load Instagram session: {e}")
                
        logger.info("No valid Instagram session found")
        return False
    
    def _verify_session(self) -> bool:
        """
        Verify the loaded session is valid by trying to access account info.
        
        Returns:
            True if session is valid, False otherwise
        """
        try:
            # Try to access own profile to check if session is valid
            if self.username:
                self.loader.context.get_id_from_username(self.username)
                return True
            return False
        except Exception as e:
            logger.warning(f"Session verification failed: {e}")
            return False
    
    def login(self, force: bool = False) -> bool:
        """
        Log in to Instagram using provided credentials.
        
        Args:
            force: Force login even if already logged in
            
        Returns:
            True if login successful, False otherwise
        """
        if self._is_logged_in and not force:
            logger.info("Already logged in to Instagram")
            return True
            
        if not self.username or not self.password:
            logger.error("Cannot login to Instagram: username or password not provided")
            return False
            
        try:
            logger.info(f"Logging in to Instagram as {self.username}")
            self.loader.login(self.username, self.password)
            
            # Save session for future use
            session_file = f"{self.session_path}_{self.username}"
            self.loader.save_session_to_file(session_file)
            
            logger.info("Login successful, session saved")
            self._is_logged_in = True
            return True
        
        except instaloader.exceptions.InvalidArgumentException:
            logger.error("Invalid username or password")
        except instaloader.exceptions.ConnectionException as e:
            logger.error(f"Connection error during login: {e}")
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            logger.error("Two-factor authentication required. Cannot continue with automated login.")
        except Exception as e:
            logger.error(f"Failed to login to Instagram: {e}")
            
        return False
    
    def is_logged_in(self) -> bool:
        """
        Check if currently logged in to Instagram.
        
        Returns:
            True if logged in, False otherwise
        """
        return self._is_logged_in
    
    def logout(self) -> None:
        """Log out from Instagram and clear session."""
        if self._is_logged_in:
            try:
                self.loader.close()
                self._is_logged_in = False
                logger.info("Logged out from Instagram")
            except Exception as e:
                logger.error(f"Error during logout: {e}")
    
    def search_by_hashtag(self, hashtag: str, post_limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search Instagram for posts with the given hashtag and extract business profiles.
        
        Args:
            hashtag: Hashtag to search for (without the # symbol)
            post_limit: Maximum number of posts to process
            
        Returns:
            List of business profile data dictionaries
        """
        # Clear results for new search
        self.results = []
        
        try:
            # Hashtag must not include the # symbol
            hashtag = hashtag.strip('#')
            logger.info(f"Searching Instagram for posts with hashtag #{hashtag}")
            
            # Get posts by hashtag
            hashtag_posts = self.loader.get_hashtag_posts(hashtag)
            
            # Process posts
            post_count = 0
            for post in hashtag_posts:
                if post_count >= post_limit:
                    break
                    
                post_count += 1
                logger.debug(f"Processing post {post_count}/{post_limit} from #{hashtag}")
                
                # Extract business information from the post author
                self._process_post(post)
                
                # Add delay to avoid rate limiting
                self.delay_request()
                
            logger.info(f"Processed {post_count} posts with hashtag #{hashtag}")
            
            # Clean results before returning
            self.clean_results()
            return self.results
            
        except instaloader.exceptions.ConnectionException as e:
            logger.error(f"Connection error while searching hashtag #{hashtag}: {e}")
        except instaloader.exceptions.InvalidArgumentException:
            logger.error(f"Invalid hashtag: {hashtag}")
        except Exception as e:
            logger.error(f"Error while searching hashtag #{hashtag}: {e}")
            
        return self.results
    
    def search_by_location(self, location_id: str, post_limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search Instagram for posts from the given location and extract business profiles.
        
        Args:
            location_id: Instagram location ID
            post_limit: Maximum number of posts to process
            
        Returns:
            List of business profile data dictionaries
        """
        # Clear results for new search
        self.results = []
        
        try:
            logger.info(f"Searching Instagram for posts from location ID {location_id}")
            
            # Get posts by location
            location_posts = self.loader.get_location_posts(int(location_id))
            
            # Process posts
            post_count = 0
            for post in location_posts:
                if post_count >= post_limit:
                    break
                    
                post_count += 1
                logger.debug(f"Processing post {post_count}/{post_limit} from location {location_id}")
                
                # Extract business information from the post author
                self._process_post(post)
                
                # Add delay to avoid rate limiting
                self.delay_request()
                
            logger.info(f"Processed {post_count} posts from location {location_id}")
            
            # Clean results before returning
            self.clean_results()
            return self.results
            
        except instaloader.exceptions.ConnectionException as e:
            logger.error(f"Connection error while searching location {location_id}: {e}")
        except instaloader.exceptions.InvalidArgumentException:
            logger.error(f"Invalid location ID: {location_id}")
        except Exception as e:
            logger.error(f"Error while searching location {location_id}: {e}")
            
        return self.results
    
    def _process_post(self, post: Post) -> None:
        """
        Process a post to extract business profile information from its author.
        
        Args:
            post: Instagram post object
        """
        try:
            # Get post author profile
            profile_username = post.owner_username
            
            # Skip if we've already processed this profile
            if profile_username in self._processed_profiles:
                return
                
            # Mark profile as processed
            self._processed_profiles.add(profile_username)
            
            # Get full profile information
            profile = Profile.from_username(self.loader.context, profile_username)
            
            # Check if this looks like a business profile
            if self._is_likely_business(profile, post):
                # Extract business data from profile
                business_data = self._extract_profile_data(profile, post)
                if business_data:
                    self.results.append(business_data)
                    logger.info(f"Extracted business profile: {profile_username}")
            
        except instaloader.exceptions.ProfileNotExistsException:
            logger.warning(f"Profile does not exist or is private: {post.owner_username}")
        except Exception as e:
            logger.error(f"Error processing post from {post.owner_username}: {e}")
    
    def _is_likely_business(self, profile: Profile, post: Post) -> bool:
        """
        Determine if a profile is likely to be a business account.
        
        Args:
            profile: Instagram profile object
            post: Post that led to this profile
            
        Returns:
            True if the profile appears to be a business, False otherwise
        """
        business_indicators = [
            # Profile indicators
            profile.is_business_account,
            profile.business_category_name is not None,
            profile.external_url is not None,
            
            # Bio indicators (look for keywords)
            any(term in profile.biography.lower() for term in [
                'negocio', 'business', 'empresa', 'tienda', 'store', 'shop', 
                'venta', 'compra', 'servicio', 'service', 'empresa', 'company',
                'restaurante', 'restaurant', 'café', 'cafe', 'bar',
                'oficial', 'official', 'profesional', 'professional'
            ]),
            
            # Contact indicators
            re.search(r'[0-9]{6,}', profile.biography) is not None,  # Phone number
            '@' in profile.biography,  # Email or mention
            
            # Profile stats
            profile.mediacount > 10,  # Active posting
            profile.followers > 500,  # Significant following
        ]
        
        # Count how many business indicators are true
        score = sum(1 for indicator in business_indicators if indicator)
        
        # Consider it a business if at least 3 indicators are present
        return score >= 3
    
    def _extract_profile_data(self, profile: Profile, post: Post) -> Optional[Dict[str, Any]]:
        """
        Extract business data from an Instagram profile.
        
        Args:
            profile: Instagram profile object
            post: Post that led to this profile
            
        Returns:
            Dictionary with extracted business data or None if not enough data
        """
        try:
            # Contact information
            phone_numbers = extract_phone_numbers(profile.biography)
            emails = extract_emails(profile.biography)
            
            # Extract location information
            location = post.location if hasattr(post, 'location') else None
            location_name = location.name if location else None
            location_lat = location.lat if location and hasattr(location, 'lat') else None
            location_lng = location.lng if location and hasattr(location, 'lng') else None
            
            # Extract hashtags from post
            hashtags = set()
            if post.caption:
                hashtags = set(re.findall(r'#(\w+)', post.caption))
            
            # Build the business data dictionary
            business_data = {
                'source': 'instagram',
                'scrape_date': datetime.now().strftime('%Y-%m-%d'),
                'name': profile.full_name or profile.username,
                'username': profile.username,
                'profile_url': f'https://www.instagram.com/{profile.username}/',
                'description': sanitize_text(profile.biography) if profile.biography else None,
                'website': profile.external_url,
                'phone': phone_numbers[0] if phone_numbers else None,
                'additional_phones': phone_numbers[1:] if len(phone_numbers) > 1 else None,
                'email': emails[0] if emails else None,
                'additional_emails': emails[1:] if len(emails) > 1 else None,
                'category': profile.business_category_name,
                'followers': profile.followers,
                'following': profile.followees,
                'post_count': profile.mediacount,
                'is_business_account': profile.is_business_account,
                'is_verified': profile.is_verified,
                'location_name': location_name,
                'location_lat': location_lat,
                'location_lng': location_lng,
                'hashtags': list(hashtags) if hashtags else None,
                'social_media': {
                    'instagram': f'https://www.instagram.com/{profile.username}/'
                }
            }
            
            # Filter out None values
            business_data = {k: v for k, v in business_data.items() if v is not None}
            
            # Ensure we have at least some basic contact information
            has_contact_info = any([
                business_data.get('phone'),
                business_data.get('email'),
                business_data.get('website'),
                business_data.get('location_name')
            ])
            
            return business_data if has_contact_info else None
            
        except Exception as e:
            logger.error(f"Error extracting profile data for {profile.username}: {e}")
            return None
    
    def scrape(self, query: str, location: str = "") -> List[Dict[str, Any]]:
        """
        Implement BaseScraper's abstract method to scrape data.
        
        For Instagram, the query will be interpreted as a hashtag.
        The location parameter is ignored in favor of search_by_location method.
        
        Args:
            query: Hashtag to search for (can include # symbol)
            location: Ignored for this implementation
            
        Returns:
            List of business profile data dictionaries
        """
        return self.search_by_hashtag(query, self.max_results)
    
    def clean_results(self) -> None:
        """
        Clean the scraped results.
        Override BaseScraper's method to add Instagram-specific cleaning.
        """
        # Call parent class's clean_results first
        super().clean_results()
        
        # Additional Instagram-specific cleaning
        cleaned_results = []
        for result in self.results:
            # Only include results that have at least one contact method
            if any(result.get(field) for field in ['phone', 'email', 'website']):
                cleaned_results.append(result)
        
        self.results = cleaned_results
        
        # Sort results by follower count (most popular first)
        self.results.sort(key=lambda x: x.get('followers', 0), reverse=True)
        
        # Truncate to max_results if needed
        if len(self.results) > self.max_results:
            self.results = self.results[:self.max_results]
