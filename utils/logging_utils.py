#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Logging Utilities for ScraperMVP

This module provides enhanced logging functionality including:
- Structured logging with JSON formatting
- Rotating file handlers to manage log file sizes
- Different severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Context tracking for correlation across components
- Log filtering and masking for sensitive information
- Integration with monitoring and alerting systems
"""

import logging
import logging.handlers
import os
import json
import socket
import sys
import time
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Union, List, Callable

# Custom log levels for more granular logging
TRACE = 5  # More detailed than DEBUG
logging.addLevelName(TRACE, "TRACE")

# Define a severity mapping dict to align with common monitoring systems
SEVERITY_MAP = {
    logging.CRITICAL: "CRITICAL",
    logging.ERROR: "ERROR",
    logging.WARNING: "WARNING",
    logging.INFO: "INFO",
    logging.DEBUG: "DEBUG",
    TRACE: "TRACE"
}

class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after formatting the log record.
    """
    def __init__(self, **kwargs):
        """
        Initialize the formatter with specified JSON fields.
        """
        self.json_fields = kwargs
        self.hostname = socket.gethostname()
        
    def format(self, record):
        """
        Format the specified record as JSON.
        """
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": SEVERITY_MAP.get(record.levelno, record.levelname),
            "name": record.name,
            "message": record.getMessage(),
            "logger": record.name,
            "path": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
            "hostname": self.hostname,
        }
        
        # Add thread and process info in threading/multiprocessing contexts
        log_data["thread"] = record.threadName
        log_data["thread_id"] = record.thread
        log_data["process"] = record.processName
        log_data["process_id"] = record.process
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add any custom fields
        for field, value in self.json_fields.items():
            if callable(value):
                log_data[field] = value()
            else:
                log_data[field] = value
        
        # Add any extra attributes from the record
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text",
                          "filename", "funcName", "id", "levelname", "levelno",
                          "lineno", "module", "msecs", "message", "msg", "name",
                          "pathname", "process", "processName", "relativeCreated",
                          "stack_info", "thread", "threadName"]:
                log_data[key] = value
        
        return json.dumps(log_data)

class ContextualLogger(logging.Logger):
    """
    Logger that can track context across log calls.
    """
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        self.context = {}
        self.correlation_id = None
    
    def with_context(self, **context):
        """
        Set context values to be included in all subsequent log messages.
        """
        self.context.update(context)
        return self
    
    def clear_context(self):
        """
        Clear all context values.
        """
        self.context.clear()
        return self
    
    def with_correlation_id(self, correlation_id=None):
        """
        Set a correlation ID for tracking related log entries.
        If no ID is provided, a new UUID is generated.
        """
        self.correlation_id = correlation_id or str(uuid.uuid4())
        return self
    
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False,
            stacklevel=1, **kwargs):
        """
        Override _log to include context and correlation ID in log records.
        """
        if extra is None:
            extra = {}
        
        # Include context in the log record
        if self.context:
            extra.update(self.context)
        
        # Include correlation ID if set
        if self.correlation_id:
            extra["correlation_id"] = self.correlation_id
        
        # Add any keyword arguments as extra fields
        if kwargs:
            extra.update(kwargs)
        
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)
    
    def trace(self, msg, *args, **kwargs):
        """
        Log a message with TRACE level.
        """
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kwargs)

def create_rotating_log_handler(
    log_file: str,
    max_bytes: int = 10_485_760,  # 10MB
    backup_count: int = 5,
    encoding: str = "utf-8"
) -> logging.handlers.RotatingFileHandler:
    """
    Create a rotating file handler for log rotation based on size.
    
    Args:
        log_file: Path to the log file
        max_bytes: Maximum size of the log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
        encoding: File encoding (default: utf-8)
    
    Returns:
        RotatingFileHandler instance
    """
    return logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding=encoding
    )

def create_timed_rotating_log_handler(
    log_file: str,
    when: str = "midnight",
    interval: int = 1,
    backup_count: int = 7,
    encoding: str = "utf-8"
) -> logging.handlers.TimedRotatingFileHandler:
    """
    Create a time-based rotating file handler for log rotation.
    
    Args:
        log_file: Path to the log file
        when: When to rotate (default: 'midnight', other options: 'S', 'M', 'H', 'D', 'W0'-'W6')
        interval: How many units to wait before rotating (default: 1)
        backup_count: Number of backup files to keep (default: 7)
        encoding: File encoding (default: utf-8)
    
    Returns:
        TimedRotatingFileHandler instance
    """
    return logging.handlers.TimedRotatingFileHandler(
        filename=log_file,
        when=when,
        interval=interval,
        backupCount=backup_count,
        encoding=encoding
    )

class SensitiveDataFilter(logging.Filter):
    """
    Filter for masking sensitive data in log records.
    """
    def __init__(self, patterns=None):
        """
        Initialize the filter with the specified patterns.
        
        Args:
            patterns: Dictionary mapping field names to regex patterns
        """
        super().__init__()
        self.patterns = patterns or {
            "password": r"password[\"']?\s*:\s*[\"']([^\"']+)[\"']",
            "api_key": r"api_key[\"']?\s*:\s*[\"']([^\"']+)[\"']",
            "auth": r"auth[\"']?\s*:\s*[\"']([^\"']+)[\"']",
            "token": r"token[\"']?\s*:\s*[\"']([^\"']+)[\"']",
            "authorization": r"Authorization[\"']?\s*:\s*[\"']([^\"']+)[\"']",
            "secret": r"secret[\"']?\s*:\s*[\"']([^\"']+)[\"']",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
        }
        
        import re
        self.compiled_patterns = {k: re.compile(v) for k, v in self.patterns.items()}
    
    def filter(self, record):
        """
        Filter log records to mask sensitive data.
        """
        if isinstance(record.msg, str):
            for pattern_name, pattern in self.compiled_patterns.items():
                # Replace with masked value (keeping first and last character if possible)
                mask_length = 6  # Default mask length
                record.msg = pattern.sub(
                    lambda m: m.group(0).replace(
                        m.group(1),
                        m.group(1)[0] + "*" * mask_length + (m.group(1)[-1] if len(m.group(1)) > 1 else "")
                    ),
                    record.msg
                )
        
        # Also check in any extra fields
        for key in record.__dict__:
            if isinstance(record.__dict__[key], str):
                for pattern_name, pattern in self.compiled_patterns.items():
                    record.__dict__[key] = pattern.sub(
                        lambda m: m.group(0).replace(
                            m.group(1), 
                            m.group(1)[0] + "*" * 6 + (m.group(1)[-1] if len(m.group(1)) > 1 else "")
                        ),
                        record.__dict__[key]
                    )
        
        return True

def setup_advanced_logger(
    name: str,
    log_dir: str = None,
    log_file: str = None,
    console: bool = True,
    log_level: str = "INFO",
    json_format: bool = False,
    rotate_logs: bool = True,
    max_bytes: int = 10_485_760,  # 10MB
    backup_count: int = 5,
    filter_sensitive: bool = True,
    context: Dict[str, Any] = None
) -> ContextualLogger:
    """
    Set up an advanced logger with file and console handlers.
    
    Args:
        name: Logger name
        log_dir: Directory for log files (default: None, uses current dir)
        log_file: Path to log file (optional)
        console: Whether to log to console (default: True)
        log_level: Logging level (default: "INFO")
        json_format: Whether to use JSON formatting (default: False)
        rotate_logs: Whether to use log rotation (default: True)
        max_bytes: Maximum size for log rotation (default: 10MB)
        backup_count: Number of backup files for rotation (default: 5)
        filter_sensitive: Whether to filter sensitive data (default: True)
        context: Initial context values to include in logs (default: None)
    
    Returns:
        Configured ContextualLogger
    """
    # Register the ContextualLogger class
    logging.setLoggerClass(ContextualLogger)
    
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    logger.handlers = []  # Clear existing handlers
    
    # Determine log file path if directory is provided but not specific file
    if log_dir and not log_file:
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f"{name}_{timestamp}.log")
    
    # Create formatters
    if json_format:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Add file handler if specified
    if log_file:
        if rotate_logs:
            file_handler = create_rotating_log_handler(
                log_file, max_bytes=max_bytes, backup_count=backup_count
            )
        else:
            file_handler = logging.FileHandler(log_file)
        
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Add console handler if specified
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add sensitive data filter if specified
    if filter_sensitive:
        sensitive_filter = SensitiveDataFilter()
        for handler in logger.handlers:
            handler.addFilter(sensitive_filter)
    
    # Set initial context if provided
    if context and isinstance(logger, ContextualLogger):
        logger.with_context(**context)
    
    return logger

# Make trace method available at module level
def trace(self, msg, *args, **kwargs):
    """
    Log a message with TRACE level.
    """
    if self.isEnabledFor(TRACE):
        self._log(TRACE, msg, args, **kwargs)

# Add trace method to the Logger class
logging.Logger.trace = trace
