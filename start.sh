#!/bin/bash
# Start script for Django application on Railpack
export DJANGO_SETTINGS_MODULE=config.settings_production
gunicorn --bind 0.0.0.0:$PORT config.wsgi:application
