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


class FuelPrice(models.Model):
    date = models.DateField(unique=True)
    diesel_price = models.DecimalField(max_digits=5, decimal_places=2)
    petrol_price = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.date} ON:{self.diesel_price} E95:{self.petrol_price}"


class Inflation(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()
    value = models.FloatField()

    class Meta:
        unique_together = ("year", "month")
        ordering = ["year", "month"]

    def __str__(self):
        return f"Year:{self.year}, month:{self.month:02d}, value:{self.value}"
