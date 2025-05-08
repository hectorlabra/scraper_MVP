#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Quality Monitoring for ScraperMVP

This module provides functionality to monitor and assess the quality of
scraped data by applying validation rules, statistical analysis, and 
trend monitoring to detect anomalies and data issues.

It integrates with the metrics system to track data quality metrics over time
and can trigger alerts when quality falls below defined thresholds.
"""

import pandas as pd
import numpy as np
import logging
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union, Tuple, Set
from collections import defaultdict, Counter
import jsonschema
from pathlib import Path

# Import local modules
from utils.monitoring import MetricsRegistry
from utils.notification import NotificationManager
from utils.logging_utils import setup_advanced_logger

# Configure logger
try:
    logger = setup_advanced_logger(
        name=__name__,
        console=True,
        log_level=os.environ.get("LOG_LEVEL", "INFO")
    )
except (ImportError, NameError):
    # Fall back to basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

class DataQualityConfig:
    """
    Configuration for data quality monitoring rules and thresholds.
    """
    DEFAULT_CONFIG = {
        # General thresholds
        "missing_threshold": 0.1,  # Alert if >10% of required fields are missing
        "duplicate_threshold": 0.05,  # Alert if >5% of records are duplicates
        "invalid_threshold": 0.1,  # Alert if >10% of records have invalid values
        
        # Field-specific rules
        "field_rules": {
            "business_name": {
                "required": True,
                "min_length": 2,
                "max_length": 100,
                "pattern": None  # No specific pattern required
            },
            "email": {
                "required": True,
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            },
            "phone": {
                "required": True,
                "pattern": r"^(\+\d{1,3})?\s*(\(\d{1,4}\))?\s*[\d\s-]{5,}$"
            },
            "website": {
                "required": False,
                "pattern": r"^(https?:\/\/)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$"
            },
            "address": {
                "required": False,
                "min_length": 5
            },
            "description": {
                "required": False
            }
        },
        
        # Pattern detection for suspicious data
        "pattern_detection": {
            "enabled": True,
            "suspicious_patterns": [
                r"test[0-9]*@",  # Test emails
                r"example\.com$",  # Example domain
                r"@example\.",  # Example domain
                r"@test\.",  # Test domain
                r"^[a-z]{1,3}@",  # Short/suspicious usernames
                r"12345",  # Sequential numbers
                r"^admin@",  # Admin email
                r"^info@",  # Generic info email
                r"^sales@",  # Generic sales email
            ]
        },
        
        # Anomaly detection settings
        "anomaly_detection": {
            "enabled": True,
            "std_dev_threshold": 3.0,  # Standard deviations for numeric outliers
            "categorical_frequency_threshold": 0.01  # Minimum expected frequency for categories
        },
        
        # Time-based thresholds
        "time_thresholds": {
            "min_expected_records_per_day": 10,  # Minimum expected records per day
            "max_expected_records_per_day": 10000,  # Maximum expected records per day
            "max_stale_data_days": 7  # Maximum days before data is considered stale
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize data quality configuration.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                
                # Merge user config with default config
                self._merge_configs(user_config)
                logger.info(f"Loaded data quality configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading data quality configuration: {str(e)}")
    
    def _merge_configs(self, user_config: Dict[str, Any]) -> None:
        """
        Merge user configuration with default configuration.
        
        Args:
            user_config: User-provided configuration
        """
        # Handle top-level parameters
        for key in self.config:
            if key in user_config and key != "field_rules":
                if isinstance(self.config[key], dict) and isinstance(user_config[key], dict):
                    # Recursively merge dictionaries
                    self._merge_dict(self.config[key], user_config[key])
                else:
                    self.config[key] = user_config[key]
        
        # Handle field rules
        if "field_rules" in user_config:
            for field, rules in user_config["field_rules"].items():
                if field in self.config["field_rules"]:
                    # Update existing field rules
                    self.config["field_rules"][field].update(rules)
                else:
                    # Add new field rules
                    self.config["field_rules"][field] = rules
    
    def _merge_dict(self, d1: Dict[str, Any], d2: Dict[str, Any]) -> None:
        """
        Recursively merge dictionaries.
        
        Args:
            d1: First dictionary (will be modified)
            d2: Second dictionary (values will be copied to d1)
        """
        for k, v in d2.items():
            if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
                self._merge_dict(d1[k], v)
            else:
                d1[k] = v
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the configuration.
        
        Returns:
            Data quality configuration
        """
        return self.config
    
    def get_field_rules(self) -> Dict[str, Dict[str, Any]]:
        """
        Get field-specific validation rules.
        
        Returns:
            Field validation rules
        """
        return self.config["field_rules"]
    
    def get_threshold(self, name: str) -> float:
        """
        Get a threshold value.
        
        Args:
            name: Name of the threshold
            
        Returns:
            Threshold value
        """
        return self.config.get(name, 0.0)
    
    def get_pattern_detection_config(self) -> Dict[str, Any]:
        """
        Get pattern detection configuration.
        
        Returns:
            Pattern detection configuration
        """
        return self.config["pattern_detection"]
    
    def get_anomaly_detection_config(self) -> Dict[str, Any]:
        """
        Get anomaly detection configuration.
        
        Returns:
            Anomaly detection configuration
        """
        return self.config["anomaly_detection"]
    
    def get_time_thresholds(self) -> Dict[str, Any]:
        """
        Get time-based thresholds.
        
        Returns:
            Time-based thresholds
        """
        return self.config["time_thresholds"]

class DataQualitySchema:
    """
    JSON schema for validating data structure.
    """
    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize data quality schema.
        
        Args:
            schema_path: Optional path to schema file
        """
        self.schema = None
        
        if schema_path and os.path.exists(schema_path):
            try:
                with open(schema_path, 'r') as f:
                    self.schema = json.load(f)
                logger.info(f"Loaded data quality schema from {schema_path}")
            except Exception as e:
                logger.error(f"Error loading data quality schema: {str(e)}")
    
    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate data against schema.
        
        Args:
            data: Data to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        if not self.schema:
            return True, []
        
        try:
            jsonschema.validate(instance=data, schema=self.schema)
            return True, []
        except jsonschema.exceptions.ValidationError as e:
            return False, [str(e)]
        
class DataQualityMonitor:
    """
    Monitor for assessing data quality and tracking metrics.
    """
    def __init__(
        self, 
        metrics_registry: MetricsRegistry,
        config: Optional[DataQualityConfig] = None,
        schema: Optional[DataQualitySchema] = None,
        notification_manager: Optional = None
    ):
        """
        Initialize data quality monitor.
        
        Args:
            metrics_registry: Registry for tracking metrics
            config: Optional data quality configuration
            schema: Optional data quality schema
            notification_manager: Optional notification manager
        """
        self.metrics = metrics_registry
        self.config = config or DataQualityConfig()
        self.schema = schema or DataQualitySchema()
        self.notification_manager = notification_manager
        
        # Store history of quality scores
        self.quality_history = defaultdict(list)
        
        # Initialize statistics
        self.statistics = {
            "total_records_processed": 0,
            "records_with_issues": 0,
            "fields_with_issues": defaultdict(int),
            "issue_types": defaultdict(int),
            "last_processing_time": None,
            "quality_score": 100.0
        }
        
        # Initialize issue categorization
        self.issue_categories = {
            "missing_required": "Required field is missing",
            "invalid_format": "Field format is invalid",
            "out_of_range": "Field value is out of acceptable range",
            "suspicious_pattern": "Field contains suspicious pattern",
            "duplicate_record": "Record is a duplicate",
            "schema_violation": "Record violates schema",
            "anomaly": "Statistical anomaly detected"
        }
        
        # Create metrics for data quality
        for category in self.issue_categories:
            self.metrics.create_counter(f"data_quality.issues.{category}")
        
        self.metrics.create_gauge("data_quality.score")
        self.metrics.create_gauge("data_quality.records_processed")
        self.metrics.create_gauge("data_quality.records_with_issues")
        
        logger.info("Data quality monitoring initialized")
    
    def process_dataset(self, data: pd.DataFrame, source_name: str = "unknown") -> Dict[str, Any]:
        """
        Process a dataset and assess its quality.
        
        Args:
            data: DataFrame to process
            source_name: Name of the data source
            
        Returns:
            Quality assessment results
        """
        start_time = time.time()
        
        if data.empty:
            logger.warning(f"Empty dataset received from {source_name}")
            return {
                "quality_score": 0,
                "issues": ["Empty dataset"],
                "records_processed": 0,
                "records_with_issues": 0,
                "source": source_name,
                "timestamp": datetime.now().isoformat()
            }
        
        # Initialize results
        results = {
            "issues": [],
            "records_processed": len(data),
            "records_with_issues": 0,
            "field_issues": defaultdict(int),
            "issue_types": defaultdict(int),
            "suspicious_records": [],
            "source": source_name,
            "timestamp": datetime.now().isoformat()
        }
        
        # Update statistics
        self.statistics["total_records_processed"] += len(data)
        self.statistics["last_processing_time"] = datetime.now().isoformat()
        
        # Track metrics
        self.metrics.set_gauge("data_quality.records_processed", self.statistics["total_records_processed"])
        
        # 1. Check for missing values in required fields
        missing_issues = self._check_missing_values(data)
        if missing_issues:
            results["issues"].extend(missing_issues)
        
        # 2. Validate field formats and patterns
        format_issues = self._validate_field_formats(data)
        if format_issues:
            results["issues"].extend(format_issues)
        
        # 3. Check for duplicates
        duplicate_issues = self._check_duplicates(data)
        if duplicate_issues:
            results["issues"].extend(duplicate_issues)
        
        # 4. Check for suspicious patterns
        suspicious_issues, suspicious_indices = self._check_suspicious_patterns(data)
        if suspicious_issues:
            results["issues"].extend(suspicious_issues)
            
            # Add suspicious records
            for idx in suspicious_indices:
                if idx < len(data):
                    results["suspicious_records"].append(data.iloc[idx].to_dict())
        
        # 5. Detect statistical anomalies
        anomaly_issues = self._detect_anomalies(data)
        if anomaly_issues:
            results["issues"].extend(anomaly_issues)
        
        # Calculate field-specific issue counts
        for issue in results["issues"]:
            if "field" in issue:
                results["field_issues"][issue["field"]] += 1
            
            results["issue_types"][issue["type"]] += 1
            
            # Update global statistics
            self.statistics["fields_with_issues"][issue.get("field", "unknown")] += 1
            self.statistics["issue_types"][issue["type"]] += 1
        
        # Count records with issues
        records_with_issues = set()
        for issue in results["issues"]:
            if "record_index" in issue:
                records_with_issues.add(issue["record_index"])
        
        results["records_with_issues"] = len(records_with_issues)
        self.statistics["records_with_issues"] += len(records_with_issues)
        
        # Update metrics
        self.metrics.set_gauge("data_quality.records_with_issues", self.statistics["records_with_issues"])
        
        for issue_type, count in results["issue_types"].items():
            self.metrics.inc_counter(f"data_quality.issues.{issue_type}", count)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(results)
        results["quality_score"] = quality_score
        
        # Update metrics
        self.metrics.set_gauge("data_quality.score", quality_score)
        
        # Store in history
        self.quality_history[source_name].append({
            "timestamp": datetime.now().isoformat(),
            "quality_score": quality_score,
            "records_processed": len(data),
            "records_with_issues": results["records_with_issues"]
        })
        
        # Trim history to last 100 entries per source
        if len(self.quality_history[source_name]) > 100:
            self.quality_history[source_name] = self.quality_history[source_name][-100:]
        
        # Check if quality score is below threshold and send notification if needed
        if quality_score < 70 and self.notification_manager:
            self._send_quality_alert(results, source_name)
        
        # Log processing time
        processing_time = time.time() - start_time
        logger.info(f"Data quality assessment completed for {source_name} in {processing_time:.2f}s with score {quality_score:.1f}")
        
        return results
    
    def _check_missing_values(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Check for missing values in required fields.
        
        Args:
            data: DataFrame to check
            
        Returns:
            List of issues
        """
        issues = []
        field_rules = self.config.get_field_rules()
        missing_threshold = self.config.get_threshold("missing_threshold")
        
        for field, rules in field_rules.items():
            if rules.get("required", False) and field in data.columns:
                missing_count = data[field].isna().sum()
                if missing_count > 0:
                    missing_pct = missing_count / len(data)
                    
                    # Add overall issue if above threshold
                    if missing_pct > missing_threshold:
                        issues.append({
                            "type": "missing_required",
                            "field": field,
                            "description": f"{field} missing in {missing_count} records ({missing_pct:.1%})",
                            "count": missing_count,
                            "percentage": missing_pct
                        })
                    
                    # Add record-specific issues
                    for idx in data[data[field].isna()].index:
                        issues.append({
                            "type": "missing_required",
                            "field": field,
                            "record_index": idx,
                            "description": f"Required field {field} is missing"
                        })
        
        return issues
    
    def _validate_field_formats(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Validate field formats and patterns.
        
        Args:
            data: DataFrame to validate
            
        Returns:
            List of issues
        """
        issues = []
        field_rules = self.config.get_field_rules()
        invalid_threshold = self.config.get_threshold("invalid_threshold")
        
        for field, rules in field_rules.items():
            if field not in data.columns:
                continue
            
            invalid_indices = []
            
            # Check pattern if specified
            if "pattern" in rules and rules["pattern"]:
                pattern = re.compile(rules["pattern"])
                
                # Skip NaN values
                mask = ~data[field].isna()
                if mask.sum() > 0:
                    invalid_mask = mask & ~data.loc[mask, field].astype(str).str.match(pattern)
                    if invalid_mask.any():
                        invalid_indices.extend(data[invalid_mask].index.tolist())
            
            # Check min_length if specified
            if "min_length" in rules:
                min_length = rules["min_length"]
                
                # Skip NaN values
                mask = ~data[field].isna()
                if mask.sum() > 0:
                    invalid_mask = mask & (data.loc[mask, field].astype(str).str.len() < min_length)
                    if invalid_mask.any():
                        invalid_indices.extend(data[invalid_mask].index.tolist())
            
            # Check max_length if specified
            if "max_length" in rules:
                max_length = rules["max_length"]
                
                # Skip NaN values
                mask = ~data[field].isna()
                if mask.sum() > 0:
                    invalid_mask = mask & (data.loc[mask, field].astype(str).str.len() > max_length)
                    if invalid_mask.any():
                        invalid_indices.extend(data[invalid_mask].index.tolist())
            
            # Deduplicate indices
            invalid_indices = list(set(invalid_indices))
            
            # Add issues
            invalid_count = len(invalid_indices)
            if invalid_count > 0:
                invalid_pct = invalid_count / len(data)
                
                # Add overall issue if above threshold
                if invalid_pct > invalid_threshold:
                    issues.append({
                        "type": "invalid_format",
                        "field": field,
                        "description": f"{field} has invalid format in {invalid_count} records ({invalid_pct:.1%})",
                        "count": invalid_count,
                        "percentage": invalid_pct
                    })
                
                # Add record-specific issues
                for idx in invalid_indices:
                    issues.append({
                        "type": "invalid_format",
                        "field": field,
                        "record_index": idx,
                        "description": f"Field {field} has invalid format: '{data.loc[idx, field]}'"
                    })
        
        return issues
    
    def _check_duplicates(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Check for duplicate records.
        
        Args:
            data: DataFrame to check
            
        Returns:
            List of issues
        """
        issues = []
        duplicate_threshold = self.config.get_threshold("duplicate_threshold")
        
        # Find duplicate records based on key fields
        # Use subset of important fields to determine duplicates, not all fields
        key_fields = []
        field_rules = self.config.get_field_rules()
        
        for field in data.columns:
            if field in field_rules and field_rules[field].get("required", False):
                key_fields.append(field)
        
        # Fallback if no required fields defined
        if not key_fields:
            key_fields = data.columns.tolist()
        
        # Find duplicates
        if key_fields:
            # Get duplicate indices
            dup_indices = data.duplicated(subset=key_fields, keep='first')
            duplicate_count = dup_indices.sum()
            
            if duplicate_count > 0:
                duplicate_pct = duplicate_count / len(data)
                
                # Add overall issue if above threshold
                if duplicate_pct > duplicate_threshold:
                    issues.append({
                        "type": "duplicate_record",
                        "description": f"Found {duplicate_count} duplicate records ({duplicate_pct:.1%})",
                        "count": duplicate_count,
                        "percentage": duplicate_pct
                    })
                
                # Add record-specific issues
                for idx in data[dup_indices].index:
                    issues.append({
                        "type": "duplicate_record",
                        "record_index": idx,
                        "description": f"Record is a duplicate based on key fields: {', '.join(key_fields)}"
                    })
        
        return issues
    
    def _check_suspicious_patterns(self, data: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[int]]:
        """
        Check for suspicious patterns in data.
        
        Args:
            data: DataFrame to check
            
        Returns:
            Tuple of (issues, suspicious_indices)
        """
        issues = []
        suspicious_indices = set()
        
        pattern_config = self.config.get_pattern_detection_config()
        if not pattern_config.get("enabled", True):
            return [], []
        
        suspicious_patterns = pattern_config.get("suspicious_patterns", [])
        field_rules = self.config.get_field_rules()
        
        # Check each field with patterns
        for field, rules in field_rules.items():
            if field not in data.columns:
                continue
            
            # Skip fields that don't usually have suspicious patterns
            if field in ["description", "address"]:
                continue
            
            suspicious_count = 0
            
            # Check for suspicious patterns
            for pattern_str in suspicious_patterns:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                
                # Skip NaN values
                mask = ~data[field].isna()
                if mask.sum() > 0:
                    suspicious_mask = mask & data.loc[mask, field].astype(str).str.contains(pattern, regex=True, na=False)
                    
                    if suspicious_mask.any():
                        suspicious_count += suspicious_mask.sum()
                        pattern_indices = data[suspicious_mask].index.tolist()
                        suspicious_indices.update(pattern_indices)
                        
                        # Add record-specific issues
                        for idx in pattern_indices:
                            issues.append({
                                "type": "suspicious_pattern",
                                "field": field,
                                "record_index": idx,
                                "pattern": pattern_str,
                                "description": f"Field {field} contains suspicious pattern: '{pattern_str}'"
                            })
            
            # Add field-level issue if there are suspicious patterns
            if suspicious_count > 0:
                suspicious_pct = suspicious_count / len(data)
                issues.append({
                    "type": "suspicious_pattern",
                    "field": field,
                    "description": f"{field} contains suspicious patterns in {suspicious_count} records ({suspicious_pct:.1%})",
                    "count": suspicious_count,
                    "percentage": suspicious_pct
                })
        
        return issues, list(suspicious_indices)
    
    def _detect_anomalies(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect statistical anomalies in data.
        
        Args:
            data: DataFrame to check
            
        Returns:
            List of issues
        """
        issues = []
        
        anomaly_config = self.config.get_anomaly_detection_config()
        if not anomaly_config.get("enabled", True):
            return []
        
        std_dev_threshold = anomaly_config.get("std_dev_threshold", 3.0)
        cat_freq_threshold = anomaly_config.get("categorical_frequency_threshold", 0.01)
        
        # Check numeric fields for outliers
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if data[col].isna().all():
                continue
            
            mean = data[col].mean()
            std = data[col].std()
            
            if std == 0:
                continue  # Skip if no variation
            
            # Find outliers (values more than N std devs from mean)
            lower_bound = mean - std_dev_threshold * std
            upper_bound = mean + std_dev_threshold * std
            
            outliers = data[(data[col] < lower_bound) | (data[col] > upper_bound)]
            
            if not outliers.empty:
                outlier_count = len(outliers)
                outlier_pct = outlier_count / len(data)
                
                # Add overall issue
                issues.append({
                    "type": "anomaly",
                    "field": col,
                    "description": f"{col} has {outlier_count} outliers ({outlier_pct:.1%})",
                    "count": outlier_count,
                    "percentage": outlier_pct
                })
                
                # Add record-specific issues
                for idx in outliers.index:
                    value = data.loc[idx, col]
                    issues.append({
                        "type": "anomaly",
                        "field": col,
                        "record_index": idx,
                        "description": f"Field {col} has outlier value: {value} (outside range {lower_bound:.2f}-{upper_bound:.2f})",
                        "value": float(value)  # Convert to float for serialization
                    })
        
        # Check categorical fields for unusual frequencies
        for col in data.select_dtypes(include=['object']).columns:
            if data[col].isna().all():
                continue
            
            value_counts = data[col].value_counts(normalize=True)
            rare_values = value_counts[value_counts < cat_freq_threshold]
            
            if not rare_values.empty:
                rare_count = data[data[col].isin(rare_values.index)].shape[0]
                rare_pct = rare_count / len(data)
                
                if rare_count > 0:
                    # Add overall issue
                    issues.append({
                        "type": "anomaly",
                        "field": col,
                        "description": f"{col} has {rare_count} rare category values ({rare_pct:.1%})",
                        "count": rare_count,
                        "percentage": rare_pct
                    })
        
        return issues
    
    def _calculate_quality_score(self, results: Dict[str, Any]) -> float:
        """
        Calculate overall data quality score.
        
        Args:
            results: Quality assessment results
            
        Returns:
            Quality score (0-100)
        """
        # Base score
        score = 100.0
        
        if results["records_processed"] == 0:
            return 0.0  # No records
        
        # Decrease score based on issue percentages
        issue_weights = {
            "missing_required": 10.0,  # Higher impact
            "invalid_format": 8.0,
            "duplicate_record": 5.0,
            "suspicious_pattern": 4.0,
            "anomaly": 2.0  # Lower impact
        }
        
        for issue_type, count in results["issue_types"].items():
            if issue_type in issue_weights:
                issue_pct = count / results["records_processed"]
                score -= issue_pct * issue_weights[issue_type] * 100
        
        # Also penalize for high percentage of records with issues
        records_with_issues_pct = results["records_with_issues"] / results["records_processed"]
        score -= records_with_issues_pct * 20  # Up to 20 points off for 100% records with issues
        
        # Ensure score is within range 0-100
        score = max(0.0, min(100.0, score))
        
        return score
    
    def _send_quality_alert(self, results: Dict[str, Any], source_name: str) -> None:
        """
        Send alert for poor data quality.
        
        Args:
            results: Quality assessment results
            source_name: Name of the data source
        """
        if not self.notification_manager:
            return
        
        # Format message
        title = f"Data Quality Alert: {source_name}"
        
        message = f"Data quality score: {results['quality_score']:.1f}/100\n"
        message += f"Records processed: {results['records_processed']}\n"
        message += f"Records with issues: {results['records_with_issues']} ({results['records_with_issues']/results['records_processed']:.1%})\n\n"
        
        message += "Key issues:\n"
        for issue_type, count in results["issue_types"].items():
            if count > 0:
                message += f"- {self.issue_categories.get(issue_type, issue_type)}: {count} occurrences\n"
        
        # Send notification
        self.notification_manager.send_notification(
            title=title,
            message=message,
            level="warning",
            category="data_quality"
        )
        
        logger.warning(f"Data quality alert sent for {source_name}: score={results['quality_score']:.1f}")
    
    def get_quality_history(self, source_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get history of quality scores.
        
        Args:
            source_name: Optional name of data source to filter by
            
        Returns:
            Quality score history
        """
        if source_name:
            return {source_name: self.quality_history.get(source_name, [])}
        
        return dict(self.quality_history)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get data quality statistics.
        
        Returns:
            Data quality statistics
        """
        return self.statistics
    
    def generate_quality_report(self, source_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate data quality report.
        
        Args:
            source_name: Optional name of data source to filter by
            
        Returns:
            Data quality report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_records_processed": self.statistics["total_records_processed"],
            "total_records_with_issues": self.statistics["records_with_issues"],
            "overall_quality_score": self.statistics.get("quality_score", 100.0),
            "issue_summary": dict(self.statistics["issue_types"]),
            "field_issues": dict(self.statistics["fields_with_issues"]),
            "history": {}
        }
        
        # Add history
        if source_name:
            report["history"][source_name] = self.quality_history.get(source_name, [])
        else:
            report["history"] = self.get_quality_history()
        
        # Calculate trends
        for src, history in report["history"].items():
            if len(history) >= 2:
                oldest = history[0]["quality_score"]
                newest = history[-1]["quality_score"]
                report["history"][src + "_trend"] = newest - oldest
        
        return report
    
    def export_report(self, directory: str, source_name: Optional[str] = None) -> str:
        """
        Export data quality report to file.
        
        Args:
            directory: Directory to save report
            source_name: Optional name of data source to filter by
            
        Returns:
            Path to exported report
        """
        # Create directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Generate report
        report = self.generate_quality_report(source_name)
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if source_name:
            filename = f"data_quality_{source_name}_{timestamp}.json"
        else:
            filename = f"data_quality_report_{timestamp}.json"
        
        filepath = os.path.join(directory, filename)
        
        # Write report to file
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Data quality report exported to {filepath}")
        
        return filepath

# Helper functions for integration with data processors

def validate_dataset(
    data: pd.DataFrame,
    metrics_registry: MetricsRegistry,
    source_name: str = "unknown",
    config_path: Optional[str] = None,
    notification_manager = None
) -> Dict[str, Any]:
    """
    Validate a dataset and assess its quality.
    
    Args:
        data: DataFrame to validate
        metrics_registry: Registry for tracking metrics
        source_name: Name of the data source
        config_path: Optional path to configuration file
        notification_manager: Optional notification manager
        
    Returns:
        Quality assessment results
    """
    config = DataQualityConfig(config_path)
    monitor = DataQualityMonitor(metrics_registry, config, notification_manager=notification_manager)
    
    return monitor.process_dataset(data, source_name)

def create_data_quality_monitor(
    metrics_registry: MetricsRegistry,
    config_path: Optional[str] = None,
    schema_path: Optional[str] = None,
    notification_manager = None
) -> DataQualityMonitor:
    """
    Create a data quality monitor.
    
    Args:
        metrics_registry: Registry for tracking metrics
        config_path: Optional path to configuration file
        schema_path: Optional path to schema file
        notification_manager: Optional notification manager
        
    Returns:
        Data quality monitor
    """
    config = DataQualityConfig(config_path)
    schema = DataQualitySchema(schema_path)
    
    return DataQualityMonitor(metrics_registry, config, schema, notification_manager)

def main():
    """
    Main function for testing data quality monitoring.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Data Quality Monitoring for ScraperMVP")
    parser.add_argument("--data-file", help="Path to data file (CSV)")
    parser.add_argument("--config", help="Path to configuration file (JSON)")
    parser.add_argument("--schema", help="Path to schema file (JSON)")
    parser.add_argument("--output-dir", help="Directory for output reports", default="reports")
    parser.add_argument("--source", help="Name of data source", default="test")
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Create metrics registry
    metrics_registry = MetricsRegistry()
    
    if args.data_file:
        # Load data
        try:
            data = pd.read_csv(args.data_file)
            logger.info(f"Loaded {len(data)} records from {args.data_file}")
            
            # Create monitor
            monitor = create_data_quality_monitor(
                metrics_registry,
                config_path=args.config,
                schema_path=args.schema
            )
            
            # Process dataset
            results = monitor.process_dataset(data, source_name=args.source)
            
            # Export report
            report_path = monitor.export_report(args.output_dir, args.source)
            
            print(f"Data quality score: {results['quality_score']:.1f}/100")
            print(f"Records processed: {results['records_processed']}")
            print(f"Records with issues: {results['records_with_issues']}")
            print(f"Report exported to: {report_path}")
            
        except Exception as e:
            logger.error(f"Error processing data file: {str(e)}")
    else:
        logger.error("No data file specified")

if __name__ == "__main__":
    main()
