from typing import Dict
from django.http import HttpRequest
from .models import NewsAndEvents
import time


def news_ticker(request: HttpRequest) -> Dict[str, object]:
    items = NewsAndEvents.objects.all().order_by("-updated_date")[:10]
    can_add_news = False
    user = getattr(request, "user", None)
    
    if user and user.is_authenticated:
        # Check if user is superuser or lecturer (using the same logic as home view)
        can_add_news = user.is_superuser or (hasattr(user, 'is_lecturer') and user.is_lecturer and user.is_active)
    
    return {
        "ticker_items": items,
        "can_add_news": can_add_news,
    }


def timestamp(request: HttpRequest) -> Dict[str, object]:
    """Add timestamp for cache busting."""
    return {
        "timestamp": int(time.time())
    }


