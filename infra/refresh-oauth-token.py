#!/usr/bin/env python3
"""
YouTube OAuth Token Refresh Script

This script automatically refreshes YouTube OAuth tokens and stores them
in Google Cloud Secret Manager for secure access by n8n workflows.

Features:
- Automatic token refresh using refresh_token
- Google Cloud Secret Manager integration
- Error handling and logging
- Test mode for credential validation
- Backup token storage

Usage:
    python3 refresh-oauth-token.py [--test] [--force]

Environment Variables Required:
    YOUTUBE_CLIENT_ID
    YOUTUBE_CLIENT_SECRET
    YOUTUBE_REFRESH_TOKEN
    GOOGLE_CLOUD_PROJECT_ID
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

try:
    import requests
    from google.cloud import secretmanager
    from google.auth import default
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Install with: pip3 install google-cloud-secret-manager requests google-auth")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/token-refresh.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class YouTubeTokenRefresher:
    """Handles YouTube OAuth token refresh and storage."""
    
    def __init__(self):
        self.client_id = os.getenv('YOUTUBE_CLIENT_ID')
        self.client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
        self.refresh_token = os.getenv('YOUTUBE_REFRESH_TOKEN')
        self.project_id = os.getenv('GOOGLE_PROJECT_ID')
        
        # Validate required environment variables
        self._validate_environment()
        
        # Initialize Google Cloud Secret Manager client
        try:
            self.secret_client = secretmanager.SecretManagerServiceClient()
        except Exception as e:
            logger.warning(f"Could not initialize Secret Manager client: {e}")
            self.secret_client = None
    
    def _validate_environment(self) -> None:
        """Validate that all required environment variables are set."""
        required_vars = [
            'YOUTUBE_CLIENT_ID',
            'YOUTUBE_CLIENT_SECRET', 
            'YOUTUBE_REFRESH_TOKEN',
            'GOOGLE_CLOUD_PROJECT_ID'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            raise ValueError(f"Missing environment variables: {missing_vars}")
    
    def refresh_access_token(self) -> Tuple[bool, Optional[Dict]]:
        """Refresh the YouTube access token using the refresh token."""
        logger.info("Refreshing YouTube access token...")
        
        token_url = "https://oauth2.googleapis.com/token"
        
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.post(token_url, data=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            
            if 'access_token' not in token_data:
                logger.error("No access_token in response")
                return False, None
            
            # Add metadata
            token_data['refreshed_at'] = datetime.utcnow().isoformat()
            token_data['expires_at'] = (datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600))).isoformat()
            
            logger.info("Successfully refreshed access token")
            return True, token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to refresh token: {e}")
            return False, None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            return False, None
    
    def store_token_in_secret_manager(self, token_data: Dict) -> bool:
        """Store the refreshed token in Google Cloud Secret Manager."""
        if not self.secret_client:
            logger.warning("Secret Manager client not available, skipping cloud storage")
            return False
        
        secret_name = "youtube-access-token"
        parent = f"projects/{self.project_id}"
        
        try:
            # Create secret if it doesn't exist
            try:
                secret_path = f"{parent}/secrets/{secret_name}"
                self.secret_client.get_secret(request={"name": secret_path})
                logger.info(f"Secret {secret_name} already exists")
            except Exception:
                # Secret doesn't exist, create it
                secret = {
                    "replication": {"automatic": {}}
                }
                self.secret_client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_name,
                        "secret": secret
                    }
                )
                logger.info(f"Created secret {secret_name}")
            
            # Add new version with token data
            secret_path = f"{parent}/secrets/{secret_name}"
            payload = json.dumps(token_data).encode('utf-8')
            
            response = self.secret_client.add_secret_version(
                request={
                    "parent": secret_path,
                    "payload": {"data": payload}
                }
            )
            
            logger.info(f"Stored token in Secret Manager: {response.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store token in Secret Manager: {e}")
            return False
    
    def store_token_locally(self, token_data: Dict) -> bool:
        """Store token data locally as backup."""
        try:
            backup_file = '/tmp/youtube-token-backup.json'
            
            with open(backup_file, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            # Set restrictive permissions
            os.chmod(backup_file, 0o600)
            
            logger.info(f"Stored token backup locally: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store token locally: {e}")
            return False
    
    def test_credentials(self) -> bool:
        """Test the current credentials by making a simple API call."""
        logger.info("Testing YouTube API credentials...")
        
        # First refresh the token
        success, token_data = self.refresh_access_token()
        if not success or not token_data:
            logger.error("Failed to refresh token for testing")
            return False
        
        # Test the token with a simple API call
        access_token = token_data['access_token']
        test_url = "https://www.googleapis.com/youtube/v3/channels"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        
        params = {
            'part': 'snippet',
            'mine': 'true'
        }
        
        try:
            response = requests.get(test_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'items' in data:
                logger.info("✅ Credentials test successful")
                if data['items']:
                    channel = data['items'][0]['snippet']
                    logger.info(f"Channel: {channel.get('title', 'Unknown')}")
                return True
            else:
                logger.error("❌ Unexpected API response format")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Credentials test failed: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON response during test: {e}")
            return False
    
    def run(self, test_only: bool = False, force: bool = False) -> bool:
        """Main execution method."""
        logger.info("Starting YouTube token refresh process")
        
        if test_only:
            return self.test_credentials()
        
        # Check if we need to refresh (skip if not forced and token is recent)
        if not force:
            # You could add logic here to check token expiry
            # For now, we'll always refresh unless explicitly testing
            pass
        
        # Refresh the token
        success, token_data = self.refresh_access_token()
        if not success or not token_data:
            logger.error("Failed to refresh access token")
            return False
        
        # Store in Secret Manager
        secret_stored = self.store_token_in_secret_manager(token_data)
        
        # Store locally as backup
        local_stored = self.store_token_locally(token_data)
        
        if secret_stored or local_stored:
            logger.info("✅ Token refresh completed successfully")
            
            # Update environment variable for current session
            os.environ['YOUTUBE_ACCESS_TOKEN'] = token_data['access_token']
            
            return True
        else:
            logger.error("❌ Failed to store refreshed token")
            return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Refresh YouTube OAuth tokens')
    parser.add_argument('--test', action='store_true', help='Test credentials only')
    parser.add_argument('--force', action='store_true', help='Force refresh even if token is recent')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        refresher = YouTubeTokenRefresher()
        success = refresher.run(test_only=args.test, force=args.force)
        
        if success:
            logger.info("🎉 Process completed successfully")
            sys.exit(0)
        else:
            logger.error("💥 Process failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()