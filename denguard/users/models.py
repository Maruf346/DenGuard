from django.conf import settings
from django.db import models

class UserProfile(models.Model):
    user     = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # example extra fields:
    location = models.CharField(max_length=100, blank=True)
    avatar   = models.URLField(blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"
