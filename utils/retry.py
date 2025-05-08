#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Retry Utilities for ScraperMVP

This module provides utilities for implementing retry logic for operations
that may fail due to transient errors. It includes:
- Decorators for automatic retries
- Retry strategies (constant, exponential backoff, etc.)
- Customizable retry conditions
- Jitter to prevent retry storms
- Circuit breakers to prevent repeated failures
"""

import time
import random
import logging
import functools
import inspect
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Callable, Type, Tuple
from enum import Enum, auto

# Configure logger
logger = logging.getLogger(__name__)

class RetryStrategy(Enum):
    """
    Strategies for determining retry delay.
    """
    CONSTANT = auto()       # Constant delay between retries
    LINEAR = auto()         # Linearly increasing delay
    EXPONENTIAL = auto()    # Exponentially increasing delay
    FIBONACCI = auto()      # Fibonacci sequence delay

class RetryException(Exception):
    """
    Exception raised when maximum retries are exceeded.
    """
    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception

class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent repeated failures.
    """
    CLOSED = "closed"       # Normal operation, requests pass through
    OPEN = "open"           # Failing, requests immediately fail
    HALF_OPEN = "half_open" # Testing if service is back, limited requests pass
    
    def __init__(self, 
                failure_threshold: int = 5, 
                recovery_timeout: int = 60,
                half_open_max_calls: int = 1):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying to recover
            half_open_max_calls: Max calls to allow in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_call_count = 0
        
        # Thread safety
        self.lock = threading.RLock()
    
    def __call__(self, func):
        """
        Decorator to apply circuit breaker to a function.
        
        Args:
            func: Function to decorate
        
        Returns:
            Wrapped function
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                if self.state == self.OPEN:
                    # Check if recovery timeout has elapsed
                    if (datetime.now() - self.last_failure_time).total_seconds() >= self.recovery_timeout:
                        logger.info(f"Circuit breaker for {func.__name__} transitioning from OPEN to HALF_OPEN")
                        self.state = self.HALF_OPEN
                        self.half_open_call_count = 0
                    else:
                        # Still in timeout, fail fast
                        logger.warning(f"Circuit breaker for {func.__name__} is OPEN, failing fast")
                        raise RetryException(f"Circuit breaker for {func.__name__} is open")
                
                if self.state == self.HALF_OPEN and self.half_open_call_count >= self.half_open_max_calls:
                    # Max calls in half-open state reached, fail fast
                    logger.warning(f"Circuit breaker for {func.__name__} is HALF_OPEN with max calls reached, failing fast")
                    raise RetryException(f"Circuit breaker for {func.__name__} is half-open with max calls reached")
                
                # Increment half-open call counter if needed
                if self.state == self.HALF_OPEN:
                    self.half_open_call_count += 1
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Success - reset circuit breaker
                with self.lock:
                    if self.state != self.CLOSED:
                        logger.info(f"Circuit breaker for {func.__name__} recovered, transitioning to CLOSED")
                    self.state = self.CLOSED
                    self.failure_count = 0
                    self.half_open_call_count = 0
                
                return result
                
            except Exception as e:
                # Failure - update circuit breaker state
                with self.lock:
                    self.failure_count += 1
                    self.last_failure_time = datetime.now()
                    
                    if self.state == self.CLOSED and self.failure_count >= self.failure_threshold:
                        logger.warning(f"Circuit breaker for {func.__name__} transitioning from CLOSED to OPEN after {self.failure_count} failures")
                        self.state = self.OPEN
                    
                    elif self.state == self.HALF_OPEN:
                        logger.warning(f"Circuit breaker for {func.__name__} transitioning from HALF_OPEN to OPEN after failure during recovery")
                        self.state = self.OPEN
                
                # Re-raise the original exception
                raise
        
        return wrapper
    
    def reset(self) -> None:
        """
        Manually reset the circuit breaker to closed state.
        """
        with self.lock:
            self.state = self.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            self.half_open_call_count = 0
    
    def get_state(self) -> str:
        """
        Get the current state of the circuit breaker.
        
        Returns:
            Current state (CLOSED, OPEN, or HALF_OPEN)
        """
        with self.lock:
            return self.state

def retry(max_retries: int = 3, 
         delay: float = 1.0, 
         max_delay: float = 60.0,
         strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
         exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
         on_retry: Optional[Callable[[int, Exception, float], None]] = None,
         jitter: bool = True,
         jitter_factor: float = 0.5,
         circuit_breaker: Optional[CircuitBreaker] = None,
         retry_condition: Optional[Callable[[Exception], bool]] = None):
    """
    Decorator for retrying functions on failure.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        strategy: Retry delay strategy to use
        exceptions: Exception types to catch and retry on
        on_retry: Callback function to call before each retry
        jitter: Whether to add random jitter to delays
        jitter_factor: Factor to apply to jitter (0-1)
        circuit_breaker: Circuit breaker instance to use
        retry_condition: Function to determine whether to retry based on the exception
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            
            # Use fibonacci sequence for delay calculation if needed
            fib = [1, 1]
            
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    # Check if we should retry based on custom condition
                    if retry_condition and not retry_condition(e):
                        logger.debug(f"Not retrying {func.__name__} because retry condition returned False")
                        raise
                    
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Maximum retries ({max_retries}) exceeded for {func.__name__}")
                        raise RetryException(
                            f"Maximum retries ({max_retries}) exceeded for {func.__name__}",
                            last_exception=e
                        ) from e
                    
                    # Calculate delay based on strategy
                    if strategy == RetryStrategy.CONSTANT:
                        current_delay = delay
                    elif strategy == RetryStrategy.LINEAR:
                        current_delay = delay * retries
                    elif strategy == RetryStrategy.EXPONENTIAL:
                        current_delay = delay * (2 ** (retries - 1))
                    elif strategy == RetryStrategy.FIBONACCI:
                        # Generate next Fibonacci number if needed
                        if retries + 1 >= len(fib):
                            fib.append(fib[-1] + fib[-2])
                        current_delay = delay * fib[retries]
                    
                    # Apply jitter if enabled
                    if jitter:
                        jitter_amount = random.uniform(-jitter_factor, jitter_factor)
                        current_delay = max(0.001, current_delay * (1 + jitter_amount))
                    
                    # Cap delay at max_delay
                    current_delay = min(current_delay, max_delay)
                    
                    logger.warning(f"Retry {retries}/{max_retries} for {func.__name__} after error: {str(e)}. "
                                   f"Waiting {current_delay:.2f} seconds.")
                    
                    # Call on_retry callback if provided
                    if on_retry:
                        try:
                            on_retry(retries, e, current_delay)
                        except Exception as callback_error:
                            logger.error(f"Error in retry callback: {str(callback_error)}")
                    
                    # Wait before retrying
                    time.sleep(current_delay)
        
        # Apply circuit breaker if provided
        if circuit_breaker:
            wrapper = circuit_breaker(wrapper)
        
        return wrapper
    
    return decorator

class RetryManager:
    """
    Manager for configuring and applying retry logic across multiple functions.
    """
    def __init__(self):
        """
        Initialize retry manager.
        """
        self.default_config = {
            "max_retries": 3,
            "delay": 1.0,
            "max_delay": 60.0,
            "strategy": RetryStrategy.EXPONENTIAL,
            "jitter": True,
            "jitter_factor": 0.5
        }
        
        self.special_configs = {}
        self.circuit_breakers = {}
    
    def set_default_config(self, **kwargs) -> None:
        """
        Set default retry configuration.
        
        Args:
            **kwargs: Configuration parameters to set
        """
        self.default_config.update(kwargs)
    
    def set_special_config(self, function_pattern: str, **kwargs) -> None:
        """
        Set special retry configuration for functions matching a pattern.
        
        Args:
            function_pattern: Pattern to match function names against
            **kwargs: Configuration parameters to set
        """
        self.special_configs[function_pattern] = kwargs
    
    def create_circuit_breaker(self, name: str, **kwargs) -> CircuitBreaker:
        """
        Create and register a circuit breaker.
        
        Args:
            name: Name of the circuit breaker
            **kwargs: Circuit breaker parameters
            
        Returns:
            Circuit breaker instance
        """
        circuit_breaker = CircuitBreaker(**kwargs)
        self.circuit_breakers[name] = circuit_breaker
        return circuit_breaker
    
    def get_config_for_function(self, func_name: str) -> Dict[str, Any]:
        """
        Get the retry configuration for a function.
        
        Args:
            func_name: Name of the function
            
        Returns:
            Configuration dictionary
        """
        # Start with default config
        config = self.default_config.copy()
        
        # Apply special configs that match the function name
        for pattern, special_config in self.special_configs.items():
            import re
            if re.search(pattern, func_name):
                config.update(special_config)
        
        return config
    
    def apply(self, func=None, circuit_breaker_name: str = None, **kwargs):
        """
        Apply retry logic to a function.
        
        Args:
            func: Function to decorate (optional)
            circuit_breaker_name: Name of circuit breaker to use (optional)
            **kwargs: Override configuration parameters
            
        Returns:
            Decorated function or decorator
        """
        def decorator(func):
            # Get base configuration for the function
            func_name = f"{func.__module__}.{func.__name__}"
            config = self.get_config_for_function(func_name)
            
            # Override with provided kwargs
            config.update(kwargs)
            
            # Get circuit breaker if specified
            cb = None
            if circuit_breaker_name and circuit_breaker_name in self.circuit_breakers:
                cb = self.circuit_breakers[circuit_breaker_name]
            
            # Apply retry decorator
            return retry(
                max_retries=config["max_retries"],
                delay=config["delay"],
                max_delay=config["max_delay"],
                strategy=config["strategy"],
                jitter=config["jitter"],
                jitter_factor=config["jitter_factor"],
                circuit_breaker=cb,
                **{k: v for k, v in config.items() if k not in self.default_config}
            )(func)
        
        # Called with or without function
        if func is None:
            return decorator
        return decorator(func)

# Create global retry manager instance
retry_manager = RetryManager()

def configure_retry_from_env() -> RetryManager:
    """
    Configure the retry manager from environment variables.
    
    Returns:
        Configured RetryManager instance
    """
    import os
    
    # Configure default retry settings
    retry_manager.set_default_config(
        max_retries=int(os.environ.get("RETRY_MAX_ATTEMPTS", "3")),
        delay=float(os.environ.get("RETRY_BASE_DELAY", "1.0")),
        max_delay=float(os.environ.get("RETRY_MAX_DELAY", "60.0")),
        strategy=getattr(RetryStrategy, os.environ.get("RETRY_STRATEGY", "EXPONENTIAL"), RetryStrategy.EXPONENTIAL),
        jitter=os.environ.get("RETRY_USE_JITTER", "true").lower() == "true",
        jitter_factor=float(os.environ.get("RETRY_JITTER_FACTOR", "0.5"))
    )
    
    # Configure special retry settings for network operations
    retry_manager.set_special_config(
        "requests|urllib|http|connect|fetch|download|scrape",
        max_retries=int(os.environ.get("NETWORK_RETRY_MAX_ATTEMPTS", "5")),
        delay=float(os.environ.get("NETWORK_RETRY_BASE_DELAY", "2.0")),
        exceptions=(
            ConnectionError,
            TimeoutError,
        )
    )
    
    # Configure circuit breakers
    retry_manager.create_circuit_breaker(
        "network",
        failure_threshold=int(os.environ.get("NETWORK_CB_FAILURE_THRESHOLD", "5")),
        recovery_timeout=int(os.environ.get("NETWORK_CB_RECOVERY_TIMEOUT", "300"))
    )
    
    retry_manager.create_circuit_breaker(
        "database",
        failure_threshold=int(os.environ.get("DB_CB_FAILURE_THRESHOLD", "3")),
        recovery_timeout=int(os.environ.get("DB_CB_RECOVERY_TIMEOUT", "60"))
    )
    
    return retry_manager
