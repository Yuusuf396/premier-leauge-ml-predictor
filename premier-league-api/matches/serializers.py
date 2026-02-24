from rest_framework import serializers

from .models import ModelVersion, PredictionRequest, PredictionResult


class PredictionCreateSerializer(serializers.Serializer):
    home_team = serializers.CharField(max_length=100)
    away_team = serializers.CharField(max_length=100)
    season = serializers.CharField(max_length=20, required=False, allow_blank=True)
    match_date = serializers.DateField()

    def validate(self, attrs):
        if attrs["home_team"].strip().lower() == attrs["away_team"].strip().lower():
            raise serializers.ValidationError("Home team and away team must be different.")
        return attrs


class PredictionContractSerializer(serializers.Serializer):
    home_team = serializers.CharField()
    away_team = serializers.CharField()
    expected_home_goals = serializers.FloatField()
    expected_away_goals = serializers.FloatField()
    home_win_probability = serializers.FloatField()
    draw_probability = serializers.FloatField()
    away_win_probability = serializers.FloatField()
    model_version = serializers.CharField()
    features = serializers.JSONField()


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
