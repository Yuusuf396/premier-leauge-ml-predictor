from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    short_name = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class ModelVersion(models.Model):
    version = models.CharField(max_length=64, unique=True)
    artifact_path = models.CharField(max_length=255)
    selected_model_name = models.CharField(max_length=64, blank=True)
    calibration_method = models.CharField(max_length=32, blank=True)
    val_log_loss = models.FloatField(null=True, blank=True)
    val_accuracy = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PredictionRequest(models.Model):
    home_team = models.ForeignKey(Team, related_name="home_requests", on_delete=models.PROTECT)
    away_team = models.ForeignKey(Team, related_name="away_requests", on_delete=models.PROTECT)
    match_date = models.DateField()
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-requested_at"]


class PredictionResult(models.Model):
    request = models.OneToOneField(PredictionRequest, related_name="result", on_delete=models.CASCADE)
    model_version = models.ForeignKey(ModelVersion, on_delete=models.PROTECT)
    p_home = models.FloatField()
    p_draw = models.FloatField()
    p_away = models.FloatField()
    predicted_outcome = models.CharField(max_length=1)
    features_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
