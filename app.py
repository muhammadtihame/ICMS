#!/usr/bin/env python
"""
Alternative entry point for Django application on Railpack.
This file serves as another fallback option.
"""
import os
import sys
import subprocess

def main():
    # Set Django settings module for production
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_production')
    
    # Get port from environment variable
    port = os.environ.get('PORT', '8000')
    
    # Start gunicorn server
    cmd = [
        'gunicorn',
        '--bind', f'0.0.0.0:{port}',
        '--workers', '3',
        '--timeout', '120',
        'config.wsgi:application'
    ]
    
    print(f"Starting Django application via app.py on port {port}")
    print(f"Command: {' '.join(cmd)}")
    
    # Execute the command
    subprocess.run(cmd)

if __name__ == '__main__':
    main()
