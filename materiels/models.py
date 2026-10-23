from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Materiels(models.Model):
    nom = models.CharField(max_length=100)
    typeMat = models.CharField(max_length=100)
    catMat = models.CharField(max_length=100)
    photo = models.ImageField(
        upload_to="images/materiaux/",
        blank=True,
        null=True,
    )
    stock_initial = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
    )

    def stock_sorti(self):
        return sum(
            (sortie.Nb_MatSort or Decimal("0") for sortie in self.sorties.all()),
            Decimal("0"),
        )

    def stock_entre(self):
        return sum(
            (
                entree.Nb_Entre or Decimal("0")
                for sortie in self.sorties.all()
                for entree in sortie.entrees.all()
            ),
            Decimal("0"),
        )

    def stock_restant(self):
        return self.stock_initial - self.stock_sorti() + self.stock_entre()

    def __str__(self):
        return f"{self.nom} | {self.typeMat} | {self.catMat}"



class Vehicule(models.Model):
    TYPE_VEHICULE_CHOICES = [
        ("ROUTIER", "Véhicule routier"),
        ("ENGIN", "Engin de chantier"),
    ]

    vehicule = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="N° Immatriculation",
        help_text="Exemple : 54254 WWT ou 5474 TG.",
    )

    type_vehicule = models.CharField(
        max_length=20,
        choices=TYPE_VEHICULE_CHOICES,
        default="ROUTIER",
        verbose_name="Type",
    )

    date_debut = models.DateField(
        verbose_name="Date de début",
    )

    date_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de fin",
    )

    kilometrage_initial = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Kilométrage initial",
    )

    kilometrage_final = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Kilométrage final",
    )

    consommation_km_litre = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Consommation (km/litre)",
    )

    heures_initiales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Heures initiales",
    )

    heures_finales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Heures finales",
    )

    consommation_heure_litre = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Consommation (heures/litre)",
    )

    actif = models.BooleanField(
        default=True,
        verbose_name="Actif",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière modification",
    )

    class Meta:
        ordering = ["vehicule"]
        verbose_name = "Véhicule"
        verbose_name_plural = "Véhicules"

    def __str__(self):
        return self.vehicule

    def clean(self):
        super().clean()

        erreurs = {}

        # Vérification des dates.
        if self.date_debut and self.date_fin:
            if self.date_fin < self.date_debut:
                erreurs["date_fin"] = (
                    "La date de fin doit être postérieure "
                    "ou égale à la date de début."
                )

        # Véhicule routier : validation du kilométrage.
        if self.type_vehicule == "ROUTIER":
            champs_km = {
                "kilometrage_initial": self.kilometrage_initial,
                "kilometrage_final": self.kilometrage_final,
                "consommation_km_litre": self.consommation_km_litre,
            }

            for nom, valeur in champs_km.items():
                if valeur is not None and valeur < 0:
                    erreurs[nom] = "Cette valeur ne peut pas être négative."

            if (
                self.kilometrage_initial is not None
                and self.kilometrage_final is not None
                and self.kilometrage_final < self.kilometrage_initial
            ):
                erreurs["kilometrage_final"] = (
                    "Le kilométrage final doit être supérieur "
                    "ou égal au kilométrage initial."
                )

        # Engin de chantier : validation des heures.
        elif self.type_vehicule == "ENGIN":
            champs_heures = {
                "heures_initiales": self.heures_initiales,
                "heures_finales": self.heures_finales,
                "consommation_heure_litre": self.consommation_heure_litre,
            }

            for nom, valeur in champs_heures.items():
                if valeur is not None and valeur < 0:
                    erreurs[nom] = "Cette valeur ne peut pas être négative."

            if (
                self.heures_initiales is not None
                and self.heures_finales is not None
                and self.heures_finales < self.heures_initiales
            ):
                erreurs["heures_finales"] = (
                    "Les heures finales doivent être supérieures "
                    "ou égales aux heures initiales."
                )

        if erreurs:
            raise ValidationError(erreurs)

    def save(self, *args, **kwargs):
        """
        Enregistre l'immatriculation saisie par l'utilisateur.
        Ne génère jamais de références VEH-001 ou ENG-001.
        """

        if self.vehicule:
            self.vehicule = self.vehicule.strip().upper()

        # Un véhicule routier utilise les kilomètres.
        # Les champs horaires ne sont donc pas utilisés.
        if self.type_vehicule == "ROUTIER":
            self.heures_initiales = Decimal("0.00")
            self.heures_finales = Decimal("0.00")
            self.consommation_heure_litre = Decimal("0.00")

        # Un engin utilise les heures de fonctionnement.
        # Les champs kilométriques ne sont donc pas utilisés.
        elif self.type_vehicule == "ENGIN":
            self.kilometrage_initial = Decimal("0.00")
            self.kilometrage_final = Decimal("0.00")
            self.consommation_km_litre = Decimal("0.00")

        # Garantit la persistance des champs normalisés, même si
        # save(update_fields=...) est utilisé ailleurs dans le projet.
        update_fields = kwargs.get("update_fields")

        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {
                "vehicule",
                "kilometrage_initial",
                "kilometrage_final",
                "consommation_km_litre",
                "heures_initiales",
                "heures_finales",
                "consommation_heure_litre",
            }

        super().save(*args, **kwargs)

    @property
    def acces_actif(self):
        """Indique si le véhicule est actif et dans sa période d'affectation."""
        if not self.actif:
            return False

        if self.date_fin and self.date_fin < timezone.localdate():
            return False

        return True

    @property
    def periode_terminee(self):
        """Indique si la période d'affectation est terminée."""
        return bool(
            self.date_fin
            and self.date_fin < timezone.localdate()
        )

    @property
    def kilometres_parcourus(self):
        """Calcule les kilomètres parcourus pour un véhicule routier."""
        if self.type_vehicule != "ROUTIER":
            return Decimal("0.00")

        initial = self.kilometrage_initial or Decimal("0.00")
        final = self.kilometrage_final or Decimal("0.00")

        return max(final - initial, Decimal("0.00"))

    @property
    def heures_travail(self):
        """Calcule les heures de fonctionnement d'un engin."""
        if self.type_vehicule != "ENGIN":
            return Decimal("0.00")

        initial = self.heures_initiales or Decimal("0.00")
        final = self.heures_finales or Decimal("0.00")

        return max(final - initial, Decimal("0.00"))

    @property
    def carburant_estime(self):
        """Estime le carburant consommé selon le type de véhicule."""
        if self.type_vehicule == "ROUTIER":
            consommation = self.consommation_km_litre or Decimal("0.00")

            if consommation <= 0:
                return Decimal("0.00")

            return self.kilometres_parcourus / consommation

        consommation = self.consommation_heure_litre or Decimal("0.00")

        if consommation <= 0:
            return Decimal("0.00")

        return self.heures_travail / consommation

    @property
    def unite_travail(self):
        """Retourne l'unité de suivi adaptée au véhicule."""
        return "heures" if self.type_vehicule == "ENGIN" else "km"

    @property
    def travail_total(self):
        """Retourne le total de travail selon le type de véhicule."""
        if self.type_vehicule == "ENGIN":
            return self.heures_travail

        return self.kilometres_parcourus


class ReparationVehicule(models.Model):
    """Réparation liée à un véhicule ou engin du parc GALAXY."""

    REPARATION = "REPARATION"
    CHANGEMENT = "CHANGEMENT"

    TYPE_REPARATION_CHOICES = [
        (REPARATION, "Réparation"),
        (CHANGEMENT, "Changement"),
    ]

    date_reparation = models.DateField(
        verbose_name="Date de réparation",
    )

    vehicule = models.ForeignKey(
        "materiels.Vehicule",
        on_delete=models.PROTECT,
        related_name="reparations",
        verbose_name="Véhicule / Engin du chantier",
    )

    chauffeur = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Chauffeur (texte historique)",
    )
    designation = models.CharField(
        max_length=255,
        verbose_name="Désignation",
    )
    type_reparation = models.CharField(
        max_length=20,
        choices=TYPE_REPARATION_CHOICES,
        default=REPARATION,
        verbose_name="Type",
    )
    garage = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Garage",
    )
    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("1.00"),
        verbose_name="Quantité",
    )
    unite = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Unité",
    )
    prix_unitaire = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Prix unitaire",
    )
    montant_main_oeuvre = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Main-d'œuvre",
    )
    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
        verbose_name="Total de la réparation",
    )
    enregistre_par = models.ForeignKey(
        "users.AppUser",
        on_delete=models.PROTECT,
        related_name="reparations_vehicules_enregistrees_materiels",
        null=True,
        blank=True,
        verbose_name="Enregistré par",
    )
    photo_piece_remplacee = models.ImageField(
        upload_to="reparations/pieces_remplacees/",
        blank=True,
        null=True,
        verbose_name="Photo de la pièce remplacée",
    )
    photo_piece_remplacante = models.ImageField(
        upload_to="reparations/pieces_remplacantes/",
        blank=True,
        null=True,
        verbose_name="Photo de la pièce de remplacement",
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_reparation", "-id"]
        verbose_name = "Réparation de véhicule"
        verbose_name_plural = "Réparations des véhicules"

    @property
    def montant_piece(self):
        return (self.quantite or Decimal("0.00")) * (
            self.prix_unitaire or Decimal("0.00")
        )

    @property
    def montant_total_calcule(self):
        return self.montant_piece + (self.montant_main_oeuvre or Decimal("0.00"))

    @property
    def montant_total(self):
        return self.montant_total_calcule

    def clean(self):
        super().clean()
        errors = {}

        if self.quantite is not None and self.quantite <= 0:
            errors["quantite"] = "La quantité doit être supérieure à zéro."

        if self.prix_unitaire is not None and self.prix_unitaire < 0:
            errors["prix_unitaire"] = "Le prix unitaire ne peut pas être négatif."

        if self.montant_main_oeuvre is not None and self.montant_main_oeuvre < 0:
            errors["montant_main_oeuvre"] = "La main-d'œuvre ne peut pas être négative."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.total = self.montant_total_calcule
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.designation} - {self.vehicule} - " f"{self.date_reparation}"


class H_Materiels(models.Model):
    nom = models.CharField(max_length=100)
    typeMat = models.CharField(max_length=100)
    catMat = models.CharField(max_length=100)
    photo = models.ImageField(
        upload_to="images/materiaux/",
        blank=True,
        null=True,
    )
    stock_initial = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
    )

    def stock_sorti(self):
        return sum(
            (sortie.Nb_MatSort or Decimal("0") for sortie in self.sorties.all()),
            Decimal("0"),
        )

    def stock_entre(self):
        return sum(
            (
                entree.Nb_Entre or Decimal("0")
                for sortie in self.sorties.all()
                for entree in sortie.entrees.all()
            ),
            Decimal("0"),
        )

    def stock_restant(self):
        return self.stock_initial - self.stock_sorti() + self.stock_entre()

    def __str__(self):
        return f"{self.nom} | {self.typeMat} | {self.catMat}"
