# Google Cloud Storage Setup Guide for CMS ProgressSQL

This guide will help you set up Google Cloud Storage for media files in your CMS ProgressSQL deployment on Render.

## 🚨 Current Issue

Your Render deployment is showing errors like:
```
ERROR: Internal Server Error: /media/profile_pictures/25/09/06/1725474248663-removebg-preview.png
Error processing image: [Errno 2] No such file or directory: '/opt/render/project/src/media/profile_pictures/...'
```

This happens because Render's filesystem is ephemeral - uploaded files disappear when the container restarts.

## ✅ Solution: Google Cloud Storage

We've configured your Django app to use Google Cloud Storage for media files. Here's how to set it up:

## 📋 Step-by-Step Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your **Project ID** (you'll need this later)

### 2. Enable Cloud Storage API

1. In the Google Cloud Console, go to **APIs & Services > Library**
2. Search for "Cloud Storage API"
3. Click **Enable**

### 3. Create Storage Bucket

1. Go to **Cloud Storage > Buckets**
2. Click **Create Bucket**
3. Choose a **unique bucket name** (this will be your `GS_BUCKET_NAME`)
4. Select a **location** close to your users
5. Choose **Uniform** access control
6. **Important**: Make the bucket public for media files:
   - After creating, click on the bucket name
   - Go to **Permissions** tab
   - Click **Add Principal**
   - Add `allUsers` with **Storage Object Viewer** role

### 4. Create Service Account

1. Go to **IAM & Admin > Service Accounts**
2. Click **Create Service Account**
3. Give it a name like `cms-storage`
4. Grant **Storage Admin** role
5. Click **Done**
6. Click on the created service account
7. Go to **Keys** tab
8. Click **Add Key > Create New Key**
9. Choose **JSON** format
10. Download the key file

### 5. Configure Render Environment Variables

In your Render dashboard, go to your service and add these environment variables:

```bash
USE_GCS=True
GS_BUCKET_NAME=your-bucket-name-here
GOOGLE_CLOUD_PROJECT=your-project-id-here
GOOGLE_APPLICATION_CREDENTIALS=/opt/render/project/src/gcs-key.json
```

### 6. Upload Service Account Key

**Option A: Upload as File (Recommended)**
1. Rename your downloaded JSON key file to `gcs-key.json`
2. Add it to your project root directory
3. Commit and push to GitHub
4. Render will automatically deploy it

**Option B: Use Environment Variable**
1. Copy the entire content of your JSON key file
2. In Render, add environment variable:
   - Key: `GCS_CREDENTIALS_JSON`
   - Value: (paste the entire JSON content)
3. Update your settings to use this environment variable

## 🔧 Alternative: Environment Variable Method

If you prefer not to upload the key file, you can use an environment variable instead:

1. In Render, add environment variable:
   - Key: `GCS_CREDENTIALS_JSON`
   - Value: (paste your entire JSON key content)

2. Update `config/settings_production.py` to use this:

```python
# Add this after the GCS configuration
if USE_GCS and os.environ.get('GCS_CREDENTIALS_JSON'):
    import json
    import tempfile
    
    # Write credentials to temporary file
    credentials_json = os.environ.get('GCS_CREDENTIALS_JSON')
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(credentials_json)
        GOOGLE_APPLICATION_CREDENTIALS = f.name
```

## 🧪 Testing Your Setup

1. Deploy your changes to Render
2. Try uploading a profile picture
3. Check if the image loads correctly
4. The image URL should be: `https://storage.googleapis.com/your-bucket-name/path/to/image.png`

## 🔍 Troubleshooting

### Common Issues:

1. **"Bucket not found" error**
   - Check your `GS_BUCKET_NAME` is correct
   - Ensure the bucket exists in the correct project

2. **"Permission denied" error**
   - Check your service account has Storage Admin role
   - Verify the JSON key file is correct

3. **"File not found" error**
   - Ensure the bucket is public
   - Check the file was uploaded successfully

4. **Environment variables not working**
   - Restart your Render service after adding environment variables
   - Check variable names are exactly as specified

### Debug Commands:

You can test your setup locally by running:
```bash
python setup_gcs.py
```

## 💰 Cost Considerations

Google Cloud Storage pricing:
- **Storage**: ~$0.020 per GB per month
- **Operations**: ~$0.05 per 10,000 operations
- **Network egress**: First 1GB per month is free

For a typical CMS with profile pictures and documents, costs should be minimal (< $5/month).

## 🔒 Security Notes

- The service account key gives full access to your bucket
- Keep the key file secure
- Consider using IAM conditions for more granular access
- Regularly rotate service account keys

## 📞 Support

If you encounter issues:
1. Check the Render logs for detailed error messages
2. Verify all environment variables are set correctly
3. Test the GCS connection using the setup script
4. Ensure your Google Cloud project has billing enabled

---

**After completing this setup, your media files will be stored permanently in Google Cloud Storage and will persist across Render deployments!**
