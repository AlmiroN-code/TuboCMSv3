"""
Core URL configuration.
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    path('categories/', views.get_categories, name='categories'),
    path('tags/', views.get_tags, name='tags'),
]




