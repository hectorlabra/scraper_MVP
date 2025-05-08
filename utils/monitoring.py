#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitoring and Metrics System for ScraperMVP

This module provides monitoring functionality to track:
- Performance metrics (execution time, memory usage)
- Success/failure rates
- Request rates and latencies
- Data quality metrics
- Component status and health checks

The metrics can be visualized in dashboards, used for alerting, or exported to monitoring systems.
"""

import time
import os
import psutil
import json
import logging
import threading
import atexit
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from collections import defaultdict, deque
import socket
from pathlib import Path

# Configure basic logger for this module
logger = logging.getLogger(__name__)

class MetricsRegistry:
    """
    Registry for collecting and tracking metrics.
    
    This class provides methods for recording various types of metrics:
    - Counters: For tracking discrete events or occurrences
    - Gauges: For tracking values that can go up and down
    - Histograms: For tracking distributions of values
    - Timers: For tracking durations of operations
    """
    def __init__(self, app_name: str = "scraperMVP"):
        """
        Initialize the metrics registry.
        
        Args:
            app_name: Name of the application for labeling metrics
        """
        self.app_name = app_name
        self.host = socket.gethostname()
        self._counters = defaultdict(int)
        self._gauges = {}
        self._histograms = defaultdict(list)
        self._timers = {}
        self._timer_starts = {}
        self._last_export = datetime.now()
        self._metrics_history = defaultdict(lambda: deque(maxlen=1000))  # Keep last 1000 values for each metric
        
        # Initialize periodic export if enabled
        self._export_interval = None
        self._export_thread = None
        self._exit_event = threading.Event()
        
        # Register shutdown handler
        atexit.register(self.shutdown)
    
    def inc_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Name of the metric
            value: Value to increment by
            labels: Additional labels to apply to the metric
        """
        key = self._make_key(name, labels)
        self._counters[key] += value
        self._metrics_history[f"counter:{key}"].append((datetime.now(), self._counters[key]))
        logger.debug(f"Counter {key} incremented by {value} to {self._counters[key]}")
    
    def dec_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None) -> None:
        """
        Decrement a counter metric.
        
        Args:
            name: Name of the metric
            value: Value to decrement by
            labels: Additional labels to apply to the metric
        """
        key = self._make_key(name, labels)
        self._counters[key] -= value
        self._metrics_history[f"counter:{key}"].append((datetime.now(), self._counters[key]))
        logger.debug(f"Counter {key} decremented by {value} to {self._counters[key]}")
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """
        Set a gauge metric.
        
        Args:
            name: Name of the metric
            value: Value to set
            labels: Additional labels to apply to the metric
        """
        key = self._make_key(name, labels)
        self._gauges[key] = value
        self._metrics_history[f"gauge:{key}"].append((datetime.now(), value))
        logger.debug(f"Gauge {key} set to {value}")
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """
        Record a value in a histogram metric.
        
        Args:
            name: Name of the metric
            value: Value to record
            labels: Additional labels to apply to the metric
        """
        key = self._make_key(name, labels)
        self._histograms[key].append(value)
        self._metrics_history[f"histogram:{key}"].append((datetime.now(), value))
        logger.debug(f"Histogram {key} recorded value {value}")
    
    def start_timer(self, name: str, labels: Dict[str, str] = None) -> str:
        """
        Start a timer for measuring operation duration.
        
        Args:
            name: Name of the timer
            labels: Additional labels to apply to the metric
            
        Returns:
            Timer ID for stopping the timer
        """
        key = self._make_key(name, labels)
        timer_id = f"{key}:{id(threading.current_thread())}:{time.time_ns()}"
        self._timer_starts[timer_id] = time.time()
        logger.debug(f"Timer {timer_id} started")
        return timer_id
    
    def stop_timer(self, timer_id: str) -> float:
        """
        Stop a timer and record the duration.
        
        Args:
            timer_id: Timer ID returned from start_timer
            
        Returns:
            Duration in seconds
        """
        if timer_id not in self._timer_starts:
            logger.warning(f"Timer {timer_id} not found")
            return 0.0
        
        start_time = self._timer_starts.pop(timer_id)
        duration = time.time() - start_time
        
        # Extract the base key from the timer_id
        base_key = timer_id.split(':', 1)[0]
        
        # Update timer stats
        if base_key not in self._timers:
            self._timers[base_key] = {
                "count": 0,
                "sum": 0.0,
                "min": float('inf'),
                "max": 0.0
            }
        
        self._timers[base_key]["count"] += 1
        self._timers[base_key]["sum"] += duration
        self._timers[base_key]["min"] = min(self._timers[base_key]["min"], duration)
        self._timers[base_key]["max"] = max(self._timers[base_key]["max"], duration)
        
        self._metrics_history[f"timer:{base_key}"].append((datetime.now(), duration))
        logger.debug(f"Timer {timer_id} stopped. Duration: {duration:.6f}s")
        
        return duration
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """
        Create a key for a metric with labels.
        
        Args:
            name: Metric name
            labels: Labels to include in the key
            
        Returns:
            String key for the metric
        """
        if not labels:
            return name
        
        # Sort labels to ensure consistent keys
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all current metrics.
        
        Returns:
            Dictionary of all metrics
        """
        # Calculate histogram stats
        histogram_stats = {}
        for name, values in self._histograms.items():
            if values:
                values.sort()
                length = len(values)
                histogram_stats[name] = {
                    "count": length,
                    "sum": sum(values),
                    "min": values[0],
                    "max": values[-1],
                    "avg": sum(values) / length,
                    "median": values[length // 2] if length % 2 else (values[length // 2 - 1] + values[length // 2]) / 2,
                    "p95": values[int(length * 0.95)] if length > 20 else values[-1],
                    "p99": values[int(length * 0.99)] if length > 100 else values[-1]
                }
        
        # Build complete metrics report
        return {
            "timestamp": datetime.now().isoformat(),
            "app": self.app_name,
            "host": self.host,
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": histogram_stats,
            "timers": dict(self._timers)
        }
    
    def reset(self) -> None:
        """
        Reset all metrics.
        """
        self._counters = defaultdict(int)
        self._gauges = {}
        self._histograms = defaultdict(list)
        self._timers = {}
        self._timer_starts = {}
        logger.info("All metrics have been reset")
    
    def export_metrics(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Export current metrics to a file or return as a dictionary.
        
        Args:
            file_path: Path to export metrics to (optional)
            
        Returns:
            Dictionary of metrics
        """
        metrics = self.get_metrics()
        
        if file_path:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            # Write metrics to file
            with open(file_path, 'w') as f:
                json.dump(metrics, f, indent=2)
            
            logger.info(f"Metrics exported to {file_path}")
        
        self._last_export = datetime.now()
        return metrics
    
    def start_periodic_export(self, 
                             interval_seconds: int = 60, 
                             file_path: Optional[str] = None,
                             callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        """
        Start periodic export of metrics.
        
        Args:
            interval_seconds: Export interval in seconds
            file_path: Path to export metrics to (optional)
            callback: Function to call with metrics (optional)
        """
        if self._export_thread is not None:
            logger.warning("Periodic export already running")
            return
        
        self._export_interval = interval_seconds
        self._exit_event.clear()
        
        def export_loop():
            while not self._exit_event.wait(self._export_interval):
                metrics = self.get_metrics()
                
                # Export to file if specified
                if file_path:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    path = Path(file_path)
                    export_path = path.parent / f"{path.stem}_{timestamp}{path.suffix}"
                    
                    with open(export_path, 'w') as f:
                        json.dump(metrics, f, indent=2)
                
                # Call callback if specified
                if callback:
                    try:
                        callback(metrics)
                    except Exception as e:
                        logger.error(f"Error in metrics callback: {e}")
        
        self._export_thread = threading.Thread(target=export_loop, daemon=True)
        self._export_thread.start()
        logger.info(f"Started periodic metrics export every {interval_seconds} seconds")
    
    def stop_periodic_export(self) -> None:
        """
        Stop periodic export of metrics.
        """
        if self._export_thread is None:
            return
        
        self._exit_event.set()
        self._export_thread.join(timeout=5)
        self._export_thread = None
        logger.info("Stopped periodic metrics export")
    
    def shutdown(self) -> None:
        """
        Perform cleanup operations on shutdown.
        """
        self.stop_periodic_export()
        
        # Export final metrics if needed
        if (datetime.now() - self._last_export).total_seconds() > 10:
            try:
                self.export_metrics()
            except Exception as e:
                logger.error(f"Error exporting final metrics: {e}")

class SystemMonitor:
    """
    Monitor system resources (CPU, memory, disk) used by the application.
    """
    def __init__(self, metrics_registry: MetricsRegistry):
        """
        Initialize the system monitor.
        
        Args:
            metrics_registry: Registry to record metrics
        """
        self.metrics = metrics_registry
        self.process = psutil.Process(os.getpid())
        self.monitor_thread = None
        self.stop_event = threading.Event()
    
    def record_current_usage(self) -> Dict[str, float]:
        """
        Record current system resource usage.
        
        Returns:
            Dictionary with current usage metrics
        """
        # CPU usage (percent)
        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
            self.metrics.set_gauge("system.cpu.percent", cpu_percent)
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            cpu_percent = 0
        
        # Memory usage (MB)
        try:
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            self.metrics.set_gauge("system.memory.rss_mb", memory_mb)
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            memory_mb = 0
        
        # Open files count
        try:
            open_files = len(self.process.open_files())
            self.metrics.set_gauge("system.open_files", open_files)
        except Exception as e:
            logger.error(f"Error getting open files count: {e}")
            open_files = 0
        
        # Thread count
        try:
            thread_count = len(self.process.threads())
            self.metrics.set_gauge("system.thread_count", thread_count)
        except Exception as e:
            logger.error(f"Error getting thread count: {e}")
            thread_count = 0
        
        # System-wide metrics
        try:
            disk_usage = psutil.disk_usage('/').percent
            self.metrics.set_gauge("system.disk.percent", disk_usage)
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            disk_usage = 0
        
        return {
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "open_files": open_files,
            "thread_count": thread_count,
            "disk_percent": disk_usage
        }
    
    def start_monitoring(self, interval_seconds: int = 5) -> None:
        """
        Start periodic monitoring of system resources.
        
        Args:
            interval_seconds: Interval between measurements in seconds
        """
        if self.monitor_thread is not None:
            logger.warning("Monitoring already started")
            return
        
        self.stop_event.clear()
        
        def monitor_loop():
            while not self.stop_event.wait(interval_seconds):
                try:
                    self.record_current_usage()
                except Exception as e:
                    logger.error(f"Error in system monitoring: {e}")
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"Started system monitoring every {interval_seconds} seconds")
    
    def stop_monitoring(self) -> None:
        """
        Stop periodic monitoring of system resources.
        """
        if self.monitor_thread is None:
            return
        
        self.stop_event.set()
        self.monitor_thread.join(timeout=5)
        self.monitor_thread = None
        logger.info("Stopped system monitoring")


class ScraperMetrics:
    """
    Track scraper-specific metrics.
    """
    def __init__(self, metrics_registry: MetricsRegistry):
        """
        Initialize scraper metrics.
        
        Args:
            metrics_registry: Registry to record metrics
        """
        self.metrics = metrics_registry
    
    def record_scrape_start(self, scraper_name: str, query: str = None) -> str:
        """
        Record the start of a scraping operation.
        
        Args:
            scraper_name: Name of the scraper
            query: Search query being executed
            
        Returns:
            Timer ID for stopping the timer
        """
        labels = {"scraper": scraper_name}
        if query:
            labels["query"] = query
        
        self.metrics.inc_counter("scraper.operations", labels=labels)
        timer_id = self.metrics.start_timer("scraper.duration", labels=labels)
        return timer_id
    
    def record_scrape_success(self, scraper_name: str, timer_id: str, items_found: int) -> None:
        """
        Record a successful scraping operation.
        
        Args:
            scraper_name: Name of the scraper
            timer_id: Timer ID from record_scrape_start
            items_found: Number of items found
        """
        labels = {"scraper": scraper_name, "result": "success"}
        
        self.metrics.inc_counter("scraper.success", labels=labels)
        self.metrics.record_histogram("scraper.items_found", items_found, labels=labels)
        duration = self.metrics.stop_timer(timer_id)
        
        if items_found > 0:
            # Calculate average time per item
            time_per_item = duration / items_found
            self.metrics.record_histogram("scraper.time_per_item", time_per_item, labels=labels)
    
    def record_scrape_failure(self, scraper_name: str, timer_id: str, error: str) -> None:
        """
        Record a failed scraping operation.
        
        Args:
            scraper_name: Name of the scraper
            timer_id: Timer ID from record_scrape_start
            error: Error message
        """
        labels = {"scraper": scraper_name, "result": "failure", "error": error}
        
        self.metrics.inc_counter("scraper.failure", labels=labels)
        self.metrics.stop_timer(timer_id)
    
    def record_request(self, scraper_name: str, url: str, success: bool, status_code: int = None) -> None:
        """
        Record a web request.
        
        Args:
            scraper_name: Name of the scraper
            url: URL of the request
            success: Whether the request was successful
            status_code: HTTP status code
        """
        labels = {
            "scraper": scraper_name,
            "host": url.split('/')[2] if '://' in url else url.split('/')[0]
        }
        
        if status_code:
            labels["status_code"] = str(status_code)
        
        self.metrics.inc_counter("scraper.requests", labels=labels)
        
        if success:
            self.metrics.inc_counter("scraper.requests.success", labels=labels)
        else:
            self.metrics.inc_counter("scraper.requests.failure", labels=labels)
    
    def record_rate_limit(self, scraper_name: str, host: str, retry_after: int = None) -> None:
        """
        Record a rate limit event.
        
        Args:
            scraper_name: Name of the scraper
            host: Host that imposed the rate limit
            retry_after: Seconds to wait before retrying
        """
        labels = {"scraper": scraper_name, "host": host}
        
        self.metrics.inc_counter("scraper.rate_limits", labels=labels)
        
        if retry_after:
            self.metrics.record_histogram("scraper.rate_limit.retry_seconds", retry_after, labels=labels)
    
    def record_data_quality(self, scraper_name: str, complete_records: int, incomplete_records: int) -> None:
        """
        Record data quality metrics.
        
        Args:
            scraper_name: Name of the scraper
            complete_records: Number of complete records
            incomplete_records: Number of incomplete records
        """
        labels = {"scraper": scraper_name}
        
        total_records = complete_records + incomplete_records
        
        if total_records > 0:
            completeness_pct = (complete_records / total_records) * 100
            self.metrics.set_gauge("scraper.data_quality.completeness_pct", completeness_pct, labels=labels)
        
        self.metrics.set_gauge("scraper.data_quality.complete_records", complete_records, labels=labels)
        self.metrics.set_gauge("scraper.data_quality.incomplete_records", incomplete_records, labels=labels)

# Create global instances
metrics_registry = MetricsRegistry(app_name="scraperMVP")
system_monitor = SystemMonitor(metrics_registry)
scraper_metrics = ScraperMetrics(metrics_registry)

def initialize_monitoring(
    metrics_export_path: str = None,
    metrics_export_interval: int = 60,
    enable_system_monitoring: bool = True,
    system_monitoring_interval: int = 30
) -> Tuple[MetricsRegistry, SystemMonitor, ScraperMetrics]:
    """
    Initialize the monitoring system.
    
    Args:
        metrics_export_path: Path to export metrics to
        metrics_export_interval: Interval for exporting metrics in seconds
        enable_system_monitoring: Whether to enable system monitoring
        system_monitoring_interval: Interval for system monitoring in seconds
        
    Returns:
        Tuple of (MetricsRegistry, SystemMonitor, ScraperMetrics)
    """
    # Start metrics export if path provided
    if metrics_export_path:
        metrics_registry.start_periodic_export(
            interval_seconds=metrics_export_interval,
            file_path=metrics_export_path
        )
    
    # Start system monitoring if enabled
    if enable_system_monitoring:
        system_monitor.start_monitoring(interval_seconds=system_monitoring_interval)
    
    return metrics_registry, system_monitor, scraper_metrics

def shutdown_monitoring() -> None:
    """
    Shutdown the monitoring system.
    """
    system_monitor.stop_monitoring()
    metrics_registry.stop_periodic_export()
    
    # Export final metrics
    try:
        metrics_registry.export_metrics()
    except Exception as e:
        logger.error(f"Error exporting final metrics: {e}")
