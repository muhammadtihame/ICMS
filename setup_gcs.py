#!/usr/bin/env python3
"""
Google Cloud Storage Setup Script for CMS ProgressSQL

This script helps set up Google Cloud Storage for media files in production.
Run this script to test your GCS configuration.
"""

import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_production')
django.setup()

def test_gcs_connection():
    """Test Google Cloud Storage connection and configuration."""
    print("🔍 Testing Google Cloud Storage Configuration...")
    
    # Check environment variables
    required_vars = ['GS_BUCKET_NAME', 'GOOGLE_CLOUD_PROJECT', 'GOOGLE_APPLICATION_CREDENTIALS']
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {value}")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    # Test storage backend
    try:
        from storages.backends.gcloud import GoogleCloudStorage
        storage = GoogleCloudStorage()
        
        # Test bucket access
        if storage.bucket.exists():
            print("✅ GCS bucket exists and is accessible")
        else:
            print("❌ GCS bucket does not exist or is not accessible")
            return False
            
        # Test file operations
        test_file_name = 'test-connection.txt'
        test_content = b'Test connection to Google Cloud Storage'
        
        # Save test file
        storage.save(test_file_name, test_content)
        print("✅ Successfully saved test file to GCS")
        
        # Check if file exists
        if storage.exists(test_file_name):
            print("✅ Test file exists in GCS")
        else:
            print("❌ Test file not found in GCS")
            return False
        
        # Delete test file
        storage.delete(test_file_name)
        print("✅ Successfully deleted test file from GCS")
        
        print("🎉 Google Cloud Storage is properly configured!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing GCS connection: {str(e)}")
        return False

def print_setup_instructions():
    """Print setup instructions for Google Cloud Storage."""
    print("\n📋 Google Cloud Storage Setup Instructions:")
    print("=" * 50)
    print("1. Create a Google Cloud Project:")
    print("   - Go to https://console.cloud.google.com/")
    print("   - Create a new project or select existing one")
    print("   - Note your project ID")
    print()
    print("2. Enable Cloud Storage API:")
    print("   - Go to APIs & Services > Library")
    print("   - Search for 'Cloud Storage API'")
    print("   - Click 'Enable'")
    print()
    print("3. Create a Storage Bucket:")
    print("   - Go to Cloud Storage > Buckets")
    print("   - Click 'Create Bucket'")
    print("   - Choose a unique name (will be your GS_BUCKET_NAME)")
    print("   - Select a location close to your users")
    print("   - Choose 'Uniform' access control")
    print("   - Make bucket public (for media files)")
    print()
    print("4. Create Service Account:")
    print("   - Go to IAM & Admin > Service Accounts")
    print("   - Click 'Create Service Account'")
    print("   - Give it a name like 'cms-storage'")
    print("   - Grant 'Storage Admin' role")
    print("   - Create and download JSON key file")
    print()
    print("5. Set Environment Variables in Render:")
    print("   USE_GCS=True")
    print("   GS_BUCKET_NAME=your-bucket-name")
    print("   GOOGLE_CLOUD_PROJECT=your-project-id")
    print("   GOOGLE_APPLICATION_CREDENTIALS=/opt/render/project/src/gcs-key.json")
    print()
    print("6. Upload Service Account Key:")
    print("   - Upload the JSON key file to your project root")
    print("   - Rename it to 'gcs-key.json'")
    print("   - Add it to your git repository (temporarily)")
    print("   - Or use Render's environment variables for the key content")

if __name__ == '__main__':
    print("🚀 CMS ProgressSQL - Google Cloud Storage Setup")
    print("=" * 50)
    
    # Check if we're in production mode
    if not os.environ.get('USE_GCS', 'False').lower() == 'true':
        print("ℹ️  GCS is not enabled. Set USE_GCS=True to enable.")
        print_setup_instructions()
        sys.exit(0)
    
    # Test connection
    if test_gcs_connection():
        print("\n✅ Setup complete! Your media files will now be stored in Google Cloud Storage.")
    else:
        print("\n❌ Setup failed. Please check your configuration.")
        print_setup_instructions()
        sys.exit(1)
