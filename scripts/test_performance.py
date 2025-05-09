#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Testing Script for ScraperMVP

This script measures performance metrics for the scrapers to evaluate
optimization improvements. It runs benchmark tests and reports on:
- Execution time
- Memory usage
- Cache efficiency
- Browser reuse statistics

Usage:
    python test_performance.py --scraper google_maps
    python test_performance.py --scraper paginas_amarillas
    python test_performance.py --scraper all
"""

import time
import logging
import json
import os
import sys
import argparse
import psutil
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# Import scrapers
from scrapers.guialocal_scraper import GuiaLocalScraper
from scrapers.cylex_scraper import CylexScraper
from scrapers.paginas_amarillas_scraper import PaginasAmarillasScraper
from utils.browser_pool import get_browser_pool, shutdown_browser_pool
from utils.cache_manager import get_cache_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/performance_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("performance_test")

# Test data
TEST_QUERIES = [
    {"query": "restaurantes", "location": "Buenos Aires"},
    {"query": "hoteles", "location": "Córdoba"},
    {"query": "cafeterias", "location": "Rosario"},
    {"query": "dentistas", "location": "Mendoza"},
    {"query": "abogados", "location": "La Plata"}
]

def get_cache_stats():
    """Get and log cache statistics"""
    try:
        cache_manager = get_cache_manager()
        stats = cache_manager.get_cache_stats()
        
        logger.info("Cache Statistics:")
        logger.info(f"  - Hit ratio: {stats['hit_ratio']:.2f}")
        logger.info(f"  - Total hits: {stats['hits']}")
        logger.info(f"  - Total misses: {stats['misses']}")
        logger.info(f"  - Total saves: {stats['saves']}")
        logger.info(f"  - Storage saved: {stats['storage_saved_mb']:.2f} MB")
        logger.info(f"  - Total cache size: {stats['total_cache_size_mb']:.2f} MB")
        logger.info(f"  - Cache entries: {stats['cache_entries']}")
        logger.info(f"  - Hits by scraper: {stats['hits_by_scraper']}")
        logger.info(f"  - Age distribution: {stats['age_distribution']}")
        
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return None

def measure_memory() -> Dict[str, float]:
    """Measure current memory usage of the process"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return {
        "rss_mb": memory_info.rss / (1024 * 1024),  # Resident Set Size in MB
        "vms_mb": memory_info.vms / (1024 * 1024),  # Virtual Memory Size in MB
        "percent": process.memory_percent()
    }

def test_scraper_performance(
    scraper_class,
    query: str,
    location: str = "",
    max_results: int = 15,
    use_cache: bool = True,
    use_browser_pool: bool = True,
    **kwargs
) -> tuple:
    """
    Run a single performance test for a scraper.
    Returns: (elapsed_time, num_results, memory_metrics)
    """
    scraper_name = scraper_class.__name__
    logger.info(f"Testing {scraper_name} with query='{query}', location='{location}'")

    # Clear cache for this test if not using cache
    cache_manager = get_cache_manager()
    if not use_cache:
           cache_manager.clear_cache()  # Clear all cache for testing

    # Start measuring memory
    start_memory = measure_memory()

    # Initialize scraper with test parameters
    # For faster tests, disable dynamic analysis on PaginasAmarillasScraper
    if scraper_class.__name__ == 'PaginasAmarillasScraper':
        kwargs['skip_dynamic'] = False
    scraper = scraper_class(
        max_results=max_results,
        use_browser_pool=use_browser_pool,
        use_cache=use_cache,
        **kwargs
    )

    # Start memory tracking
    tracemalloc.start()

    # Measure performance
    start_time = time.time()
    try:
        results = scraper.scrape(query, location)
    finally:
        scraper.close()
    end_time = time.time()

    # Get memory snapshot
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Calculate metrics
    elapsed_time = end_time - start_time
    num_results = len(results) if results else 0

    # Measure final memory
    end_memory = measure_memory()

    # Calculate memory growth
    memory_metrics = {
        "rss_mb_growth": end_memory["rss_mb"] - start_memory["rss_mb"],
        "vms_mb_growth": end_memory["vms_mb"] - start_memory["vms_mb"],
        "peak_mb": peak / (1024 * 1024),
        "final_rss_mb": end_memory["rss_mb"],
        "final_vms_mb": end_memory["vms_mb"]
    }

    logger.info(f"Performance results for {scraper_name}:")
    logger.info(f"  - Elapsed time: {elapsed_time:.2f} seconds")
    logger.info(f"  - Number of results: {num_results}")
    logger.info(f"  - Time per result: {elapsed_time/max(num_results, 1):.2f} seconds/result")
    logger.info(f"  - Memory growth: {memory_metrics['rss_mb_growth']:.2f} MB")
    logger.info(f"  - Peak memory usage: {memory_metrics['peak_mb']:.2f} MB")

    # Log cache stats after run
    get_cache_stats()

    return elapsed_time, num_results, memory_metrics

def main():
    """Run performance tests with different optimization configurations."""
    parser = argparse.ArgumentParser(description="Benchmark performance of scrapers")
    parser.add_argument("--scraper", choices=["all", "guialocal", "cylex", "paginas_amarillas"], 
                        default="all", help="Which scraper to benchmark")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache for testing")
    parser.add_argument("--no-pool", action="store_true", help="Disable browser pool for testing")
    parser.add_argument("--compare", action="store_true", 
                        help="Run comparison between enabled and disabled optimizations")
    parser.add_argument("--limit", type=int, default=None,
                        help="Límite de número de queries a ejecutar")
    
    args = parser.parse_args()
    # Reducir la lista de TEST_QUERIES si se especifica un límite
    if args.limit:
        global TEST_QUERIES
        TEST_QUERIES = TEST_QUERIES[:args.limit]
    
    logger.info("Starting scrapers performance test")
    
    # Determine which scrapers to test
    scrapers = []
    if args.scraper == "all" or args.scraper == "guialocal":
        scrapers.append({"class": GuiaLocalScraper, "name": "GuiaLocal"})
    if args.scraper == "all" or args.scraper == "cylex":
        scrapers.append({"class": CylexScraper, "name": "Cylex"})
    if args.scraper == "all" or args.scraper == "paginas_amarillas":
        scrapers.append({"class": PaginasAmarillasScraper, "name": "PaginasAmarillas"})
    
    # Determine optimization configuration
    use_cache = not args.no_cache
    use_pool = not args.no_pool
    
    # Initialize results dictionary
    results = {}
    optimization_results = {}
    baseline_results = {}
    
    try:
        # Run tests with optimizations enabled
        logger.info(f"Running tests with optimizations: cache={use_cache}, pool={use_pool}")
        
        for test_case in TEST_QUERIES:
            query = test_case["query"]
            location = test_case["location"]
            test_key = f"{query}_{location}"
            
            results[test_key] = {}
            
            for scraper_info in scrapers:
                scraper_class = scraper_info["class"]
                scraper_name = scraper_info["name"]
                
                elapsed_time, num_results, memory_metrics = test_scraper_performance(
                    scraper_class,
                    query,
                    location,
                    max_results=15,
                    use_cache=use_cache,
                    use_browser_pool=use_pool
                )
                
                results[test_key][scraper_name] = {
                    "elapsed_time": elapsed_time,
                    "num_results": num_results,
                    "time_per_result": elapsed_time / max(num_results, 1),
                    "memory_metrics": memory_metrics
                }
        
        # Save optimization results
        optimization_results = results.copy()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        config_name = "optimized"
        if use_cache:
            config_name += "_cache"
        if use_pool:
            config_name += "_pool"
        optimization_file = f"results/performance_{config_name}_{timestamp}.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(optimization_file), exist_ok=True)
        
        with open(optimization_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Optimized performance results saved to {optimization_file}")
        
        # Run comparison tests if requested
        if args.compare:
            # Clear results for baseline test
            results = {}
            
            logger.info("Running baseline tests with optimizations disabled")
            
            for test_case in TEST_QUERIES:
                query = test_case["query"]
                location = test_case["location"]
                test_key = f"{query}_{location}"
                
                results[test_key] = {}
                
                for scraper_info in scrapers:
                    scraper_class = scraper_info["class"]
                    scraper_name = scraper_info["name"]
                    
                    elapsed_time, num_results, memory_metrics = test_scraper_performance(
                        scraper_class,
                        query,
                        location,
                        max_results=15,
                        use_cache=False,
                        use_browser_pool=False
                    )
                    
                    results[test_key][scraper_name] = {
                        "elapsed_time": elapsed_time,
                        "num_results": num_results,
                        "time_per_result": elapsed_time / max(num_results, 1),
                        "memory_metrics": memory_metrics
                    }
            
            # Save baseline results
            baseline_results = results.copy()
            baseline_file = f"results/performance_baseline_{timestamp}.json"
            
            with open(baseline_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Baseline performance results saved to {baseline_file}")
            
            # Generate comparison report
            logger.info("Generating performance comparison report")
            
            comparison = {
                "timestamp": timestamp,
                "optimized_config": {"cache": use_cache, "pool": use_pool},
                "comparisons": {}
            }
            
            # Compare by scraper and calculate improvements
            for scraper_info in scrapers:
                scraper_name = scraper_info["name"]
                scraper_comparison = {
                    "query_improvements": {},
                    "average_improvement": {
                        "time_percent": 0,
                        "memory_percent": 0
                    }
                }
                
                time_improvements = []
                memory_improvements = []
                
                for test_key in optimization_results:
                    if scraper_name in optimization_results[test_key] and scraper_name in baseline_results[test_key]:
                        opt = optimization_results[test_key][scraper_name]
                        base = baseline_results[test_key][scraper_name]
                        
                        # Calculate improvements
                        time_diff = base["elapsed_time"] - opt["elapsed_time"]
                        time_percent = (time_diff / base["elapsed_time"]) * 100 if base["elapsed_time"] > 0 else 0
                        
                        memory_diff = base["memory_metrics"]["peak_mb"] - opt["memory_metrics"]["peak_mb"]
                        memory_percent = (memory_diff / base["memory_metrics"]["peak_mb"]) * 100 if base["memory_metrics"]["peak_mb"] > 0 else 0
                        
                        time_improvements.append(time_percent)
                        memory_improvements.append(memory_percent)
                        
                        scraper_comparison["query_improvements"][test_key] = {
                            "time_seconds_saved": time_diff,
                            "time_percent_improvement": time_percent,
                            "memory_mb_saved": memory_diff,
                            "memory_percent_improvement": memory_percent
                        }
                
                # Calculate averages
                if time_improvements:
                    scraper_comparison["average_improvement"]["time_percent"] = sum(time_improvements) / len(time_improvements)
                
                if memory_improvements:
                    scraper_comparison["average_improvement"]["memory_percent"] = sum(memory_improvements) / len(memory_improvements)
                
                comparison["comparisons"][scraper_name] = scraper_comparison
            
            # Save comparison
            comparison_file = f"results/performance_comparison_{timestamp}.json"
            with open(comparison_file, 'w', encoding='utf-8') as f:
                json.dump(comparison, f, indent=2)
            
            logger.info(f"Performance comparison saved to {comparison_file}")
            
            # Print summary
            logger.info("\n=== PERFORMANCE IMPROVEMENT SUMMARY ===")
            for scraper_name, data in comparison["comparisons"].items():
                logger.info(f"\n{scraper_name}:")
                logger.info(f"  Average time reduction: {data['average_improvement']['time_percent']:.1f}%")
                logger.info(f"  Average memory reduction: {data['average_improvement']['memory_percent']:.1f}%")
    
    finally:
        # Clean up resources
        if 'shutdown_browser_pool' in globals():
            shutdown_browser_pool()
    
    logger.info("Performance testing completed")

if __name__ == "__main__":
    main()
