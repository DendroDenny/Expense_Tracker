from django.db import models
from django.conf import settings


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    image = models.ImageField(upload_to='profile_pictures/', blank=True)

    def __str__(self):
        return f'{self.user.username} profile'
