#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility Functions

This module provides utility functions used throughout the project.
"""

import logging
import os
import json
import random
import time
import re
from typing import List, Dict, Any, Optional, Union, Tuple

logger = logging.getLogger(__name__)

def load_config_from_env(prefix: str = "") -> Dict[str, Any]:
    """
    Load configuration from environment variables.
    
    Args:
        prefix: Prefix for environment variables to filter by
        
    Returns:
        Dictionary of configuration values
    """
    config = {}
    for key, value in os.environ.items():
        if prefix and not key.startswith(prefix):
            continue
            
        # Remove prefix if it exists
        config_key = key[len(prefix):] if prefix and key.startswith(prefix) else key
        
        # Try to parse value as JSON if it looks like a JSON string
        if value.startswith('{') and value.endswith('}'):
            try:
                config[config_key] = json.loads(value)
                continue
            except json.JSONDecodeError:
                pass
                
        # Try to convert value to appropriate type
        if value.lower() in ('true', 'yes', '1'):
            config[config_key] = True
        elif value.lower() in ('false', 'no', '0'):
            config[config_key] = False
        elif value.isdigit():
            config[config_key] = int(value)
        elif re.match(r'^-?\d+(\.\d+)?$', value):
            config[config_key] = float(value)
        elif ',' in value:
            # Treat as comma-separated list
            config[config_key] = [v.strip() for v in value.split(',')]
        else:
            config[config_key] = value
            
    return config

def retry_on_failure(max_retries: int = 3, 
                     delay: float = 1.0,
                     backoff_factor: float = 2.0,
                     exceptions: Tuple = (Exception,)) -> callable:
    """
    Decorator to retry a function on failure.
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to increase delay for subsequent retries
        exceptions: Tuple of exceptions to catch and retry on
        
    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {str(e)}")
                        raise
                        
                    logger.warning(f"Retry {retries}/{max_retries} for function {func.__name__} after error: {str(e)}")
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
                    
        return wrapper
    return decorator

def clean_text(text: Optional[str]) -> Optional[str]:
    """
    Clean text by removing excess whitespace and normalizing line endings.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return text
        
    # Replace multiple whitespace with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text

def extract_phone_numbers(text: str) -> List[str]:
    """
    Extract phone numbers from text.
    
    Args:
        text: Text to extract phone numbers from
        
    Returns:
        List of extracted phone numbers
    """
    if not text:
        return []
        
    # Pattern to match common LATAM phone number formats
    # This is a simplified pattern and might need adjustment for specific countries
    pattern = r'(?:\+?(?:1|5[0-9])?[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
    
    matches = re.findall(pattern, text)
    return [clean_text(match) for match in matches if match]

def extract_emails(text: str) -> List[str]:
    """
    Extract email addresses from text.
    
    Args:
        text: Text to extract email addresses from
        
    Returns:
        List of extracted email addresses
    """
    if not text:
        return []
        
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    matches = re.findall(pattern, text)
    return [match.lower() for match in matches if match]

def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text.
    
    Args:
        text: Text to extract URLs from
        
    Returns:
        List of extracted URLs
    """
    if not text:
        return []
        
    pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)'
    
    matches = re.findall(pattern, text)
    return [match for match in matches if match]
