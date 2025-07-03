import logging
from django.db import transaction, IntegrityError
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Profile

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        try:
            with transaction.atomic():
                Profile.objects.create(user=instance)
        except IntegrityError as e:
            logger.error(f"Profile creation failed for {instance.pk}: {e}")

            