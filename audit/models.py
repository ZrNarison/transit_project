from django.db import models
from users.models import AppUser


class Audit(models.Model):

    ACTION_CHOICES = (
        ("CREATE", "Création"),
        ("UPDATE", "Modification"),
        ("DELETE", "Suppression"),
        ("LOGIN", "Connexion"),
        ("LOGOUT", "Déconnexion"),
    )


    utilisateur = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )

    table = models.CharField(
        max_length=100
    )

    objet_id = models.IntegerField(
        null=True,
        blank=True
    )

    ancienne_valeur = models.JSONField(
        null=True,
        blank=True
    )

    nouvelle_valeur = models.JSONField(
        null=True,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    date_action = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return f"{self.action} - {self.table}"