"""
Constants for videos app.
"""

# Pagination
VIDEOS_PER_PAGE = 20
COMMENTS_PER_PAGE = 10

# Homepage limits
FEATURED_VIDEOS_LIMIT = 8
RECENT_VIDEOS_LIMIT = 16
RELATED_VIDEOS_LIMIT = 6

# Search limits
SEARCH_RESULTS_LIMIT = 50
SEARCH_SUGGESTIONS_LIMIT = 10
SEARCH_DROPDOWN_LIMIT = 8
SEARCH_MIN_QUERY_LENGTH = 2

# Video processing
MAX_VIDEO_SIZE_MB = 500
MAX_VIDEO_DURATION_SECONDS = 3600
ALLOWED_VIDEO_FORMATS = ["mp4", "avi", "mov", "wmv", "mkv"]

# Thumbnails
THUMBNAIL_SIZES = {
    "small": (150, 100),
    "medium": (300, 200),
    "large": (600, 400),
}

# Cache timeouts (in seconds)
CACHE_TIMEOUT_SHORT = 300  # 5 minutes
CACHE_TIMEOUT_MEDIUM = 1800  # 30 minutes
CACHE_TIMEOUT_LONG = 3600  # 1 hour
CACHE_TIMEOUT_VERY_LONG = 86400  # 24 hours

# Specific cache timeouts
RECOMMENDATIONS_CACHE_TIMEOUT = CACHE_TIMEOUT_MEDIUM
