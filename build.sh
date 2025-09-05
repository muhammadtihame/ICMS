#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Create staticfiles directory if it doesn't exist
mkdir -p staticfiles

# Make sure we have the latest migrations
python manage.py makemigrations

# Run migrations
python manage.py migrate

# Collect static files with --clear to ensure clean collection
python manage.py collectstatic --noinput --clear

# Create superuser if it doesn't exist (optional)
# python manage.py createsuperuser --noinput || true