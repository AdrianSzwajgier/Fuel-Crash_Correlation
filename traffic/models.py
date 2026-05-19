from django.db import models

class AccidentRecord(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()  # 1-12

    accidents_total = models.IntegerField()
    accidents_pct = models.FloatField()
    fatalities_total = models.IntegerField()
    fatalities_pct = models.FloatField()
    injured_total = models.IntegerField()
    injured_pct = models.FloatField()

    class Meta:
        unique_together = ("year", "month")
        ordering = ["year", "month"]

    def __str__(self):
        return f"{self.year}-{self.month:02d}"