from django.urls import path

from . import views

urlpatterns = [
    path("predictions/", views.list_predictions, name="predictions-list"),
    path("predictions/create/", views.create_prediction, name="predictions-create"),
    path("predictions/<int:prediction_id>/", views.prediction_detail, name="predictions-detail"),
    path("models/active/", views.active_model, name="active-model"),
]
