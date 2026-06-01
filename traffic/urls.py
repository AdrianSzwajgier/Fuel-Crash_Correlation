from django.urls import path, include
from . import views

urlpatterns = [
    path("dashboard", views.dashboard, name="dashboard"),
    path("sync/", views.sync_database, name="sync_database"),
    path("chart-data/", views.chart_data, name="chart_data"),
    path("chart-data/by-month/", views.chart_data_by_month, name="chart_data_by_month"),
    path("correlation/", views.correlation_data, name="correlation_data"),

    path("gus/inflation/", views.inflation_data, name="inflation"),

    path("register", views.register, name='register'),

    path("", include('django.contrib.auth.urls')),

    path("profile/", views.profile, name='profile'),

    path("profile/password-change", views.change_password, name="password_change"),

    path("logout", views.log_out, name='logout'),

    path("source", views.used_data, name='used_data'),

    path("about", views.about, name='about'),
]
