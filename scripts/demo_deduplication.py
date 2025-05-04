#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo script for the DeduplicationProcessor 

This script demonstrates how to use the DeduplicationProcessor with different deduplication strategies:
1. Exact matching
2. Fuzzy matching 
3. Configurable rules
"""

import pandas as pd
import logging
import os
import sys

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from processing import DeduplicationProcessor

def main():
    """Main demo function"""
    # Create a sample dataset with various types of duplicates
    data = {
        'business_name': [
            'TechSolutions Inc', 
            'Tech Solutions Inc.', 
            'TECHSOLUTIONS INC',
            'ABC Consulting', 
            'ABC Consulting', 
            'XYZ Services',
            'Smith & Johnson', 
            'Smith and Johnson', 
            'Johnson & Smith LLC'
        ],
        'phone': [
            '(555) 123-4567', 
            '555-123-4567', 
            '555.123.4567',
            '(555) 987-6543', 
            '(555) 987-6543', 
            '(555) 888-9999',
            '(123) 456-7890', 
            '(123) 456-7890', 
            '(800) 555-1234'
        ],
        'email': [
            'info@techsolutions.com', 
            'info@techsolutions.com', 
            'support@techsolutions.com',
            'contact@abc-consulting.com', 
            'contact@abc-consulting.com', 
            'info@xyzservices.net',
            'hello@smithjohnson.com', 
            'contact@smithjohnson.com', 
            'info@johnsonsmith.com'
        ],
        'address': [
            '123 Tech Blvd, San Francisco, CA', 
            '123 Tech Boulevard, San Francisco, CA', 
            '123 Tech Blvd, San Francisco, California',
            '456 Consulting Ave, New York, NY', 
            '456 Consulting Avenue, New York, NY', 
            '789 Service St, Chicago, IL',
            '321 Partnership Ln, Dallas, TX', 
            '321 Partnership Lane, Dallas, TX', 
            '987 Business Rd, Houston, TX'
        ],
        'website': [
            'www.techsolutions.com', 
            'techsolutions.com', 
            'www.techsolutions.com/home',
            'www.abcconsulting.com', 
            'www.abcconsulting.com', 
            'www.xyzservices.net',
            'smithjohnson.com', 
            'www.smithjohnson.com', 
            'johnsonsmith.com'
        ],
        'year_founded': [
            2010, 
            2010, 
            2010,
            2005, 
            2005, 
            2015,
            1998, 
            1998, 
            2008
        ],
        'employee_count': [
            50, 
            None, 
            75,
            120, 
            120, 
            30,
            45, 
            None, 
            15
        ],
        'description': [
            'Technology solutions provider', 
            'Provider of technology solutions', 
            'Enterprise tech solutions',
            'Business consulting services', 
            'Business consulting services', 
            'Professional services',
            'Legal partnership', 
            'Law practice and consulting', 
            'Legal services provider'
        ]
    }

    df = pd.DataFrame(data)
    
    print("\n===== DEDUPLICATION DEMO =====\n")
    print(f"Original dataset: {len(df)} records")
    
    # Create the processor
    processor = DeduplicationProcessor(df)
    processor.save_original()  # Save state for reuse
    
    # Demo 1: Exact matching on email
    print("\n----- DEMO 1: EXACT MATCHING -----")
    print("Looking for exact matches on email addresses...")
    processor.deduplicate_exact(subset=['email'])
    print_results(processor, "Exact Email Matching")
    
    # Reset for next demo
    processor.reset()
    
    # Demo 2: Exact matching on multiple fields
    print("\n----- DEMO 2: MULTI-FIELD EXACT MATCHING -----")
    print("Looking for exact matches on phone AND address...")
    processor.deduplicate_exact(subset=['phone', 'address'])
    print_results(processor, "Exact Phone & Address Matching")
    
    # Reset for next demo
    processor.reset()
    
    # Demo 3: Fuzzy matching on business name
    print("\n----- DEMO 3: FUZZY MATCHING -----")
    print("Looking for similar business names with 80% similarity threshold...")
    try:
        processor.deduplicate_fuzzy(column='business_name', threshold=80)
        print_results(processor, "Fuzzy Business Name Matching")
    except ImportError:
        print("ERROR: fuzzywuzzy package not installed. Run: pip install fuzzywuzzy python-Levenshtein")
    
    # Reset for next demo
    processor.reset()
    
    # Demo 4: Combining exact and fuzzy matching with rules
    print("\n----- DEMO 4: CONFIGURABLE RULES -----")
    print("Using rules to find duplicates:")
    print("1. Exact email matches OR")
    print("2. Exact phone matches OR")
    print("3. Fuzzy business name matches (threshold 85) AND exact address matches")
    
    rules = [
        {'type': 'exact', 'columns': ['email'], 'operator': 'OR'},
        {'type': 'exact', 'columns': ['phone'], 'operator': 'OR'},
        {'type': 'fuzzy', 'column': 'business_name', 'threshold': 85, 'additional_exact': ['address']}
    ]
    
    try:
        processor.deduplicate(rules=rules)
        print_results(processor, "Configurable Rules Matching")
    except ImportError:
        print("ERROR: fuzzywuzzy package not installed. Run: pip install fuzzywuzzy python-Levenshtein")
    
    print("\n===== DEMO COMPLETE =====")

def print_results(processor, method_name):
    """Print the results of a deduplication operation"""
    stats = processor.get_deduplication_stats()
    print(f"\nResults from {method_name}:")
    print(f"  - Original records: {stats['original_count']}")
    print(f"  - Remaining records: {stats['current_count']}")
    print(f"  - Duplicates removed: {stats['removed_count']} ({stats['removed_percentage']}%)")
    
    if stats['removed_count'] > 0:
        print("\nRemaining records after deduplication:")
        print(processor.get_data()[['business_name', 'phone', 'email']].head())

if __name__ == "__main__":
    main()
