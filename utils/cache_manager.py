#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cache Manager Module

This module provides sophisticated caching functionality with TTL, LRU eviction,
memory optimization, and monitoring integration.

Features:
- In-memory caching with TTL support
- LRU eviction strategy for memory management
- Memory-optimized data processing
- File-based persistent storage
- Compression support
- Monitoring and metrics tracking
- Incremental update capabilities
"""

import os
import json
import time
import hashlib
import logging
import gzip
import shutil
import threading
import weakref
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from utils.monitoring import MetricsRegistry, get_metrics_registry

logger = logging.getLogger(__name__)

class CacheEntry:
    """Represents a cache entry with TTL and metadata."""
    
    def __init__(self, data: Any, metadata: Dict[str, Any], ttl_seconds: int):
        self.data = data
        self.metadata = metadata
        self.timestamp = time.time()
        self.ttl = ttl_seconds
        self.access_count = 0
        self.last_accessed = self.timestamp
        
    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        return time.time() - self.timestamp > self.ttl
        
    def touch(self) -> None:
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = time.time()

class CacheManager:
    """
    Advanced cache manager with TTL, LRU eviction, and memory optimization.
    
    Features:
    - In-memory caching with TTL
    - LRU eviction strategy
    - Memory optimization
    - Batch processing
    - Monitoring integration
    - Incremental updates
    """
    
    DEFAULT_TTL = 300  # 5 minutes
    DEFAULT_MAX_ITEMS = 1000
    DEFAULT_BATCH_SIZE = 50
    CLEANUP_INTERVAL = 60  # cleanup every minute
    
    def __init__(self, cache_dir: str = "cache",
                 ttl_seconds: int = DEFAULT_TTL,
                 max_items: int = DEFAULT_MAX_ITEMS,
                 batch_size: int = DEFAULT_BATCH_SIZE,
                 compression: bool = True,
                 compression_level: int = 6):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Directory for persistent storage
            ttl_seconds: Time-to-live for cache entries
            max_items: Maximum number of items in memory
            batch_size: Size of batches for processing
            compression: Whether to use compression
            compression_level: Compression level (1-9)
        """
        self.cache_dir = cache_dir
        self.ttl = ttl_seconds
        self.max_items = max_items
        self.batch_size = batch_size
        self.compression = compression
        self.compression_level = compression_level
        
        # Primary cache storage (in-memory with LRU)
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Statistics tracking
        self.hits = 0
        self.misses = 0
        self.saves = 0
        self.evictions = 0
        self.storage_saved = 0
        self.total_cache_size = 0
        self.cache_hits_by_scraper = {}
        
        # Cache age histogram
        self.cache_age_histogram = {
            "0-1h": 0,
            "1-6h": 0,
            "6-12h": 0,
            "12-24h": 0,
            "24h+": 0
        }
        
        # Initialize metrics registry for monitoring
        self.metrics = get_metrics_registry()
        
        # Ensure cache directory exists
        self._ensure_cache_dir()
        
        # Start maintenance tasks
        self._start_maintenance()
    
    def _ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            logger.info(f"Created cache directory: {self.cache_dir}")
            
    def _start_maintenance(self) -> None:
        """Start maintenance tasks."""
        self.cleanup_thread = threading.Thread(
            target=self._maintenance_loop,
            daemon=True,
            name="cache-maintenance"
        )
        self.cleanup_thread.start()
        logger.info("Started cache maintenance thread")
        
    def _maintenance_loop(self) -> None:
        """Run periodic maintenance tasks."""
        while True:
            try:
                # Sleep first to avoid immediate cleanup
                time.sleep(self.CLEANUP_INTERVAL)
                
                with self.lock:
                    self._cleanup_expired()
                    self._apply_lru_policy()
                    self._update_metrics()
                    
            except Exception as e:
                logger.error(f"Error in cache maintenance: {e}")
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        initial_count = len(self.cache)
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self.cache[key]
            
        if expired_keys:
            count = len(expired_keys)
            logger.debug(f"Removed {count} expired cache entries")
            self.metrics.inc_counter("cache_expired_removed", count)
            
    def _apply_lru_policy(self) -> None:
        """Apply LRU eviction if needed."""
        while len(self.cache) > self.max_items:
            # Remove least recently used item
            self.cache.popitem(last=False)
            self.evictions += 1
            
    def _update_metrics(self) -> None:
        """Update monitoring metrics."""
        self.metrics.set_gauge("cache_size", len(self.cache))
        self.metrics.set_gauge("cache_hit_ratio", 
                             self.hits / max(self.hits + self.misses, 1))
        self.metrics.set_gauge("cache_evictions", self.evictions)
        self.metrics.set_gauge("cache_memory_usage", self._estimate_memory_usage())
        
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        try:
            total_size = sum(
                len(str(entry.data)) + len(str(entry.metadata))
                for entry in self.cache.values()
            )
            return total_size / (1024 * 1024)  # Convert to MB
        except:
            return 0.0
    
    def _generate_cache_key(self, scraper_name: str, query: str, location: str = "") -> str:
        """
        Generate a unique cache key.
        
        Args:
            scraper_name: Name of the scraper
            query: Search query
            location: Location filter
            
        Returns:
            Unique cache key
        """
        # Normalize inputs
        normalized_query = query.lower().strip()
        normalized_location = location.lower().strip() if location else ""
        
        # Create string to hash
        key_string = f"{scraper_name}:{normalized_query}:{normalized_location}"
        
        # Generate hash
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return key_hash
    
    def _get_cache_path(self, cache_key: str) -> str:
        """Get full path to cache file."""
        ext = ".json.gz" if self.compression else ".json"
        return os.path.join(self.cache_dir, f"{cache_key}{ext}")
    
    def get_cached_data(self, 
                       scraper_name: str, 
                       query: str, 
                       location: str = "") -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached data with TTL support.
        
        Args:
            scraper_name: Name of the scraper
            query: Search query
            location: Location filter
            
        Returns:
            Cached data if available and valid, None otherwise
        """
        cache_key = self._generate_cache_key(scraper_name, query, location)
        
        with self.lock:
            # First check in-memory cache
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                if not entry.is_expired():
                    # Update LRU status
                    entry.touch()
                    self.cache.move_to_end(cache_key)
                    self.hits += 1
                    self.metrics.inc_counter("cache_hits")
                    logger.debug(f"Memory cache hit for {scraper_name}")
                    return entry.data
                else:
                    # Remove expired entry
                    del self.cache[cache_key]
                    logger.debug(f"Removed expired entry for {scraper_name}")
                    self.metrics.inc_counter("cache_expired_removed")
            
            # If not in memory, try file cache
            cache_path = self._get_cache_path(cache_key)
            if os.path.exists(cache_path):
                try:
                    if self.compression:
                        with gzip.open(cache_path, 'rt', encoding='utf-8') as f:
                            data = json.load(f)
                    else:
                        with open(cache_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    
                    # Check file cache timestamp
                    age = time.time() - data.get('timestamp', 0)
                    if age < self.ttl:
                        # Add to memory cache
                        entry = CacheEntry(
                            data=data['results'],
                            metadata=data.get('metadata', {}),
                            ttl_seconds=self.ttl
                        )
                        self.cache[cache_key] = entry
                        self.cache.move_to_end(cache_key)
                        
                        self.hits += 1
                        self.metrics.inc_counter("cache_hits")
                        logger.debug(f"File cache hit for {scraper_name}")
                        return entry.data
                        
                except Exception as e:
                    logger.warning(f"Error reading cache file: {e}")
            
            # Cache miss
            self.misses += 1
            self.metrics.inc_counter("cache_misses")
            return None
    
    def save_to_cache(self, 
                     scraper_name: str, 
                     query: str, 
                     location: str, 
                     results: List[Dict[str, Any]],
                     metadata: Dict[str, Any] = None) -> bool:
        """
        Save data to cache with TTL.
        
        Args:
            scraper_name: Name of the scraper
            query: Search query
            location: Location filter
            results: Data to cache
            metadata: Additional metadata
            
        Returns:
            True if saved successfully
        """
        if not results:
            logger.debug(f"No results to cache for {scraper_name}")
            return False
            
        cache_key = self._generate_cache_key(scraper_name, query, location)
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        metadata.update({
            'scraper': scraper_name,
            'query': query,
            'location': location,
            'count': len(results),
            'timestamp': time.time()
        })
        
        with self.lock:
            # Create cache entry
            entry = CacheEntry(
                data=results,
                metadata=metadata,
                ttl_seconds=self.ttl
            )
            
            # Add to memory cache with LRU
            if len(self.cache) >= self.max_items:
                self.cache.popitem(last=False)  # Remove oldest
                self.evictions += 1
                self.metrics.inc_counter("cache_evictions")
                
            self.cache[cache_key] = entry
            self.cache.move_to_end(cache_key)
            
            # Save to persistent storage
            try:
                cache_data = {
                    'results': results,
                    'metadata': metadata
                }
                
                # Calculate compression savings
                json_data = json.dumps(cache_data, ensure_ascii=False, indent=2)
                json_size = len(json_data.encode('utf-8'))
                
                cache_path = self._get_cache_path(cache_key)
                if self.compression:
                    with gzip.open(cache_path, 'wt', encoding='utf-8',
                                 compresslevel=self.compression_level) as f:
                        f.write(json_data)
                    
                    compressed_size = os.path.getsize(cache_path)
                    saved = json_size - compressed_size
                    self.storage_saved += saved
                    self.metrics.inc_counter("cache_storage_saved", saved)
                else:
                    with open(cache_path, 'w', encoding='utf-8') as f:
                        f.write(json_data)
                
                self.saves += 1
                self.metrics.inc_counter("cache_saves")
                logger.debug(f"Cached {len(results)} results for {scraper_name}")
                return True
                
            except Exception as e:
                logger.error(f"Error writing cache to disk: {e}")
                # Keep in-memory cache even if disk write fails
                return True  
        
        return False
    
    def invalidate_cache(self, 
                        scraper_name: str, 
                        query: str = None, 
                        location: str = None) -> bool:
        """
        Invalidate (remove) cached data.
        
        Args:
            scraper_name: Name of the scraper
            query: Search query (if None, invalidate all queries for this scraper)
            location: Location filter
            
        Returns:
            True if successfully invalidated, False otherwise
        """
        try:
            if query is None:
                # Invalidate all caches for this scraper
                count = 0
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.json') or filename.endswith('.json.gz'):
                        cache_path = os.path.join(self.cache_dir, filename)
                        try:
                            # Handle compressed or uncompressed files
                            if filename.endswith('.gz'):
                                with gzip.open(cache_path, 'rt', encoding='utf-8') as f:
                                    cache_data = json.load(f)
                            else:
                                with open(cache_path, 'r', encoding='utf-8') as f:
                                    cache_data = json.load(f)
                                
                            if cache_data.get('scraper') == scraper_name:
                                os.remove(cache_path)
                                count += 1
                        except:
                            pass
                
                logger.info(f"Invalidated {count} cache entries for {scraper_name}")
                return True
            else:
                # Invalidate specific query cache
                cache_key = self._generate_cache_key(scraper_name, query, location or "")
                
                # Check both compressed and uncompressed paths
                cache_paths = [
                    os.path.join(self.cache_dir, f"{cache_key}.json"),
                    os.path.join(self.cache_dir, f"{cache_key}.json.gz")
                ]
                
                removed = False
                for cache_path in cache_paths:
                    if os.path.exists(cache_path):
                        os.remove(cache_path)
                        logger.info(f"Invalidated cache for {scraper_name} query: {query}")
                        removed = True
                
                if not removed:
                    logger.debug(f"No cache found to invalidate for {scraper_name} query: {query}")
                
                return removed
                
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return False
            
    def process_in_batches(self,
                         data: List[Dict[str, Any]],
                         process_func: Optional[callable] = None,
                         batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Process large datasets in memory-efficient batches.
        
        Args:
            data: Data to process
            process_func: Optional processing function
            batch_size: Optional custom batch size
            
        Returns:
            Processed data
        """
        if not data:
            return []
            
        batch_size = batch_size or self.batch_size
        total = len(data)
        processed = []
        batch_count = (total + batch_size - 1) // batch_size
        
        with ThreadPoolExecutor() as executor:
            # Process batches in parallel
            futures = []
            
            for i in range(0, total, batch_size):
                batch = data[i:i + batch_size]
                if process_func:
                    future = executor.submit(process_func, batch)
                else:
                    future = executor.submit(lambda x: x, batch)
                futures.append(future)
                
            # Collect results
            for i, future in enumerate(futures):
                try:
                    batch_result = future.result()
                    processed.extend(batch_result)
                    
                    # Log progress
                    logger.debug(f"Processed batch {i+1}/{batch_count}")
                    self.metrics.inc_counter("cache_batches_processed")
                    
                except Exception as e:
                    logger.error(f"Error processing batch {i+1}: {e}")
                    self.metrics.inc_counter("cache_batch_errors")
        
        return processed
    
    def has_valid_cache(self, scraper_name: str, query: str, location: str = "") -> bool:
        """Check if valid cache exists."""
        cache_key = self._generate_cache_key(scraper_name, query, location)
        
        with self.lock:
            # Check memory cache first
            if cache_key in self.cache:
                return not self.cache[cache_key].is_expired()
                
            # Check file cache
            cache_path = self._get_cache_path(cache_key)
            if os.path.exists(cache_path):
                try:
                    with (gzip.open if self.compression else open)(cache_path, 'rt') as f:
                        data = json.load(f)
                    age = time.time() - data.get('timestamp', 0)
                    return age < self.ttl
                except:
                    pass
                    
        return False
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            stats = {
                "memory_cache": {
                    "size": len(self.cache),
                    "max_size": self.max_items,
                    "ttl_seconds": self.ttl,
                    "memory_usage_mb": self._estimate_memory_usage()
                },
                "persistence": {
                    "entries": self._count_cache_entries(),
                    "storage_saved_mb": self.storage_saved / (1024 * 1024),
                    "total_size_mb": self.total_cache_size / (1024 * 1024)
                },
                "operations": {
                    "hits": self.hits,
                    "misses": self.misses,
                    "saves": self.saves,
                    "evictions": self.evictions,
                    "hit_ratio": self.hits / max(self.hits + self.misses, 1),
                },
                "metrics": self.metrics.get_metrics()
            }
            return stats
    
    def _count_cache_entries(self) -> int:
        """Count number of cache files."""
        return sum(1 for f in os.listdir(self.cache_dir) 
                  if f.endswith('.json') or f.endswith('.json.gz'))
        
    def clear_cache(self, older_than_hours: Optional[int] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            older_than_hours: Only clear entries older than this
            
        Returns:
            Number of entries cleared
        """
        count = 0
        threshold = time.time() - (older_than_hours * 3600 if older_than_hours else 0)
        
        with self.lock:
            # Clear memory cache
            if older_than_hours:
                expired = [
                    key for key, entry in self.cache.items()
                    if entry.timestamp < threshold
                ]
                for key in expired:
                    del self.cache[key]
                    count += 1
            else:
                count = len(self.cache)
                self.cache.clear()
                
            # Clear file cache
            try:
                for filename in os.listdir(self.cache_dir):
                    if not (filename.endswith('.json') or filename.endswith('.json.gz')):
                        continue
                        
                    cache_path = os.path.join(self.cache_dir, filename)
                    try:
                        if older_than_hours:
                            # Check timestamp
                            with (gzip.open if filename.endswith('.gz') else open)(
                                cache_path, 'rt'
                            ) as f:
                                data = json.load(f)
                            if data.get('metadata', {}).get('timestamp', 0) >= threshold:
                                continue
                                
                        os.remove(cache_path)
                        count += 1
                        
                    except Exception as e:
                        logger.warning(f"Error clearing cache file {filename}: {e}")
                        
            except Exception as e:
                logger.error(f"Error clearing file cache: {e}")
                
        self.metrics.inc_counter("cache_entries_cleared", count)
        logger.info(f"Cleared {count} cache entries")
        return count
            
    def get_scrapers_in_cache(self) -> List[str]:
        """Get list of scrapers with cached data."""
        scrapers = set()
        
        with self.lock:
            # Check memory cache
            for entry in self.cache.values():
                scraper = entry.metadata.get('scraper')
                if scraper:
                    scrapers.add(scraper)
            
            # Check file cache
            for filename in os.listdir(self.cache_dir):
                if not (filename.endswith('.json') or filename.endswith('.json.gz')):
                    continue
                    
                cache_path = os.path.join(self.cache_dir, filename)
                try:
                    with (gzip.open if filename.endswith('.gz') else open)(
                        cache_path, 'rt'
                    ) as f:
                        data = json.load(f)
                    scraper = data.get('metadata', {}).get('scraper')
                    if scraper:
                        scrapers.add(scraper)
                except:
                    pass
                    
        return sorted(scrapers)

    def close(self):
        """Cleanup resources."""
        with self.lock:
            # Export final metrics
            self._update_metrics()
            
            # Clear memory cache
            self.cache.clear()
            
            logger.info("Cache manager closed")
            
# Global instance
_cache_manager = None

def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if not _cache_manager:
        # Get configuration from environment
        _cache_manager = CacheManager(
            ttl_seconds=int(os.getenv('CACHE_TTL', CacheManager.DEFAULT_TTL)),
            max_items=int(os.getenv('CACHE_MAX_ITEMS', CacheManager.DEFAULT_MAX_ITEMS)),
            batch_size=int(os.getenv('CACHE_BATCH_SIZE', CacheManager.DEFAULT_BATCH_SIZE))
        )
    return _cache_manager
