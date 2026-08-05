from django.db import models


class Log(models.Model):

    LEVEL_CHOICES = (
        ("INFO", "Information"),
        ("WARNING", "Avertissement"),
        ("ERROR", "Erreur"),
        ("CRITICAL", "Critique"),
    )


    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default="INFO"
    )


    message = models.TextField()


    module = models.CharField(
        max_length=100,
        blank=True
    )


    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )


    date_log = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return f"{self.level} - {self.message}"