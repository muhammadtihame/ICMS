"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Use production settings for cloud deployment
if os.environ.get('RENDER') or os.environ.get('RAILPACK') or os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_production")
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
