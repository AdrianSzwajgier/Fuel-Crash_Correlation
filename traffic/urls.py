from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("sync/", views.sync_database, name="sync_database"),
    path("chart-data/", views.chart_data, name="chart_data"),
    path("chart-data/by-month/", views.chart_data_by_month, name="chart_data_by_month"),
]