from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import UserProfile
from allauth.socialaccount.models import SocialAccount


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # Check if the user already has a profile
        if hasattr(instance, 'userprofile'):
            instance.userprofile.save()



@receiver(post_save, sender=SocialAccount)
def save_social_avatar(sender, instance, **kwargs):
    if instance.provider == 'google':
        profile = instance.user.userprofile
        profile.avatar = instance.get_avatar_url()
        profile.save()
