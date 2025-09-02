from typing import Dict
from django.http import HttpRequest
from .models import NewsAndEvents
import time


def news_ticker(request: HttpRequest) -> Dict[str, object]:
    items = NewsAndEvents.objects.all().order_by("-updated_date")[:10]
    can_add_news = False
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        can_add_news = user.is_superuser or user.is_lecturer
    return {
        "ticker_items": items,
        "can_add_news": can_add_news,
    }


def timestamp(request: HttpRequest) -> Dict[str, object]:
    """Add timestamp for cache busting."""
    return {
        "timestamp": int(time.time())
    }


