from django.db import models
from personnel.models import Personnel


class AppUser(models.Model):

    ROLE_CHOICES = (
        ("Admin", "Administrateur"),
        ("Superviseur", "Super Viseur"),
        ("User", "Utilisateur"),
    )


    personnel = models.OneToOneField(
        Personnel,
        on_delete=models.CASCADE,
        related_name="compte",
        null=True,
        blank=True
    )


    username = models.CharField(
        max_length=100,
        unique=True
    )


    email = models.EmailField(
        max_length=100,
        unique=True
    )


    password = models.CharField(
        max_length=255
    )


    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="User"
    )


    photo = models.ImageField(
        upload_to="images/users/",
        blank=True,
        null=True
    )


    date_creation = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return self.username