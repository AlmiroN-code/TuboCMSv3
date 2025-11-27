"""
Priority management utilities for video processing queue.
"""
from django.conf import settings


class PriorityManager:
    """
    Manages task priorities for video processing.
    
    Priority levels (higher = processed first):
    - 10: Critical (admin uploads, urgent)
    - 7-9: High (premium users)
    - 5: Normal (regular users, default)
    - 3: Low (new users with < 5 videos)
    - 1: Bulk (batch processing, re-encoding)
    """
    
    PRIORITY_CRITICAL = 10
    PRIORITY_HIGH = 7
    PRIORITY_NORMAL = 5
    PRIORITY_LOW = 3
    PRIORITY_BULK = 1
    
    PRIORITY_LABELS = {
        10: 'critical',
        9: 'high',
        8: 'high',
        7: 'high',
        6: 'normal',
        5: 'normal',
        4: 'normal',
        3: 'low',
        2: 'low',
        1: 'bulk',
        0: 'bulk',
    }
    
    @classmethod
    def get_priority_for_video(cls, video):
        """
        Determine processing priority for a video.
        
        Args:
            video: Video instance
            
        Returns:
            int: Priority level (0-10)
        """
        if not video.created_by:
            return cls.PRIORITY_NORMAL
        
        user = video.created_by
        
        # Admin/staff uploads get high priority
        if user.is_staff or user.is_superuser:
            return cls.PRIORITY_CRITICAL
        
        # Use user's processing priority method if available
        if hasattr(user, 'get_processing_priority'):
            return user.get_processing_priority()
        
        # Premium users
        if getattr(user, 'is_premium', False):
            return max(cls.PRIORITY_HIGH, getattr(user, 'processing_priority', cls.PRIORITY_HIGH))
        
        # Active users with many videos
        videos_count = getattr(user, 'videos_count', 0)
        if videos_count > 50:
            return min(6, cls.PRIORITY_NORMAL + 1)
        
        # New users
        if videos_count < 5:
            return cls.PRIORITY_LOW
        
        # Default priority
        return getattr(user, 'processing_priority', cls.PRIORITY_NORMAL)
    
    @classmethod
    def get_priority_for_user(cls, user):
        """
        Get default priority for a user.
        
        Args:
            user: User instance
            
        Returns:
            int: Priority level (0-10)
        """
        if not user:
            return cls.PRIORITY_NORMAL
        
        if user.is_staff or user.is_superuser:
            return cls.PRIORITY_CRITICAL
        
        if hasattr(user, 'get_processing_priority'):
            return user.get_processing_priority()
        
        if getattr(user, 'is_premium', False):
            return cls.PRIORITY_HIGH
        
        return cls.PRIORITY_NORMAL
    
    @classmethod
    def get_priority_label(cls, priority):
        """
        Get human-readable label for priority level.
        
        Args:
            priority: int priority level
            
        Returns:
            str: Priority label
        """
        return cls.PRIORITY_LABELS.get(priority, 'normal')
    
    @classmethod
    def get_queue_name(cls, priority):
        """
        Get Celery queue name based on priority.
        
        Args:
            priority: int priority level
            
        Returns:
            str: Queue name
        """
        # All video processing goes to the same queue
        # Priority is handled by Celery's priority feature
        return 'video_processing'
