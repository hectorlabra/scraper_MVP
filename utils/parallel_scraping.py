#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parallel Scraping Utilities

This module provides utilities for parallel execution of scraping tasks
using ThreadPoolExecutor to improve performance. It includes classes and functions
for managing parallel scraping tasks with proper error handling, progress tracking,
and resource management.

Key components:
- ScraperTask: Represents a single scraping task to be executed
- ParallelScraper: Manages parallel execution of multiple scraping tasks
- Helper functions for creating and running scraper tasks

Usage example:
    # Create parallel scraper manager with 4 workers
    parallel_scraper = ParallelScraper(max_workers=4, show_progress=True)
    
    # Create and add tasks
    for query, location in queries:
        task = ScraperTask(
            task_id=f"search_{query}_{location}",
            scraper_instance=my_scraper,
            method_name='scrape',
            args=[query, location]
        )
        parallel_scraper.add_task(task)
    
    # Execute all tasks in parallel
    results = parallel_scraper.execute_all()
    
    # Access the combined results
    all_data = parallel_scraper.get_all_results()
"""

import time
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional, Tuple, Union, Set
from tqdm import tqdm

# Setup logger
logger = logging.getLogger(__name__)

class ScraperTask:
    """Class to represent a scraping task for parallel execution."""
    
    def __init__(self, 
                 task_id: str,
                 scraper_instance: Any, 
                 method_name: str,
                 args: List[Any] = None,
                 kwargs: Dict[str, Any] = None):
        """
        Initialize a scraper task.
        
        Args:
            task_id: Unique identifier for the task
            scraper_instance: Instance of a scraper class
            method_name: Name of the method to call on the scraper
            args: Positional arguments to pass to the method
            kwargs: Keyword arguments to pass to the method
        """
        self.task_id = task_id
        self.scraper_instance = scraper_instance
        self.method_name = method_name
        self.args = args or []
        self.kwargs = kwargs or {}
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        
    def execute(self) -> Tuple[str, Union[List[Dict[str, Any]], Exception]]:
        """
        Execute the scraper task.
        
        Returns:
            Tuple of (task_id, result or exception)
        """
        self.start_time = time.time()
        try:
            # Get the method from the scraper instance
            method = getattr(self.scraper_instance, self.method_name)
            
            # Execute the method with the provided arguments
            result = method(*self.args, **self.kwargs)
            
            self.result = result
            return self.task_id, result
        except Exception as e:
            logger.error(f"Error executing task {self.task_id}: {str(e)}")
            self.error = e
            return self.task_id, e
        finally:
            self.end_time = time.time()
    
    def get_execution_time(self) -> Optional[float]:
        """
        Get the execution time of the task in seconds.
        
        Returns:
            Execution time in seconds or None if task hasn't completed
        """
        if self.start_time is None or self.end_time is None:
            return None
        return self.end_time - self.start_time


class ParallelScraper:
    """
    Class to manage parallel execution of scraping tasks.
    
    Uses ThreadPoolExecutor to run multiple scraping tasks concurrently,
    with proper exception handling and progress tracking.
    """
    
    def __init__(self, max_workers: int = 4, show_progress: bool = True):
        """
        Initialize the parallel scraper manager.
        
        Args:
            max_workers: Maximum number of worker threads to use
            show_progress: Whether to show a progress bar
        """
        self.max_workers = max_workers
        self.show_progress = show_progress
        self.tasks = []
        self.results = {}
        self.errors = {}
        self.completed_task_ids = set()
        
    def add_task(self, task: ScraperTask) -> None:
        """
        Add a scraping task to the queue.
        
        Args:
            task: ScraperTask instance to add
        """
        self.tasks.append(task)
        
    def add_tasks_from_config(self, 
                              scraper_configs: List[Dict[str, Any]], 
                              scraper_factory: Callable) -> None:
        """
        Add multiple tasks based on configuration dictionaries.
        
        Args:
            scraper_configs: List of configuration dictionaries
            scraper_factory: Function that creates a scraper instance from a config
        """
        for i, config in enumerate(scraper_configs):
            # Create a scraper instance using the factory function
            scraper = scraper_factory(config)
            
            # Extract method name and arguments from config
            method_name = config.get('method_name', 'scrape')
            args = config.get('args', [])
            kwargs = config.get('kwargs', {})
            
            # Create a unique task ID
            task_id = f"task_{i+1}_{method_name}"
            
            # Create and add the task
            task = ScraperTask(
                task_id=task_id,
                scraper_instance=scraper,
                method_name=method_name,
                args=args,
                kwargs=kwargs
            )
            self.add_task(task)
    
    def execute_all(self) -> Dict[str, Any]:
        """
        Execute all tasks in parallel using ThreadPoolExecutor.
        
        Returns:
            Dictionary with results and statistics
        """
        if not self.tasks:
            logger.warning("No tasks to execute")
            return {"results": {}, "errors": {}, "stats": self._generate_stats()}
        
        start_time = time.time()
        logger.info(f"Starting parallel execution of {len(self.tasks)} tasks with {self.max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks to the executor
            future_to_task = {executor.submit(task.execute): task for task in self.tasks}
            
            # Process results as they complete
            total_tasks = len(future_to_task)
            completed = 0
            
            # Setup progress bar if requested
            pbar = None
            if self.show_progress:
                pbar = tqdm(total=total_tasks, desc="Scraping Progress")
            
            try:
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        task_id, result = future.result()
                        
                        # Check if result is an exception
                        if isinstance(result, Exception):
                            self.errors[task_id] = {
                                "error": str(result),
                                "traceback": traceback.format_exc()
                            }
                        else:
                            self.results[task_id] = result
                            self.completed_task_ids.add(task_id)
                        
                        # Update progress bar
                        completed += 1
                        if pbar:
                            pbar.update(1)
                            
                    except Exception as e:
                        logger.error(f"Exception while getting result of {task.task_id}: {str(e)}")
                        self.errors[task.task_id] = {
                            "error": str(e),
                            "traceback": traceback.format_exc()
                        }
                        
                        # Update progress bar
                        completed += 1
                        if pbar:
                            pbar.update(1)
            finally:
                if pbar:
                    pbar.close()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Generate statistics
        stats = self._generate_stats()
        stats["execution_time"] = execution_time
        
        return {
            "results": self.results,
            "errors": self.errors,
            "stats": stats
        }
    
    def _generate_stats(self) -> Dict[str, Any]:
        """
        Generate statistics about the executed tasks.
        
        Returns:
            Dictionary with task execution statistics
        """
        total_tasks = len(self.tasks)
        successful_tasks = len(self.results)
        failed_tasks = len(self.errors)
        
        # Calculate average execution time for completed tasks
        execution_times = []
        for task in self.tasks:
            if task.get_execution_time() is not None:
                execution_times.append(task.get_execution_time())
        
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        return {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "completion_rate": (successful_tasks / total_tasks) * 100 if total_tasks > 0 else 0,
            "avg_execution_time": avg_execution_time
        }
    
    def get_all_results(self) -> List[Dict[str, Any]]:
        """
        Get all successful results combined into a single list.
        
        Returns:
            Combined list of all successful results
        """
        all_results = []
        for result_list in self.results.values():
            if isinstance(result_list, list):
                all_results.extend(result_list)
            else:
                # If the result isn't a list, add it directly
                all_results.append(result_list)
        return all_results
    
    def get_task_errors(self) -> Dict[str, Any]:
        """
        Get all errors that occurred during execution.
        
        Returns:
            Dictionary mapping task IDs to error information
        """
        return self.errors
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Returns:
            Dictionary with execution statistics
        """
        return self._generate_stats()
    
    def cleanup_resources(self):
        """
        Clean up resources used by tasks, such as closing browser instances.
        Call this method after execute_all() to ensure proper resource cleanup.
        """
        for task in self.tasks:
            try:
                # Check if the scraper instance has a close method
                if hasattr(task.scraper_instance, 'close'):
                    logger.debug(f"Closing scraper instance for task {task.task_id}")
                    task.scraper_instance.close()
                    
                # Check for quit method (common in Selenium)
                elif hasattr(task.scraper_instance, 'quit'):
                    logger.debug(f"Quitting scraper instance for task {task.task_id}")
                    task.scraper_instance.quit()
            except Exception as e:
                logger.warning(f"Error cleaning up resources for task {task.task_id}: {str(e)}")
        
        logger.info(f"Cleaned up resources for {len(self.tasks)} tasks")


# Utility functions for parallel scraping

def create_scraper_tasks_from_search_queries(
    scraper_class: Any, 
    search_queries: List[Dict[str, str]], 
    scraper_config: Dict[str, Any] = None,
    reuse_scraper: bool = False
) -> List[ScraperTask]:
    """
    Create scraper tasks from a list of search queries.
    
    Args:
        scraper_class: Scraper class to instantiate
        search_queries: List of dictionaries with 'query' and 'location' keys
        scraper_config: Configuration for the scraper instance
        reuse_scraper: Whether to reuse a single scraper instance for all tasks (True) 
                       or create a new instance for each task (False)
        
    Returns:
        List of ScraperTask instances
    """
    tasks = []
    
    # Use empty dict if scraper_config is None
    config = scraper_config or {}
    
    # Create a single scraper instance to reuse if requested
    shared_scraper = None
    if reuse_scraper:
        shared_scraper = scraper_class(**config)
    
    for i, search in enumerate(search_queries):
        query = search.get('query', '')
        location = search.get('location', '')
        
        if not query:
            continue
        
        # Create task ID based on query and location
        task_id = f"search_{i}_{query}_{location}".replace(' ', '_')
        
        # Determine which scraper instance to use
        scraper = shared_scraper if reuse_scraper else scraper_class(**config)
        
        # Create task for this search query
        task = ScraperTask(
            task_id=task_id,
            scraper_instance=scraper,
            method_name='scrape',
            args=[query, location]
        )
        
        tasks.append(task)
    
    return tasks


def run_parallel_scraper_from_config(
    scraper_class: Any,
    config: Dict[str, Any],
    search_queries: List[Dict[str, str]],
    max_workers: int = None,
    show_progress: bool = True
) -> Dict[str, Any]:
    """
    Run a parallel scraper from configuration.
    
    Args:
        scraper_class: Scraper class to instantiate
        config: Scraper configuration
        search_queries: List of search queries
        max_workers: Maximum worker threads (if None, uses CPU count * 2)
        show_progress: Whether to show a progress bar
        
    Returns:
        Dictionary with results, errors, and statistics
    """
    # Configure number of workers
    if max_workers is None:
        import os
        max_workers = os.cpu_count() * 2 or 4
    
    # Create scraper configuration without search queries
    scraper_config = {k: v for k, v in config.items() if k != 'search_queries'}
    
    # Create tasks from search queries
    tasks = create_scraper_tasks_from_search_queries(
        scraper_class=scraper_class,
        search_queries=search_queries,
        scraper_config=scraper_config,
        reuse_scraper=False  # Create a separate instance for each query to avoid sharing state
    )
    
    # Initialize parallel scraper
    parallel_scraper = ParallelScraper(max_workers=max_workers, show_progress=show_progress)
    
    # Add tasks
    for task in tasks:
        parallel_scraper.add_task(task)
    
    # Execute all tasks
    results = parallel_scraper.execute_all()
    
    # Clean up resources
    parallel_scraper.cleanup_resources()
    
    # Process and format results
    all_results = []
    for task_id, task_results in results['results'].items():
        # Add source and query info to results if not already present
        if isinstance(task_results, list):
            # Extract query and location from task_id
            parts = task_id.split('_')
            if len(parts) >= 4:
                query_parts = parts[2:-1]  # Skip 'search', index, and location
                location = parts[-1]
                
                query = '_'.join(query_parts)
                
                for result in task_results:
                    if 'source' not in result:
                        # Use class name as source
                        result['source'] = scraper_class.__name__.lower().replace('scraper', '')
                    
                    if 'query' not in result:
                        result['query'] = query.replace('_', ' ')
                    
                    if 'location' not in result:
                        result['location'] = location.replace('_', ' ')
            
            all_results.extend(task_results)
    
    # Add statistics
    results['all_results'] = all_results
    
    return results
