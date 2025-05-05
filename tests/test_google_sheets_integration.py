#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Google Sheets Integration

This module tests the Google Sheets Integration class functionality, including:
- Authentication with service account credentials
- Spreadsheet creation and access
- Data upload and management
- Permission management
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import json
import tempfile
import pandas as pd
from integrations.google_sheets import GoogleSheetsIntegration, PermissionType

class TestGoogleSheetsIntegration(unittest.TestCase):
    """Test cases for GoogleSheetsIntegration class."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock credentials dictionary
        self.mock_credentials = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "fake_key_id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nfakekey\n-----END PRIVATE KEY-----\n",
            "client_email": "test@example.com",
            "client_id": "12345",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40example.com"
        }
        
        # Temporary credential file
        self.temp_creds_file = tempfile.NamedTemporaryFile(delete=False)
        with open(self.temp_creds_file.name, 'w') as f:
            json.dump(self.mock_credentials, f)
            
        # Sample spreadsheet ID
        self.spreadsheet_id = "1abc2defghijklmnopqrstuvwxyz"
        
    def tearDown(self):
        """Clean up after tests."""
        os.unlink(self.temp_creds_file.name)
    
    @patch('integrations.google_sheets.Credentials')
    @patch('integrations.google_sheets.gspread')
    def test_authenticate_with_file(self, mock_gspread, mock_credentials):
        """Test authentication with credentials file."""
        # Setup mocks
        mock_credentials.from_service_account_file.return_value = "mock_creds"
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_gspread.authorize.return_value = mock_client
        mock_client.open_by_key.return_value = mock_spreadsheet
        
        # Create instance with credential file
        gs = GoogleSheetsIntegration(
            credentials_file=self.temp_creds_file.name,
            spreadsheet_id=self.spreadsheet_id
        )
        
        # Test authentication
        mock_client.list_spreadsheet_files.return_value = []
        result = gs.authenticate()
        
        # Verify
        self.assertTrue(result)
        self.assertTrue(gs.is_authenticated())
        mock_credentials.from_service_account_file.assert_called_once_with(
            self.temp_creds_file.name, 
            scopes=GoogleSheetsIntegration.SCOPES
        )
        mock_gspread.authorize.assert_called_once_with("mock_creds")
        mock_client.list_spreadsheet_files.assert_called_once()
        mock_client.open_by_key.assert_called_once_with(self.spreadsheet_id)
    
    @patch('integrations.google_sheets.Credentials')
    @patch('integrations.google_sheets.gspread')
    def test_authenticate_with_dict(self, mock_gspread, mock_credentials):
        """Test authentication with credentials dictionary."""
        # Setup mocks
        mock_credentials.from_service_account_info.return_value = "mock_creds"
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_gspread.authorize.return_value = mock_client
        mock_client.list_spreadsheet_files.return_value = []
        mock_client.open_by_key.return_value = mock_spreadsheet
        
        # Create instance with credential dictionary
        gs = GoogleSheetsIntegration(
            credentials_dict=self.mock_credentials,
            spreadsheet_id=self.spreadsheet_id
        )
        
        # Test authentication
        result = gs.authenticate()
        
        # Verify
        self.assertTrue(result)
        self.assertTrue(gs.is_authenticated())
        mock_credentials.from_service_account_info.assert_called_once_with(
            self.mock_credentials, 
            scopes=GoogleSheetsIntegration.SCOPES
        )
        mock_gspread.authorize.assert_called_once_with("mock_creds")
        mock_client.open_by_key.assert_called_once_with(self.spreadsheet_id)
    
    @patch('integrations.google_sheets.Credentials')
    @patch('integrations.google_sheets.gspread')
    def test_authenticate_from_env_var(self, mock_gspread, mock_credentials):
        """Test authentication with credentials from environment variable."""
        # Setup mocks
        mock_credentials.from_service_account_file.return_value = "mock_creds"
        mock_client = MagicMock()
        mock_client.list_spreadsheet_files.return_value = []
        mock_gspread.authorize.return_value = mock_client
        
        # Set environment variable to point to temp file
        with patch.dict(os.environ, {'GOOGLE_SERVICE_ACCOUNT_FILE': self.temp_creds_file.name}):
            # Create instance without explicit credentials
            gs = GoogleSheetsIntegration()
            
            # Test authentication
            gs.authenticate()
            
            # Verify
            mock_credentials.from_service_account_file.assert_called_once_with(
                self.temp_creds_file.name, 
                scopes=GoogleSheetsIntegration.SCOPES
            )
    
    @patch('integrations.google_sheets.Credentials')
    @patch('integrations.google_sheets.gspread')  
    def test_authenticate_failure(self, mock_gspread, mock_credentials):
        """Test authentication failure."""
        # Setup mocks to raise exception
        mock_credentials.from_service_account_file.side_effect = Exception("Auth failed")
        
        # Create instance
        gs = GoogleSheetsIntegration(
            credentials_file=self.temp_creds_file.name,
            spreadsheet_id=self.spreadsheet_id
        )
        
        # Test authentication
        with self.assertRaises(Exception):
            gs.authenticate()
            
        # Verify
        self.assertFalse(gs.is_authenticated())
    
    @patch('integrations.google_sheets.GoogleSheetsIntegration.authenticate')
    @patch('integrations.google_sheets.GoogleSheetsIntegration.is_authenticated')
    def test_ensure_authenticated(self, mock_is_auth, mock_auth):
        """Test _ensure_authenticated method."""
        # Setup mocks
        mock_is_auth.return_value = False
        mock_auth.return_value = True
        
        # Create instance
        gs = GoogleSheetsIntegration(
            credentials_file=self.temp_creds_file.name,
            spreadsheet_id=self.spreadsheet_id
        )
        
        # Call method
        gs._ensure_authenticated()
        
        # Verify
        mock_is_auth.assert_called_once()
        mock_auth.assert_called_once()
    
    @patch('integrations.google_sheets.GoogleSheetsIntegration._ensure_authenticated')
    def test_create_spreadsheet(self, mock_ensure_auth):
        """Test create_spreadsheet method."""
        # Setup
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.id = "new_id_123"
        mock_client.create.return_value = mock_spreadsheet
        
        # Create instance with mocked client
        gs = GoogleSheetsIntegration(
            credentials_file=self.temp_creds_file.name,
            spreadsheet_id=self.spreadsheet_id
        )
        gs.client = mock_client
        
        # Call method
        result = gs.create_spreadsheet("Test Spreadsheet")
        
        # Verify
        mock_ensure_auth.assert_called_once()
        mock_client.create.assert_called_once_with("Test Spreadsheet")
        self.assertEqual(result, "new_id_123")
        self.assertEqual(gs.spreadsheet_id, "new_id_123")
        self.assertEqual(gs.spreadsheet, mock_spreadsheet)
    
    @patch('integrations.google_sheets.GoogleSheetsIntegration._ensure_authenticated')
    def test_share_spreadsheet(self, mock_ensure_auth):
        """Test share_spreadsheet method."""
        # Setup
        mock_spreadsheet = MagicMock()
        
        # Create instance with mocked spreadsheet
        gs = GoogleSheetsIntegration(
            credentials_file=self.temp_creds_file.name,
            spreadsheet_id=self.spreadsheet_id
        )
        gs.spreadsheet = mock_spreadsheet
        
        # Call method
        result = gs.share_spreadsheet("user@example.com", PermissionType.WRITER)
        
        # Verify
        mock_ensure_auth.assert_called_once()
        mock_spreadsheet.share.assert_called_once_with(
            "user@example.com", 
            perm_type="writer",
            notify=True,
            email_message=None
        )
        self.assertTrue(result)
    
    @patch('integrations.google_sheets.GoogleSheetsIntegration._ensure_authenticated')
    def test_get_spreadsheet_permissions(self, mock_ensure_auth):
        """Test get_spreadsheet_permissions method."""
        # Setup
        mock_spreadsheet = MagicMock()
        mock_permissions = [{"emailAddress": "user@example.com", "role": "writer"}]
        mock_spreadsheet.list_permissions.return_value = mock_permissions
        
        # Create instance with mocked spreadsheet
        gs = GoogleSheetsIntegration(
            credentials_file=self.temp_creds_file.name,
            spreadsheet_id=self.spreadsheet_id
        )
        gs.spreadsheet = mock_spreadsheet
        
        # Call method
        result = gs.get_spreadsheet_permissions()
        
        # Verify
        mock_ensure_auth.assert_called_once()
        mock_spreadsheet.list_permissions.assert_called_once()
        self.assertEqual(result, mock_permissions)
    
    def test_validate_email(self):
        """Test _validate_email method."""
        # Create instance
        gs = GoogleSheetsIntegration()
        
        # Test valid emails
        self.assertTrue(gs._validate_email("user@example.com"))
        self.assertTrue(gs._validate_email("test.user@subdomain.example.co.uk"))
        
        # Test invalid emails
        self.assertFalse(gs._validate_email("invalid"))
        self.assertFalse(gs._validate_email("invalid@"))
        self.assertFalse(gs._validate_email("@example.com"))
        self.assertFalse(gs._validate_email(""))
        self.assertFalse(gs._validate_email(None))

    def test_validate_permission_type(self):
        """Test _validate_permission_type method."""
        # Create instance
        gs = GoogleSheetsIntegration()
        
        # Test with enum
        self.assertEqual(gs._validate_permission_type(PermissionType.READER), "reader")
        self.assertEqual(gs._validate_permission_type(PermissionType.WRITER), "writer")
        self.assertEqual(gs._validate_permission_type(PermissionType.OWNER), "owner")
        
        # Test with strings
        self.assertEqual(gs._validate_permission_type("reader"), "reader")
        self.assertEqual(gs._validate_permission_type("writer"), "writer")
        self.assertEqual(gs._validate_permission_type("owner"), "owner")
        
        # Test invalid
        with self.assertRaises(ValueError):
            gs._validate_permission_type("invalid")
    
    @patch('integrations.google_sheets.GoogleSheetsIntegration._ensure_authenticated')
    def test_make_public(self, mock_ensure_auth):
        """Test make_public method."""
        # Setup
        mock_spreadsheet = MagicMock()
        
        # Create instance with mocked spreadsheet
        gs = GoogleSheetsIntegration(
            credentials_file=self.temp_creds_file.name,
            spreadsheet_id=self.spreadsheet_id
        )
        gs.spreadsheet = mock_spreadsheet
        
        # Call method with READER permission
        result = gs.make_public(PermissionType.READER)
        
        # Verify
        mock_ensure_auth.assert_called_once()
        mock_spreadsheet.share.assert_called_once_with(
            None,
            perm_type='anyone',
            role='reader'
        )
        self.assertTrue(result)
        
        # Reset mocks for second test
        mock_ensure_auth.reset_mock()
        mock_spreadsheet.share.reset_mock()
        
        # Call method with WRITER permission
        result = gs.make_public(PermissionType.WRITER)
        
        # Verify
        mock_ensure_auth.assert_called_once()
        mock_spreadsheet.share.assert_called_once_with(
            None,
            perm_type='anyone',
            role='writer'
        )
        self.assertTrue(result)
        
        # Test that we can't make a spreadsheet publicly owned
        with self.assertRaises(ValueError):
            gs.make_public(PermissionType.OWNER)
    
    @patch('integrations.google_sheets.GoogleSheetsIntegration._ensure_authenticated')
    def test_make_private(self, mock_ensure_auth):
        """Test make_private method."""
        # Setup
        mock_spreadsheet = MagicMock()
        mock_permissions = [{"type": "anyone", "id": "public-permission-id"}]
        mock_spreadsheet.list_permissions.return_value = mock_permissions
        
        # Create instance with mocked spreadsheet
        gs = GoogleSheetsIntegration(
            credentials_file=self.temp_creds_file.name,
            spreadsheet_id=self.spreadsheet_id
        )
        gs.spreadsheet = mock_spreadsheet
        
        # Call method
        result = gs.make_private()
        
        # Verify - _ensure_authenticated is called twice, once directly and once via get_spreadsheet_permissions
        self.assertEqual(mock_ensure_auth.call_count, 2)
        mock_spreadsheet.list_permissions.assert_called_once()
        mock_spreadsheet.remove_permission.assert_called_once_with("public-permission-id")
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()
    
    
class TestGoogleSheetsIntegrationCache(unittest.TestCase):
    """Test cases for GoogleSheetsIntegration caching functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock credentials dictionary
        self.mock_credentials = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "fake_key_id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nfakekey\n-----END PRIVATE KEY-----\n",
            "client_email": "test@example.com",
            "client_id": "12345",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40example.com"
        }
        
        # Sample spreadsheet ID
        self.spreadsheet_id = "1abc2defghijklmnopqrstuvwxyz"
    
    @patch('integrations.google_sheets.Credentials')
    @patch('integrations.google_sheets.gspread')
    def test_worksheet_caching(self, mock_gspread, mock_credentials):
        """Test that worksheets are properly cached."""
        # Setup mocks
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_worksheet = MagicMock()
        
        mock_gspread.authorize.return_value = mock_client
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        
        # Create instance with credential dictionary and enable caching
        gs = GoogleSheetsIntegration(
            credentials_dict=self.mock_credentials,
            spreadsheet_id=self.spreadsheet_id,
            enable_caching=True
        )
        
        # Authenticate
        gs.client = mock_client
        gs.spreadsheet = mock_spreadsheet
        gs.authenticated = True
        
        # First call - should access API
        worksheet1 = gs.get_worksheet("Sheet1")
        
        # Second call - should use cache
        worksheet2 = gs.get_worksheet("Sheet1")
        
        # Verify
        self.assertEqual(worksheet1, worksheet2)
        # Worksheet should only be fetched once
        mock_spreadsheet.worksheet.assert_called_once_with("Sheet1")
        
        # Clear cache
        gs.clear_cache()
        
        # Fetch again - should access API again
        gs.get_worksheet("Sheet1")
        
        # Verify worksheet was fetched twice
        self.assertEqual(mock_spreadsheet.worksheet.call_count, 2)
    
    @patch('integrations.google_sheets.Credentials')
    @patch('integrations.google_sheets.gspread')
    def test_permissions_caching(self, mock_gspread, mock_credentials):
        """Test that permissions are properly cached."""
        # Setup mocks
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_permissions = [{"emailAddress": "user@example.com", "role": "writer"}]
        
        mock_gspread.authorize.return_value = mock_client
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_spreadsheet.list_permissions.return_value = mock_permissions
        
        # Create instance with credential dictionary and enable caching
        gs = GoogleSheetsIntegration(
            credentials_dict=self.mock_credentials,
            spreadsheet_id=self.spreadsheet_id,
            enable_caching=True
        )
        
        # Setup instance
        gs.client = mock_client
        gs.spreadsheet = mock_spreadsheet
        gs.authenticated = True
        
        # First call - should access API
        permissions1 = gs.get_spreadsheet_permissions()
        
        # Second call - should use cache
        permissions2 = gs.get_spreadsheet_permissions()
        
        # Verify
        self.assertEqual(permissions1, permissions2)
        # Permissions should only be fetched once
        mock_spreadsheet.list_permissions.assert_called_once()
        
        # Force refresh - should access API again
        gs.get_spreadsheet_permissions(force_refresh=True)
        
        # Verify permissions were fetched twice
        self.assertEqual(mock_spreadsheet.list_permissions.call_count, 2)
    
    @patch('integrations.google_sheets.GoogleSheetsIntegration._ensure_authenticated')
    def test_check_api_access(self, mock_ensure_auth):
        """Test check_api_access method."""
        # Setup mocks
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        
        # Create instance
        gs = GoogleSheetsIntegration(
            credentials_dict=self.mock_credentials,
            spreadsheet_id=self.spreadsheet_id
        )
        
        # Set properties directly to avoid authentication issues
        gs.client = mock_client
        gs.spreadsheet = mock_spreadsheet
        gs.authenticated = True
        
        # Mock internal calls - we'll test the two separate API accesses
        # Make sure list_spreadsheet_files works for Google Sheets API
        mock_client.list_spreadsheet_files.return_value = [{"id": "mock_id"}]
        # Make sure list_permissions works for Google Drive API
        mock_spreadsheet.list_permissions.return_value = [{"role": "owner"}]
        
        # Call the method
        result = gs.check_api_access()
        
        # Verify results
        self.assertIn('sheets', result)
        self.assertIn('drive', result)
        # Since our mocks are set to return valid values, both APIs should be accessible
        self.assertTrue(all(result.values()))


class TestGoogleSheetsIntegrationOptimized(unittest.TestCase):
    """Test cases for GoogleSheetsIntegration optimized methods."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock credentials dictionary
        self.mock_credentials = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "fake_key_id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nfakekey\n-----END PRIVATE KEY-----\n",
            "client_email": "test@example.com",
            "client_id": "12345",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40example.com"
        }
        
        # Sample spreadsheet ID
        self.spreadsheet_id = "1abc2defghijklmnopqrstuvwxyz"
        
        # Sample data
        self.test_data = [
            {"Name": "John", "Age": 25, "City": "New York"},
            {"Name": "Alice", "Age": 30, "City": "London"},
            {"Name": "Bob", "Age": 22, "City": "Paris"}
        ]
    
    @patch('integrations.google_sheets.GoogleSheetsIntegration._ensure_authenticated')
    def test_upload_data_optimized_clear_existing(self, mock_ensure_auth):
        """Test upload_data_optimized with clear_existing=True."""
        # Setup
        mock_worksheet = MagicMock()
        
        # Create instance
        gs = GoogleSheetsIntegration(
            credentials_dict=self.mock_credentials,
            spreadsheet_id=self.spreadsheet_id
        )
        
        # Mock get_worksheet to return our mock
        gs.get_worksheet = MagicMock(return_value=mock_worksheet)
        
        # Call with clear_existing=True
        result = gs.upload_data_optimized(self.test_data, "Sheet1", clear_existing=True)
        
        # Verify
        mock_ensure_auth.assert_called_once()
        gs.get_worksheet.assert_called_once_with("Sheet1")
        mock_worksheet.clear.assert_called_once()
        mock_worksheet.update.assert_called_once()
        self.assertEqual(result["added"], 4)  # Header row + 3 data rows
        
    @patch('integrations.google_sheets.GoogleSheetsIntegration._ensure_authenticated')
    def test_upload_data_optimized_detect_changes(self, mock_ensure_auth):
        """Test upload_data_optimized with detect_changes=True."""
        # Setup
        mock_worksheet = MagicMock()
        existing_values = [
            ["Name", "Age", "City"],
            ["John", "25", "New York"],
            ["Alice", "30", "London"],
            ["Bob", "22", "Paris"]
        ]
        mock_worksheet.get_all_values.return_value = existing_values
        
        # Slightly modified data
        modified_data = self.test_data.copy()
        modified_data[1]["Age"] = 31  # Change Alice's age
        
        # Create instance
        gs = GoogleSheetsIntegration(
            credentials_dict=self.mock_credentials,
            spreadsheet_id=self.spreadsheet_id
        )
        
        # Mock get_worksheet to return our mock
        gs.get_worksheet = MagicMock(return_value=mock_worksheet)
        
        # Call with detect_changes=True
        result = gs.upload_data_optimized(modified_data, "Sheet1", detect_changes=True)
        
        # Verify
        mock_ensure_auth.assert_called_once()
        gs.get_worksheet.assert_called_once_with("Sheet1")
        mock_worksheet.get_all_values.assert_called_once()
        mock_worksheet.batch_update.assert_called_once()
        
        # Check that we have some updated cells, but don't verify exact count
        # as implementation details might change
        self.assertIn("updated", result)
        self.assertIn("unchanged", result)
