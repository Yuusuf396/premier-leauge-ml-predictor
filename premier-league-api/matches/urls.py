from django.urls import path

from . import views

urlpatterns = [
    path("teams/", views.list_teams, name="teams-list"),
    path("seasons/", views.list_seasons, name="seasons-list"),
    path("matches/", views.list_matches, name="matches-list"),
    path("predict/match", views.create_prediction, name="predict-match"),
    path("health/", views.health, name="health"),
    path("admin/models/active/", views.admin_active_model, name="admin-active-model"),
    path("predictions/", views.list_predictions, name="predictions-list"),
    path("predictions/create/", views.create_prediction, name="predictions-create"),
    path("predictions/<int:prediction_id>/", views.prediction_detail, name="predictions-detail"),
    path("models/active/", views.active_model, name="active-model"),
]
