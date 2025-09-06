"""
Custom media file serving for production environments
"""
import os
from django.http import HttpResponse, Http404
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.utils.encoding import escape_uri_path


@never_cache
@require_http_methods(["GET"])
def serve_media(request, path):
    """
    Serve media files in production environment.
    This is a temporary solution - in production, use a CDN or cloud storage.
    """
    # Security check - ensure the path is within MEDIA_ROOT
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    file_path = os.path.abspath(os.path.join(media_root, path))
    
    # Check if the file path is within MEDIA_ROOT (security)
    if not file_path.startswith(media_root):
        raise Http404("File not found")
    
    # Check if file exists
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise Http404("File not found")
    
    # Get file extension for content type
    ext = os.path.splitext(file_path)[1].lower()
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }
    
    content_type = content_types.get(ext, 'application/octet-stream')
    
    try:
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=content_type)
            response['Content-Disposition'] = f'inline; filename="{escape_uri_path(os.path.basename(file_path))}"'
            return response
    except (IOError, OSError):
        raise Http404("File not found")
