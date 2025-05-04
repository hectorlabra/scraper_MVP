#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the ValidationProcessor class
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

from processing import ValidationProcessor

class TestValidationProcessor(unittest.TestCase):
    """Test cases for the ValidationProcessor class"""
    
    def setUp(self):
        """Set up test data before each test"""
        # Sample data with various email and phone formats
        self.data = {
            'business_name': [
                'Alpha Tech', 'Beta Services', 'Gamma Solutions', 
                'Delta Corp', 'Epsilon Ltd', 'Zeta Inc', 'Eta Group', 'Theta Systems'
            ],
            'phone': [
                '+52 55 1234 5678',       # Mexico
                '+55 11 91234-5678',      # Brazil
                '+54 9 11 1234-5678',     # Argentina
                '(123) 456-7890',         # Generic/US format
                '555.123.4567',           # Unusual format
                '56 9 8765 4321',         # Chile without +
                '123456789',              # Invalid - too short
                'abcdefghij'              # Invalid - not a number
            ],
            'email': [
                'info@alphatech.com',         # Standard
                'user.name+tag@example.com',  # Valid with special chars
                'email@subdomain.example.co', # With subdomain
                'email@123.123.123.123',      # IP address domain
                'plainaddress',               # Invalid - no @ symbol
                'email@example',              # Invalid - no TLD
                '@example.com',               # Invalid - no username
                'email@example..com'          # Invalid - double dot
            ],
            'location': [
                'Mexico City, Mexico', 
                'São Paulo, Brazil', 
                'Buenos Aires, Argentina', 
                'New York, USA',
                'Toronto, Canada',
                'Santiago, Chile',
                'Lima, Peru',
                'Bogotá, Colombia'
            ]
        }
        self.df = pd.DataFrame(self.data)
        self.processor = ValidationProcessor(self.df)

    def test_validate_email(self):
        """Test email validation functionality"""
        # Valid emails
        self.assertTrue(self.processor.validate_email('info@alphatech.com'))
        self.assertTrue(self.processor.validate_email('user.name+tag@example.com'))
        self.assertTrue(self.processor.validate_email('email@subdomain.example.co'))
        self.assertTrue(self.processor.validate_email('email@123.123.123.123'))
        
        # Invalid emails
        self.assertFalse(self.processor.validate_email('plainaddress'))
        self.assertFalse(self.processor.validate_email('email@example'))
        self.assertFalse(self.processor.validate_email('@example.com'))
        self.assertFalse(self.processor.validate_email('email@example..com'))
        self.assertFalse(self.processor.validate_email(''))
        self.assertFalse(self.processor.validate_email(None))

    def test_format_email(self):
        """Test email formatting functionality"""
        self.assertEqual(self.processor.format_email(' Info@AlphaTech.COM '), 'info@alphatech.com')
        self.assertEqual(self.processor.format_email('USER.NAME@EXAMPLE.COM'), 'user.name@example.com')
        self.assertIsNone(self.processor.format_email('invalid-email'))
        self.assertIsNone(self.processor.format_email(''))
        self.assertIsNone(self.processor.format_email(None))

    def test_validate_phone_number(self):
        """Test phone number validation functionality"""
        # Valid phone numbers for specific countries
        self.assertTrue(self.processor.validate_phone_number('+52 55 1234 5678', 'MX'))      # Mexico
        self.assertTrue(self.processor.validate_phone_number('+55 11 91234-5678', 'BR'))     # Brazil
        self.assertTrue(self.processor.validate_phone_number('+54 9 11 1234-5678', 'AR'))    # Argentina
        self.assertTrue(self.processor.validate_phone_number('+56 9 8765 4321', 'CL'))       # Chile
        
        # Test with automatic country detection
        self.assertTrue(self.processor.validate_phone_number('+52 55 1234 5678'))           # Mexico
        self.assertTrue(self.processor.validate_phone_number('+55 11 91234-5678'))          # Brazil
        
        # Invalid phone numbers
        self.assertFalse(self.processor.validate_phone_number('123456789'))                 # Too short
        self.assertFalse(self.processor.validate_phone_number('abcdefghij'))                # Not a number
        self.assertFalse(self.processor.validate_phone_number(''))                          # Empty
        self.assertFalse(self.processor.validate_phone_number(None))                        # None
        
        # Valid but for wrong country
        self.assertFalse(self.processor.validate_phone_number('+55 11 91234-5678', 'AR'))   # Brazil format for Argentina

    def test_format_phone_number(self):
        """Test phone number formatting functionality"""
        # Format to standard format for specific countries
        self.assertEqual(self.processor.format_phone_number('5215512345678', 'MX'), '+52 55 1234 5678')      # Mexico
        self.assertEqual(self.processor.format_phone_number('+55 11 91234-5678', 'BR'), '+55 11 91234-5678') # Brazil, already formatted
        self.assertEqual(self.processor.format_phone_number('5491112345678', 'AR'), '+54 9 11 1234-5678')    # Argentina
        
        # Test wrong country code detection and formatting
        self.assertEqual(self.processor.format_phone_number('+1 123-456-7890'), '+1 123-456-7890')  # US/Canada
        
        # Invalid phone numbers should return None
        self.assertIsNone(self.processor.format_phone_number('123'))                 # Too short
        self.assertIsNone(self.processor.format_phone_number('abcdefghij'))          # Not a number
        self.assertIsNone(self.processor.format_phone_number(''))                    # Empty
        self.assertIsNone(self.processor.format_phone_number(None))                  # None

    def test_calculate_data_quality_score(self):
        """Test data quality scoring functionality"""
        # Create sample records with different levels of completeness
        complete_record = {
            'business_name': 'Alpha Tech',
            'phone': '+52 55 1234 5678',
            'email': 'info@alphatech.com',
            'location': 'Mexico City, Mexico',
            'industry': 'Technology',
            'website': 'https://alphatech.com'
        }
        
        partial_record = {
            'business_name': 'Beta Services',
            'phone': '+55 11 91234-5678',
            'email': None,
            'location': 'São Paulo, Brazil',
            'industry': None,
            'website': None
        }
        
        minimal_record = {
            'business_name': 'Gamma Solutions',
            'phone': None,
            'email': None,
            'location': None,
            'industry': None,
            'website': None
        }
        
        # Test scores with default weights
        self.assertEqual(self.processor.calculate_data_quality_score(complete_record), 100.0)
        self.assertLess(self.processor.calculate_data_quality_score(partial_record), 100.0)
        self.assertLess(self.processor.calculate_data_quality_score(minimal_record), 
                        self.processor.calculate_data_quality_score(partial_record))
        
        # Test with custom weights
        weights = {
            'business_name': 20,
            'phone': 30,
            'email': 30,
            'location': 10,
            'industry': 5,
            'website': 5
        }
        
        score = self.processor.calculate_data_quality_score(partial_record, weights)
        expected_score = (20 + 30 + 0 + 10 + 0 + 0) / (20 + 30 + 30 + 10 + 5 + 5) * 100
        self.assertAlmostEqual(score, expected_score, places=2)

    def test_flag_suspicious_data(self):
        """Test suspicious data flagging functionality"""
        # Create test cases
        valid_record = {
            'business_name': 'Alpha Tech',
            'phone': '+52 55 1234 5678',
            'email': 'info@alphatech.com'
        }
        
        suspicious_email = {
            'business_name': 'Test Company',
            'phone': '+55 11 91234-5678',
            'email': 'test@test.com'  # Generic/suspicious
        }
        
        suspicious_phone = {
            'business_name': 'Dummy Corp',
            'phone': '1234567890',  # Sequential/simple
            'email': 'info@example.com'
        }
        
        # Test flagging
        valid_flags = self.processor.flag_suspicious_data(valid_record)
        self.assertEqual(len(valid_flags), 0)  # No flags for valid record
        
        suspicious_email_flags = self.processor.flag_suspicious_data(suspicious_email)
        self.assertGreater(len(suspicious_email_flags), 0)
        self.assertIn('email', suspicious_email_flags)
        
        suspicious_phone_flags = self.processor.flag_suspicious_data(suspicious_phone)
        self.assertGreater(len(suspicious_phone_flags), 0)
        self.assertIn('phone', suspicious_phone_flags)

    def test_validate_record(self):
        """Test the complete validation pipeline"""
        # Create test cases
        valid_record = {
            'business_name': 'Alpha Tech',
            'phone': '+52 55 1234 5678',
            'email': 'info@alphatech.com',
            'location': 'Mexico City, Mexico'
        }
        
        invalid_record = {
            'business_name': 'Test Company',
            'phone': 'abcdefghij',  # Invalid
            'email': 'notanemail',  # Invalid
            'location': ''
        }
        
        # Test full validation
        valid_result = self.processor.validate_record(valid_record)
        self.assertTrue(valid_result['is_valid'])
        self.assertEqual(valid_result['score'], 100.0)
        
        invalid_result = self.processor.validate_record(invalid_record)
        self.assertFalse(invalid_result['is_valid'])
        self.assertLess(invalid_result['score'], 100.0)
        self.assertGreater(len(invalid_result['flags']), 0)
        # Check for individual flags in invalid record
        invalid_fields = [key for key in invalid_result['flags'].keys()]
        self.assertIn('phone', invalid_fields)

    def test_process_dataframe(self):
        """Test processing an entire DataFrame"""
        # Process the sample DataFrame
        result_df = self.processor.process()
        
        # Check that the result has the expected columns
        self.assertIn('validation_score', result_df.columns)
        self.assertIn('validation_flags', result_df.columns)
        self.assertIn('is_valid', result_df.columns)
        
        # Check that validation was applied correctly
        self.assertEqual(len(result_df), len(self.df))
        
        # Check email validation - we know some are invalid in our test data
        valid_email_count = sum(result_df['email_valid'])
        self.assertLess(valid_email_count, len(result_df))
        self.assertGreater(valid_email_count, 0)
        
        # Check phone validation - we know some are invalid in our test data
        valid_phone_count = sum(result_df['phone_valid'])
        self.assertLess(valid_phone_count, len(result_df))
        self.assertGreater(valid_phone_count, 0)

if __name__ == '__main__':
    unittest.main()
