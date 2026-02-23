from rest_framework import serializers

from .models import ModelVersion, PredictionRequest, PredictionResult


class PredictionCreateSerializer(serializers.Serializer):
    home_team = serializers.CharField(max_length=100)
    away_team = serializers.CharField(max_length=100)
    match_date = serializers.DateField()

    def validate(self, attrs):
        if attrs["home_team"].strip().lower() == attrs["away_team"].strip().lower():
            raise serializers.ValidationError({"error": "home_team and away_team must be different"})
        return attrs


class PredictionResultSerializer(serializers.ModelSerializer):
    home_team = serializers.CharField(source="request.home_team.name")
    away_team = serializers.CharField(source="request.away_team.name")
    match_date = serializers.DateField(source="request.match_date")
    model_version = serializers.CharField(source="model_version.version")

    class Meta:
        model = PredictionResult
        fields = [
            "id",
            "home_team",
            "away_team",
            "match_date",
            "p_home",
            "p_draw",
            "p_away",
            "predicted_outcome",
            "model_version",
            "features_json",
            "created_at",
        ]


class ModelVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelVersion
        fields = [
            "id",
            "version",
            "artifact_path",
            "selected_model_name",
            "calibration_method",
            "val_log_loss",
            "val_accuracy",
            "is_active",
            "created_at",
        ]
