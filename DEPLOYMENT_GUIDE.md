# Deployment Guide for CMS ProgressSQL on Render

This guide will walk you through deploying your Django CMS system on Render.

## Prerequisites

1. A Render account (free tier available)
2. Your Django project code in a Git repository (GitHub, GitLab, etc.)
3. Basic understanding of Django and PostgreSQL

## Step 1: Prepare Your Repository

Make sure your repository contains all the necessary files:
- `requirements.txt` (updated for production)
- `config/settings_production.py` (production settings)
- `build.sh` (build script)
- `render.yaml` (service definitions)

## Step 2: Connect to Render

1. Go to [render.com](https://render.com) and sign up/login
2. Click "New +" and select "Blueprint"
3. Connect your Git repository
4. Render will automatically detect the `render.yaml` file

## Step 3: Configure Environment Variables

In your Render dashboard, set these environment variables:

### Required Variables:
- `DJANGO_SECRET_KEY`: A secure random string (Render can generate this)
- `DEBUG`: Set to `false`
- `ALLOWED_HOSTS`: Your Render domain (e.g., `cms-progress-sql.onrender.com`)

### Optional Variables:
- `EMAIL_HOST_USER`: Your email for sending notifications
- `EMAIL_HOST_PASSWORD`: Your email app password
- `STRIPE_SECRET_KEY`: If using Stripe payments
- `STRIPE_PUBLISHABLE_KEY`: If using Stripe payments

## Step 4: Deploy

1. Click "Create New Resources" in Render
2. Render will automatically:
   - Create a PostgreSQL database
   - Deploy your web service
   - Set up the database connection

## Step 5: Initial Setup

After deployment:

1. **Run Migrations**: Render will automatically run migrations during build
2. **Create Superuser**: Access your Django admin at `/admin/`
3. **Collect Static Files**: This happens automatically during build
4. **Test Your Application**: Visit your Render URL

## Step 6: Custom Domain (Optional)

1. In your Render dashboard, go to your web service
2. Click "Settings" → "Custom Domains"
3. Add your domain and configure DNS

## Important Notes

### Database
- Render automatically provides a PostgreSQL database
- The `DATABASE_URL` is automatically set
- Database backups are handled by Render

### Static Files
- Static files are served by WhiteNoise
- Media files are stored locally (consider using cloud storage for production)

### Security
- HTTPS is automatically enabled
- Security headers are configured in production settings
- Debug mode is disabled

### Monitoring
- Render provides built-in monitoring
- Check logs in your dashboard
- Set up alerts for downtime

## Troubleshooting

### Common Issues:

1. **Build Failures**: Check the build logs in Render dashboard
2. **Database Connection**: Ensure `DATABASE_URL` is set correctly
3. **Static Files**: Verify `STATIC_ROOT` and `MEDIA_ROOT` are correct
4. **Environment Variables**: Double-check all required variables are set

### Debug Mode:
- Never enable `DEBUG=True` in production
- Use Render's logging for debugging

## Cost Optimization

- Free tier includes:
  - 750 hours/month for web services
  - 90 days for PostgreSQL databases
- Upgrade to paid plans for:
  - Always-on services
  - Larger databases
  - Custom domains

## Support

- Render Documentation: [docs.render.com](https://docs.render.com)
- Django Documentation: [docs.djangoproject.com](https://docs.djangoproject.com)
- Render Community: [community.render.com](https://community.render.com)

## Next Steps

After successful deployment:
1. Set up monitoring and alerts
2. Configure automated backups
3. Set up CI/CD pipeline
4. Consider using cloud storage for media files
5. Implement proper logging and error tracking
