"""
User URL configuration.
"""
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('settings/', views.user_settings, name='settings'),
    path('subscribe/<str:username>/', views.subscribe, name='subscribe'),
    path('unsubscribe/<str:username>/', views.unsubscribe, name='unsubscribe'),
    path('subscriptions/', views.subscriptions, name='subscriptions'),
]









