#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrapers Package

This package contains all web scrapers for the LeadScraper LATAM project.
"""

from scrapers.base_scraper import BaseScraper
from scrapers.google_maps_scraper import GoogleMapsScraper
from scrapers.directory_scraper import DirectoryScraper
from scrapers.paginas_amarillas_scraper import PaginasAmarillasScraper
from scrapers.cylex_scraper import CylexScraper
from scrapers.guialocal_scraper import GuiaLocalScraper
from scrapers.instagram_scraper import InstagramScraper

__all__ = [
    'BaseScraper',
    'GoogleMapsScraper',
    'DirectoryScraper',
    'PaginasAmarillasScraper',
    'CylexScraper',
    'GuiaLocalScraper',
    'InstagramScraper'
]