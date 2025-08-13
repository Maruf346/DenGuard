# planner/models.py
from django.db import models

class DengueStat(models.Model):
    location_name = models.CharField(max_length=255)
    longitude = models.FloatField()
    latitude = models.FloatField()
    total = models.PositiveIntegerField()      # total admitted
    dead = models.PositiveIntegerField(default=0)
    male = models.PositiveIntegerField(default=0)
    female = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.location_name} — total:{self.total}"

