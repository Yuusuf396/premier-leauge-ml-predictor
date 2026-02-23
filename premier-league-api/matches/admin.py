from django.contrib import admin

from .models import ModelVersion, PredictionRequest, PredictionResult, Team


admin.site.register(Team)
admin.site.register(ModelVersion)
admin.site.register(PredictionRequest)
admin.site.register(PredictionResult)
