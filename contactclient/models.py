from django.db import models
from clients.models import Client


class ContactClient(models.Model):

    client = models.ForeignKey(Client, on_delete=models.CASCADE)

    numero = models.CharField(
        max_length=20
    )

    titulaire = models.CharField(
        max_length=100,
        blank=True
    )

    principal = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["numero"]

    def __str__(self):
        return f"{self.client} - {self.numero}"