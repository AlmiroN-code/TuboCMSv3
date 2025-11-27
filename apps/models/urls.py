"""
URLs for models app.
"""
from django.urls import path

from . import views

app_name = "models"

urlpatterns = [
    # Model views
    path("", views.ModelListView.as_view(), name="list"),
    path("<slug:slug>/", views.ModelDetailView.as_view(), name="detail"),
    path("create/", views.ModelCreateView.as_view(), name="create"),
    path("<slug:slug>/update/", views.ModelUpdateView.as_view(), name="update"),
    # Model actions
    path("<slug:slug>/subscribe/", views.model_subscribe, name="subscribe"),
    path("<slug:slug>/unsubscribe/", views.model_unsubscribe, name="unsubscribe"),
    path("<slug:slug>/like/", views.model_like, name="like"),
    path("<slug:slug>/unlike/", views.model_unlike, name="unlike"),
]
