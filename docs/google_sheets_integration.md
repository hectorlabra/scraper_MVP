# Google Sheets Integration

The Google Sheets Integration module provides functionality to authenticate with the Google Sheets API, manage spreadsheets, upload data, and control sharing permissions.

## Features

- OAuth2 authentication using service account credentials
- Flexible credential loading from files or environment variables
- Creating and accessing Google Sheets spreadsheets
- Uploading and appending data to worksheets
- Managing permissions and sharing settings
- Handling rate limiting and API errors

## Prerequisites

Before using this module, you need:

1. A Google Cloud Platform (GCP) project
2. Google Sheets API and Drive API enabled for your project
3. A service account with appropriate permissions
4. Service account credentials (JSON key file)

### Setup Guide for Google Cloud

#### 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click on "Select a project" at the top, then "New Project"
3. Name your project (e.g., "ScraperMVP") and create it

#### 2. Enable Required APIs

1. In your project, go to "APIs & Services" > "Library"
2. Search for and enable the following APIs:
   - Google Sheets API
   - Google Drive API

#### 3. Create a Service Account

1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Name your service account (e.g., "scrapermpv")
4. Grant roles: "Editor" is sufficient for most operations
5. Click "Create and Continue", then "Done"

#### 4. Generate Service Account Key

1. Find your service account in the list and click on it
2. Go to the "Keys" tab
3. Click "Add Key" > "Create new key"
4. Choose JSON format and click "Create"
5. Save the downloaded JSON file securely (this is your credentials file)

#### 5. Configure Environment Variables

Add these variables to your `.env` file:

```
GOOGLE_SERVICE_ACCOUNT_FILE=path/to/your-credentials-file.json
GOOGLE_SHEETS_SPREADSHEET_ID=your-spreadsheet-id-if-using-existing-sheet
```

## Installation

Required packages:

- gspread (Google Sheets API wrapper)
- google-auth (Google authentication library)
- pandas (for data manipulation)

These dependencies are included in the project's `requirements.txt` file.

## Authentication Flow

![Authentication Flow Diagram](https://raw.githubusercontent.com/yourusername/scraperMVP/main/docs/images/google_sheets_auth_flow.png)

The authentication process follows these steps:

1. The application loads credentials (either from a file or environment variables)
2. The credentials are used to create an OAuth2 token
3. This token is used to authenticate with the Google Sheets API
4. Once authenticated, the application can perform operations on spreadsheets

## Authentication

The Google Sheets Integration module supports multiple methods of authentication:

### 1. Using a Service Account Credentials File

```python
from integrations.google_sheets import GoogleSheetsIntegration

# Authenticate with credentials file
sheets = GoogleSheetsIntegration(credentials_file='/path/to/service-account.json')
sheets.authenticate()
```

### 2. Using Environment Variables

```python
# Set environment variable GOOGLE_SERVICE_ACCOUNT_FILE to the path of your credentials file
# Or set GOOGLE_SERVICE_ACCOUNT_JSON to the JSON content of your credentials

from integrations.google_sheets import GoogleSheetsIntegration

# Automatically loads credentials from environment variables
sheets = GoogleSheetsIntegration()
sheets.authenticate()
```

### 3. Using a Credentials Dictionary

```python
from integrations.google_sheets import GoogleSheetsIntegration

credentials_dict = {
    "type": "service_account",
    "project_id": "your-project-id",
    "private_key_id": "key-id",
    "private_key": "-----BEGIN PRIVATE KEY-----\nPrivate key content\n-----END PRIVATE KEY-----\n",
    "client_email": "service-account@project-id.iam.gserviceaccount.com",
    "client_id": "client-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/service-account%40project-id.iam.gserviceaccount.com"
}

sheets = GoogleSheetsIntegration(credentials_dict=credentials_dict)
sheets.authenticate()
```

## Spreadsheet Operations

### Creating a New Spreadsheet

```python
# Create a new spreadsheet and get its ID
spreadsheet_id = sheets.create_spreadsheet("My New Spreadsheet")
```

### Opening an Existing Spreadsheet

```python
# Open by ID
sheets.open_spreadsheet_by_id("spreadsheet_id")

# Open by URL
sheets.open_spreadsheet_by_url("https://docs.google.com/spreadsheets/d/spreadsheet_id/edit")
```

### Working with Worksheets

```python
# Get a worksheet (creates it if it doesn't exist)
worksheet = sheets.get_worksheet("Sheet1")

# Get a worksheet without creating it if missing
try:
    worksheet = sheets.get_worksheet("ExistingSheet", create_if_missing=False)
except gspread.exceptions.WorksheetNotFound:
    print("Worksheet not found!")
```

## Data Operations

### Uploading Data

```python
import pandas as pd

# Create sample data
data = pd.DataFrame({
    'Name': ['John', 'Alice', 'Bob'],
    'Age': [25, 30, 22]
})

# Upload DataFrame to a worksheet (clears existing data)
sheets.upload_data(data, "Users")

# Upload list of dictionaries
user_list = [
    {'Name': 'John', 'Age': 25},
    {'Name': 'Alice', 'Age': 30},
    {'Name': 'Bob', 'Age': 22}
]
sheets.upload_data(user_list, "Users")
```

### Appending Data

```python
# Append data without clearing existing content
new_data = pd.DataFrame({
    'Name': ['Charlie', 'David'],
    'Age': [28, 35]
})
sheets.append_data(new_data, "Users")
```

## Permission Management

The Google Sheets Integration provides several methods to manage access permissions for spreadsheets.

### Parameter Formats for Different Permission Types

The Google Sheets API uses different parameter formats depending on whether you're sharing with specific users or making a spreadsheet publicly accessible:

1. For specific users (via `share_spreadsheet`):

   - Requires an email address
   - Uses `perm_type` parameter with values "reader", "writer", or "owner"
   - Can include notification options

2. For public access (via `make_public`):
   - No email address (set to `None`)
   - Uses `perm_type="anyone"` to indicate public access
   - Uses `role` parameter with values "reader" or "writer"

This difference is handled automatically by the respective methods in the GoogleSheetsIntegration class.

### Sharing a Spreadsheet

```python
from integrations.google_sheets import PermissionType

# Share with a specific user as a reader
sheets.share_spreadsheet("user@example.com")

# Share with a specific user as a writer
sheets.share_spreadsheet(
    "user@example.com",
    permission_type=PermissionType.WRITER,
    message="Here's the spreadsheet I mentioned."
)

# Share with a specific user as an owner
sheets.share_spreadsheet("user@example.com", PermissionType.OWNER)
```

### Making a Spreadsheet Public

```python
# Make the spreadsheet publicly accessible (read-only)
sheets.make_public()

# Make the spreadsheet publicly editable
sheets.make_public(PermissionType.WRITER)
```

### Making a Spreadsheet Private

```python
# Remove public access
sheets.make_private()
```

### Removing User Access

```python
# Remove a user's access
sheets.remove_permission("user@example.com")
```

### Getting Current Permissions

```python
# Get all current permissions
permissions = sheets.get_spreadsheet_permissions()
for perm in permissions:
    print(f"Email: {perm.get('emailAddress', 'N/A')}, Role: {perm.get('role')}, Type: {perm.get('type')}")

# Identify public permissions
public_permissions = [p for p in permissions if p.get('type') == 'anyone']
if public_permissions:
    print("This spreadsheet is publicly accessible")
```

## Troubleshooting Guide

### Common Issues

#### 1. Authentication Failures

| Problem                      | Solution                                                                                     |
| ---------------------------- | -------------------------------------------------------------------------------------------- |
| "Credentials file not found" | Check that the file path in `GOOGLE_SERVICE_ACCOUNT_FILE` is correct and accessible          |
| "Invalid credentials"        | Verify the JSON file is correctly formatted and contains all required fields                 |
| "Access token expired"       | This should be handled automatically, but if persistent, regenerate your service account key |

#### 2. Permission Errors

| Problem                                                | Solution                                                                      |
| ------------------------------------------------------ | ----------------------------------------------------------------------------- |
| "You don't have permission to access this spreadsheet" | Ensure the spreadsheet has been shared with your service account email        |
| "Cannot access spreadsheet with ID"                    | Verify the spreadsheet ID is correct and that your service account has access |
| "Insufficient permissions"                             | Your service account may need additional permissions in Google Cloud          |

#### 3. API Errors

| Problem                    | Solution                                                                                        |
| -------------------------- | ----------------------------------------------------------------------------------------------- |
| "API has not been enabled" | Ensure both Google Sheets API and Google Drive API are enabled in your Google Cloud project     |
| "API rate limit exceeded"  | The integration has built-in retry logic, but you might need to implement additional throttling |
| "Invalid value"            | Check the format of the data you're uploading, especially if you're using custom formatting     |

### Manual Sharing Process

If your service account can't access an existing spreadsheet, manually share it:

1. Open the Google Spreadsheet in your browser
2. Click the "Share" button in the top right corner
3. Add the service account email (it looks like: `your-service-account@your-project.iam.gserviceaccount.com`)
4. Set the permission to "Editor"
5. Click "Done"

After sharing, your application will be able to access and modify the spreadsheet.

### Verifying API Access

Use the `check_api_access()` method to verify that your credentials have access to the required APIs:

```python
# Check API access
access_status = sheets.check_api_access()
print(f"Drive API access: {access_status['drive']}")
print(f"Sheets API access: {access_status['sheets']}")
```

### Logging

The integration has built-in logging that can help diagnose issues. Set your logging level to DEBUG to see more detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Error Handling

The module includes comprehensive error handling with specific exceptions for different error scenarios:

- Authentication errors
- Permission errors
- Rate limiting
- Invalid input values
- API errors

Example error handling:

```python
from integrations.google_sheets import GoogleSheetsIntegration
from google.auth.exceptions import GoogleAuthError

try:
    sheets = GoogleSheetsIntegration(credentials_file='/path/to/service-account.json')
    sheets.authenticate()
    sheets.create_spreadsheet("Test Spreadsheet")

except FileNotFoundError:
    print("Credentials file not found!")

except GoogleAuthError as e:
    print(f"Authentication error: {str(e)}")

except ValueError as e:
    print(f"Invalid input: {str(e)}")

except Exception as e:
    print(f"Unexpected error: {str(e)}")
```

## Rate Limiting

The module includes built-in handling for API rate limiting with exponential backoff. Operations will automatically retry when rate limits are encountered.

## Best Practices

1. Store credentials securely, preferably as environment variables or in secure storage
2. Avoid hardcoding credentials in your code
3. Use the minimum required permissions for your service account
4. Handle authentication errors appropriately
5. Always check if authentication was successful before performing operations
6. Use appropriate error handling for all API operations
7. Implement proper logging for debugging and monitoring

## Performance Optimizations

The Google Sheets Integration includes several performance optimizations to reduce API calls and improve efficiency.

### Caching

The module includes intelligent caching to minimize API calls:

```python
# Enable caching (enabled by default)
sheets = GoogleSheetsIntegration(enable_caching=True)

# Get a worksheet (first call hits the API)
worksheet = sheets.get_worksheet("Sheet1")

# Second call uses cached data (much faster, no API call)
worksheet = sheets.get_worksheet("Sheet1")

# Clear the cache when needed
sheets.clear_cache()

# Force refresh permissions
permissions = sheets.get_spreadsheet_permissions(force_refresh=True)
```

The cache uses a Time-To-Live (TTL) mechanism to ensure data freshness. By default:

- Cache entries expire after 5 minutes
- Maximum of 100 cache items are stored

You can customize these settings by modifying the class properties:

```python
# Custom cache settings
GoogleSheetsIntegration.CACHE_TTL = 600  # 10 minutes
GoogleSheetsIntegration.MAX_CACHE_ITEMS = 200
```

### Optimized Data Upload

The module includes an optimized data upload method that detects changes and only updates modified cells:

```python
import pandas as pd

# Standard upload method (updates all cells)
sheets.upload_data(data, "Sheet1")

# Optimized upload (only updates changed cells)
stats = sheets.upload_data_optimized(data, "Sheet1", detect_changes=True)

# Check update statistics
print(f"Updated {stats['updated']} cells, left {stats['unchanged']} cells unchanged, added {stats['added']} new cells")
```

Benefits of the optimized upload:

- Significantly reduces API calls for large datasets with small changes
- Faster execution for partial updates
- Preserves cell formatting of unchanged cells
- Reduces API quota usage

### Batch Operations

For multiple operations, the module uses batch API calls when possible:

```python
# Updating multiple cells efficiently
stats = sheets.upload_data_optimized(data, "Sheet1")
```

## Advanced Usage

### Working with Multiple Spreadsheets

You can work with multiple spreadsheets in the same session:

```python
# First spreadsheet
sheets.open_spreadsheet_by_id("spreadsheet_id_1")
sheets.upload_data(data1, "Sheet1")

# Switch to another spreadsheet
sheets.open_spreadsheet_by_id("spreadsheet_id_2")
sheets.upload_data(data2, "Sheet2")
```

### API Usage Monitoring

Monitor your API usage to avoid hitting rate limits:

```python
# Get last sync timestamp (last time data was updated)
last_sync = sheets._last_sync_timestamp
if last_sync:
    print(f"Last sync: {last_sync.strftime('%Y-%m-%d %H:%M:%S')}")
```

## Troubleshooting API Access

In case you experience issues with API access, the module provides a diagnostic method to verify API access:

```python
# Check API access
api_status = sheets.check_api_access()
print(f"Google Sheets API: {'✓ Accessible' if api_status['sheets'] else '✗ Not accessible'}")
print(f"Google Drive API: {'✓ Accessible' if api_status['drive'] else '✗ Not accessible'}")
```

### Common API Access Issues

1. **Google Sheets API not accessible, but Google Drive API is accessible**:

   - Ensure Google Sheets API is enabled in Google Cloud Console
   - The service account might have Drive access but not Sheets access

2. **Google Drive API not accessible, but Google Sheets API is accessible**:

   - Ensure Google Drive API is enabled in Google Cloud Console
   - This can cause permission management functions to fail even if you can access spreadsheets

3. **Cannot access a specific spreadsheet**:
   - Verify the spreadsheet ID is correct
   - The service account needs explicit permission to access the spreadsheet
   - Share the spreadsheet with the service account email address

### Using the Share Spreadsheet Helper

Use the provided helper script to create and share a spreadsheet properly:

```bash
python scripts/share_spreadsheet.py
```

This script creates a new spreadsheet owned by the service account and shares it with a specified email address. This approach ensures that the service account has full control over the spreadsheet.

### Creating Your Own Spreadsheets vs. Using Existing Ones

1. **Creating new spreadsheets through the API**:

   - Service account has full control automatically
   - All permission operations will work as expected
   - Recommended for automated workflows

2. **Using existing spreadsheets**:
   - Service account must be explicitly added as an editor or owner
   - Permission operations might be limited based on the service account's role
   - If the sheet is owned by a personal account, permission operations may fail
