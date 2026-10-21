from django.db import models


class JournalSauvegarde(models.Model):
    ACTION_CHOICES = [
        ("EXPORT", "Exportation"),
        ("PREVIEW", "Validation import"),
        ("IMPORT", "Importation"),
        ("ERROR", "Erreur"),
    ]

    utilisateur_id = models.CharField(max_length=100, blank=True, default="")
    utilisateur = models.CharField(max_length=150, blank=True, default="")
    source_session = models.CharField(max_length=30, blank=True, default="")
    action = models.CharField(max_length=12, choices=ACTION_CHOICES)
    statut = models.CharField(max_length=20, default="OK")
    fichier = models.CharField(max_length=255, blank=True, default="")
    empreinte_sha256 = models.CharField(max_length=64, blank=True, default="")
    details = models.TextField(blank=True, default="")
    date_operation = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-date_operation"]
        verbose_name = "Journal de sauvegarde"
        verbose_name_plural = "Journal des sauvegardes"

    def __str__(self):
        return f"{self.date_operation:%Y-%m-%d %H:%M} - {self.action} - {self.statut}"
