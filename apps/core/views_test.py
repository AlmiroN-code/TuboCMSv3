"""
Test views for translation system.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def test_translation(request):
    """Test translation page."""
    return render(request, 'test_translation.html')