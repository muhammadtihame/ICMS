# Manual Deployment Guide for CMS ProgressSQL on Render

This guide will walk you through deploying your Django CMS system manually on Render (without blueprints).

## Prerequisites

1. A Render account (free tier available)
2. Your Django project code in a Git repository (GitHub, GitLab, etc.)
3. Basic understanding of Django and PostgreSQL

## Step 1: Create a Web Service

1. Go to [render.com](https://render.com) and sign up/login
2. Click "New +" and select "Web Service"
3. Connect your Git repository: `muhammadtihame/ICMS`
4. Choose the branch: `fix/render-remove-db` (or merge to main first)

## Step 2: Configure the Web Service

### Basic Settings:
- **Name**: `cms-progress-sql`
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn config.wsgi:application`

### Environment Variables:
Add these environment variables in the Render dashboard:

```
PYTHON_VERSION=3.9.18
DJANGO_SECRET_KEY=your-secret-key-here-change-this-in-production
DEBUG=false
ALLOWED_HOSTS=cms-progress-sql-a6q1.onrender.com,*.onrender.com,localhost,127.0.0.1
STATIC_URL=/static/
MEDIA_URL=/media/
```

### Advanced Settings:
- **Plan**: Free (or Starter if you want always-on)
- **Auto-Deploy**: Yes
- **Health Check Path**: `/`

## Step 3: Create a PostgreSQL Database

1. In Render dashboard, click "New +" and select "PostgreSQL"
2. **Name**: `cms-progress-sql-db`
3. **Plan**: Free (or Starter)
4. **Database**: Leave default
5. **User**: Leave default
6. **Password**: Leave default (Render will generate)

## Step 4: Connect Database to Web Service

1. Go to your web service settings
2. Add environment variable:
   - **Key**: `DATABASE_URL`
   - **Value**: Copy the "External Database URL" from your PostgreSQL service

## Step 5: Deploy

1. Click "Create Web Service"
2. Render will automatically:
   - Install dependencies
   - Run migrations
   - Collect static files
   - Start your application

## Step 6: Update Secret Key

After deployment, generate a real secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Then update the `DJANGO_SECRET_KEY` environment variable in Render dashboard.

## Step 7: Create Superuser (Optional)

If you need admin access:

1. Go to your web service logs
2. Click "Shell" to open a terminal
3. Run: `python manage.py createsuperuser`

## Troubleshooting

### Common Issues:

1. **Build Failures**: Check the build logs in Render dashboard
2. **Database Connection**: Ensure `DATABASE_URL` is set correctly
3. **Static Files**: Should work automatically with our configuration
4. **Environment Variables**: Double-check all required variables are set

### Logs:
- Check build logs for deployment issues
- Check runtime logs for application errors
- Use Render's shell for debugging

## Cost

- **Free Tier**: 750 hours/month for web services, 90 days for databases
- **Starter Plan**: $7/month for always-on services

## Next Steps

After successful deployment:
1. Test your application
2. Set up monitoring and alerts
3. Configure custom domain (optional)
4. Set up automated backups

## Support

- Render Documentation: [docs.render.com](https://docs.render.com)
- Django Documentation: [docs.djangoproject.com](https://docs.djangoproject.com)
