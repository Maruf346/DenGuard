from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import UserProfile
from allauth.socialaccount.models import SocialAccount


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    # Always ensure profile exists
    UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=SocialAccount)
def save_social_avatar(sender, instance, **kwargs):
    if instance.provider == 'google':
        profile, created = UserProfile.objects.get_or_create(user=instance.user)
        profile.avatar = instance.get_avatar_url()
        profile.save()
