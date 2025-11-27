"""
Core URL configuration.
"""
from django.urls import path

from . import views
from .views_language import set_language

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("search-dropdown/", views.search_dropdown, name="search_dropdown"),
    path("categories/", views.get_categories, name="categories"),
    path("tags/", views.get_tags, name="tags"),
    path("tags/<slug:slug>/", views.tag_videos, name="tag_videos"),
    path("tags/autocomplete/", views.tag_autocomplete, name="tag_autocomplete"),
    path("community/", views.community_list, name="community"),
    path("set-language/", set_language, name="set_language"),
    path("robots.txt", views.robots_txt, name="robots_txt"),
]
