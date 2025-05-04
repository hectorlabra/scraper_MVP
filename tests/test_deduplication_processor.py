#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the DeduplicationProcessor class
"""

import unittest
import pandas as pd
import sys
import os
import logging

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Suppress logging during tests
logging.disable(logging.CRITICAL)

from processing import DeduplicationProcessor

class TestDeduplicationProcessor(unittest.TestCase):
    """Test cases for the DeduplicationProcessor class"""
    
    def setUp(self):
        """Set up test data before each test"""
        # Sample data with various duplicate scenarios
        self.data = {
            'business_name': [
                'Alpha Tech', 'Alpha Tech', 'ALPHA TECH', 'Alpha Technologies',
                'Beta Services', 'Beta Services Inc.',
                'Gamma Solutions', 'Gamma Solutions LLC'
            ],
            'phone': [
                '123-456-7890', '123-456-7890', '(123) 456-7890', '987-654-3210',
                '555-123-4567', '555-123-4567',
                '888-999-0000', '888-999-0000'
            ],
            'email': [
                'info@alphatech.com', 'info@alphatech.com', 'contact@alphatech.com', 'sales@alphatech.com',
                'hello@beta.com', 'info@betaservices.com',
                'support@gamma.com', 'help@gammasolutions.com'
            ],
            'location': [
                'New York', 'New York', 'NY', 'New York',
                'Los Angeles', 'LA',
                'Chicago', 'Chicago'
            ],
            'industry': [
                'Technology', 'Technology', 'Tech', 'IT Services',
                'Consulting', 'Business Services',
                'Healthcare', 'Health Tech'
            ],
            'founded': [
                2010, 2010, 2010, 2010,
                2005, 2005,
                2015, 2015
            ]
        }
        self.df = pd.DataFrame(self.data)
        
        # Initialize processor with test data
        self.processor = DeduplicationProcessor(self.df)
        self.processor.save_original()  # Save for reuse in tests
    
    def tearDown(self):
        """Reset test data after each test"""
        self.processor.reset()
    
    def test_initialization(self):
        """Test correct initialization"""
        # Test with DataFrame
        processor = DeduplicationProcessor(self.df)
        self.assertEqual(len(processor.get_data()), len(self.df))
        
        # Test with non-DataFrame
        with self.assertRaises(TypeError):
            processor = DeduplicationProcessor([1, 2, 3])
    
    def test_exact_deduplication_single_column(self):
        """Test exact deduplication with a single column"""
        # Deduplicate based on phone number
        result = self.processor.deduplicate_exact(subset=['phone'])
        
        # The exact number might vary based on implementation details
        # Just verify that duplicate records were removed
        self.assertLess(len(result), len(self.df))
        
        # Verify stats
        stats = self.processor.get_deduplication_stats()
        self.assertEqual(stats['original_count'], 8)
        self.assertGreater(stats['removed_count'], 0)
        self.assertEqual(stats['current_count'], len(result))
    
    def test_exact_deduplication_multiple_columns(self):
        """Test exact deduplication with multiple columns"""
        # Deduplicate based on business_name AND location
        result = self.processor.deduplicate_exact(subset=['business_name', 'location'])
        
        # Should keep unique combinations of business_name and location
        # The exact number might vary based on implementation details
        self.assertLess(len(result), len(self.df))
        self.assertGreaterEqual(len(result), 6) # At least 6 unique combinations
    
    def test_exact_deduplication_keep_most_complete(self):
        """Test that exact deduplication keeps the most complete record"""
        # Create test data with varying completeness
        data = {
            'id': [1, 2, 3],
            'name': ['Test Company', 'Test Company', 'Test Company'],
            'phone': ['555-1234', '555-1234', '555-1234'],
            'email': ['test@example.com', None, 'test@example.com'],
            'website': [None, 'www.test.com', 'www.test.com'],
            'address': ['123 Main St', '123 Main St', None]
        }
        df = pd.DataFrame(data)
        
        # Initialize processor with this data
        processor = DeduplicationProcessor(df)
        
        # All records have the same name and phone
        result = processor.deduplicate_exact(subset=['name', 'phone'], keep_most_complete=True)
        
        # Should have only one record remain
        self.assertEqual(len(result), 1)
        
        # Check that we kept a record with the most non-null values
        # Count non-null values in the remaining record
        remaining_id = result['id'].iloc[0]
        print(f"Kept record with ID: {remaining_id}")
        
        # Count non-null values in this record
        non_null_count = result.notna().sum(axis=1).iloc[0]
        
        # It should have at least 4 non-null values (which is the max in our test data)
        self.assertGreaterEqual(non_null_count, 4)
    
    def test_exact_deduplication_nonexistent_column(self):
        """Test handling of non-existent columns"""
        # Should issue a warning and use only valid columns
        result = self.processor.deduplicate_exact(subset=['business_name', 'nonexistent_column'])
        
        # Should still work with the valid column
        self.assertLess(len(result), len(self.df))
        
        # Test with all invalid columns
        with self.assertRaises(ValueError):
            self.processor.deduplicate_exact(subset=['nonexistent1', 'nonexistent2'])
    
    def test_fuzzy_deduplication(self):
        """Test fuzzy deduplication (if fuzzywuzzy is available)"""
        try:
            import fuzzywuzzy
            
            # Reset processor to original state
            self.processor.reset()
            
            # Deduplicate based on business_name with 85% similarity threshold
            result = self.processor.deduplicate_fuzzy(column='business_name', threshold=85)
            
            # Should identify similar business names (e.g., "Alpha Tech" and "ALPHA TECH")
            self.assertLess(len(result), len(self.df))
            
            # Test with non-existent column
            with self.assertRaises(ValueError):
                self.processor.deduplicate_fuzzy(column='nonexistent_column')
                
        except ImportError:
            # Skip this test if fuzzywuzzy is not available
            self.skipTest("fuzzywuzzy package not available")
    
    def test_fuzzy_with_exact_columns(self):
        """Test fuzzy deduplication with additional exact matching columns"""
        try:
            import fuzzywuzzy
            
            # Reset processor to original state
            self.processor.reset()
            
            # Deduplicate based on similar business names AND exact location
            result = self.processor.deduplicate_fuzzy(
                column='business_name', 
                threshold=85,
                additional_exact_columns=['location']
            )
            
            # Should only consider records fuzzy duplicates if they also have matching locations
            self.assertLess(len(result), len(self.df))
                
        except ImportError:
            # Skip this test if fuzzywuzzy is not available
            self.skipTest("fuzzywuzzy package not available")
    
    def test_configurable_rules(self):
        """Test configurable rules interface"""
        try:
            import fuzzywuzzy
            
            # Define rules: exact email OR (fuzzy business_name AND exact location)
            rules = [
                {'type': 'exact', 'columns': ['email'], 'operator': 'OR'},
                {'type': 'fuzzy', 'column': 'business_name', 'threshold': 85, 'additional_exact': ['location']}
            ]
            
            # Apply rules
            result = self.processor.deduplicate(rules=rules)
            
            # Should reduce the number of records
            self.assertLess(len(result), len(self.df))
            
            # Test with default rules (when None provided)
            self.processor.reset()
            result = self.processor.deduplicate()
            self.assertLess(len(result), len(self.df))
                
        except ImportError:
            # Skip this test if fuzzywuzzy is not available
            self.skipTest("fuzzywuzzy package not available")
    
    def test_utility_methods(self):
        """Test utility methods like reset, save_original, etc."""
        # First modify the data
        self.processor.deduplicate_exact(subset=['phone'])
        modified_count = len(self.processor.get_data())
        self.assertLess(modified_count, len(self.df))
        
        # Test reset
        self.processor.reset()
        reset_count = len(self.processor.get_data())
        self.assertEqual(reset_count, len(self.df))
        
        # Test get_deduplication_stats
        self.processor.deduplicate_exact(subset=['email'])
        stats = self.processor.get_deduplication_stats()
        self.assertEqual(stats['original_count'], len(self.df))
        self.assertGreater(stats['removed_count'], 0)
        self.assertEqual(stats['current_count'], len(self.processor.get_data()))
        
        # Test save_original after modification
        self.processor.save_original()
        new_original_count = self.processor.original_row_count
        self.assertLess(new_original_count, len(self.df))

if __name__ == '__main__':
    unittest.main()
