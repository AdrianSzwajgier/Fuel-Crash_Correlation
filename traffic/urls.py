from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("sync/", views.sync_database, name="sync_database"),
]