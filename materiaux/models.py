from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum

from users.models import AppUser


# ============================================================
# MATÉRIAUX
# ============================================================

class Materiaux(models.Model):
    libelle = models.CharField(
        max_length=100,
        verbose_name="Libellé",
    )

    unite = models.CharField(
        max_length=50,
        verbose_name="Unité",
    )

    class Meta:
        ordering = ["libelle"]
        verbose_name = "Matériau"
        verbose_name_plural = "Matériaux"

    def __str__(self):
        return f"{self.libelle} ({self.unite})"

    @property
    def total_entrees(self):
        return (
            self.entrees.aggregate(
                total=Sum("entree")
            )["total"]
            or Decimal("0")
        )

    @property
    def total_divisions(self):
        return (
            MateriauxDivision.objects.filter(
                entree__materiau=self
            ).aggregate(
                total=Sum("quantite")
            )["total"]
            or Decimal("0")
        )

    @property
    def total_sorties(self):
        return (
            MateriauxOut.objects.filter(
                division__entree__materiau=self
            ).aggregate(
                total=Sum("quantite")
            )["total"]
            or Decimal("0")
        )

    @property
    def total_retours(self):
        return (
            MateriauxRetour.objects.filter(
                sortie__division__entree__materiau=self
            ).aggregate(
                total=Sum("quantite")
            )["total"]
            or Decimal("0")
        )

    @property
    def stock_entrepot(self):
        """
        Stock encore disponible dans l'entrepôt,
        avant division vers le magasin.
        """
        return self.total_entrees - self.total_divisions

    @property
    def stock_magasin(self):
        """
        Stock magasin :

        divisions
        - sorties vers chantier
        + retours du chantier
        """
        return (
            self.total_divisions
            - self.total_sorties
            + self.total_retours
        )

    @property
    def stock_total(self):
        return self.stock_entrepot + self.stock_magasin


# ============================================================
# ENTRÉE ENTREPÔT
# ============================================================

class MateriauxEntree(models.Model):
    materiau = models.ForeignKey(
        Materiaux,
        on_delete=models.PROTECT,
        related_name="entrees",
        verbose_name="Matériau",
    )

    entree = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Quantité entrée",
    )

    date_entree = models.DateField(
        verbose_name="Date d'entrée",
    )

    destination = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Provenance",
    )

    vehicule = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Véhicule",
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="materiaux_entrees",
        verbose_name="Enregistré par",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_entree", "-id"]
        verbose_name = "Entrée matériau"
        verbose_name_plural = "Entrées matériaux"

    def clean(self):
        if self.entree is None or self.entree <= 0:
            raise ValidationError({
                "entree": (
                    "La quantité entrée doit être supérieure à zéro."
                )
            })

        if self.pk:
            total_divisions = (
                self.divisions
                .exclude(pk=self.pk)
                .aggregate(
                    total=Sum("quantite")
                )["total"]
                or Decimal("0")
            )

            if self.entree < total_divisions:
                raise ValidationError({
                    "entree": (
                        "Impossible de diminuer cette entrée à cette "
                        "quantité car une partie a déjà été divisée."
                    )
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def quantite_divisee(self):
        return (
            self.divisions.aggregate(
                total=Sum("quantite")
            )["total"]
            or Decimal("0")
        )

    @property
    def stock_entrepot(self):
        return self.entree - self.quantite_divisee

    @property
    def total_sorties(self):
        return (
            MateriauxOut.objects.filter(
                division__entree=self
            ).aggregate(
                total=Sum("quantite")
            )["total"]
            or Decimal("0")
        )

    def __str__(self):
        return (
            f"{self.materiau.libelle} - "
            f"{self.entree} "
            f"{self.materiau.unite}"
        )


# ============================================================
# DIVISION ENTREPÔT → MAGASIN
# ============================================================

class MateriauxDivision(models.Model):
    entree = models.ForeignKey(
        MateriauxEntree,
        on_delete=models.PROTECT,
        related_name="divisions",
        verbose_name="Entrée entrepôt",
    )

    destination = models.CharField(
        max_length=255,
        verbose_name="Destination / Magasin",
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Quantité divisée",
    )

    date_division = models.DateField(
        verbose_name="Date de division",
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="materiaux_divisions",
        verbose_name="Enregistré par",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_division", "-id"]
        verbose_name = "Division matériau"
        verbose_name_plural = "Divisions matériaux"

    def clean(self):
        if not self.entree_id:
            return

        if self.quantite is None or self.quantite <= 0:
            raise ValidationError({
                "quantite": (
                    "La quantité doit être supérieure à zéro."
                )
            })

        divisions_existantes = (
            self.entree.divisions
            .exclude(pk=self.pk)
            .aggregate(
                total=Sum("quantite")
            )["total"]
            or Decimal("0")
        )

        disponible = self.entree.entree - divisions_existantes

        if self.quantite > disponible:
            raise ValidationError({
                "quantite": (
                    f"Quantité insuffisante dans l'entrepôt. "
                    f"Disponible : {disponible} "
                    f"{self.entree.materiau.unite}."
                )
            })

        if self.pk:
            sorties = (
                self.sorties
                .aggregate(
                    total=Sum("quantite")
                )["total"]
                or Decimal("0")
            )

            if self.quantite < sorties:
                raise ValidationError({
                    "quantite": (
                        "Impossible de réduire cette division en dessous "
                        "des quantités déjà sorties."
                    )
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def quantite_sortie(self):
        return (
            self.sorties.aggregate(
                total=Sum("quantite")
            )["total"]
            or Decimal("0")
        )

    @property
    def quantite_retour(self):
        return (
            MateriauxRetour.objects.filter(
                sortie__division=self
            ).aggregate(
                total=Sum("quantite")
            )["total"]
            or Decimal("0")
        )

    @property
    def stock_restant(self):
        return (
            self.quantite
            - self.quantite_sortie
            + self.quantite_retour
        )

    def __str__(self):
        return (
            f"{self.entree.materiau.libelle} - "
            f"{self.destination} - "
            f"{self.quantite} "
            f"{self.entree.materiau.unite}"
        )


# ============================================================
# SORTIE MAGASIN → PROJET
# ============================================================

class MateriauxOut(models.Model):
    division = models.ForeignKey(
        MateriauxDivision,
        on_delete=models.PROTECT,
        related_name="sorties",
        verbose_name="Division",
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Quantité sortie",
    )

    date_sortie = models.DateField(
        verbose_name="Date de sortie",
    )

    destination = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Destination",
    )

    vehicule = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Véhicule",
    )

    # --------------------------------------------------------
    # NOUVELLES RELATIONS PROJET
    # --------------------------------------------------------

    projet = models.ForeignKey(
        "projet.Projet",
        on_delete=models.PROTECT,
        related_name="sorties_materiaux",
        null=True,
        blank=True,
        verbose_name="Projet",
    )

    point_projet = models.ForeignKey(
        "projet.PointProjet",
        on_delete=models.PROTECT,
        related_name="sorties_materiaux",
        null=True,
        blank=True,
        verbose_name="Point de chantier",
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="materiaux_sorties",
        verbose_name="Enregistré par",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_sortie", "-id"]
        verbose_name = "Sortie matériau"
        verbose_name_plural = "Sorties matériaux"

    def clean(self):
        if not self.division_id:
            return

        if self.quantite is None or self.quantite <= 0:
            raise ValidationError({
                "quantite": (
                    "La quantité doit être supérieure à zéro."
                )
            })

        sorties_existantes = (
            self.division.sorties
            .exclude(pk=self.pk)
            .aggregate(
                total=Sum("quantite")
            )["total"]
            or Decimal("0")
        )

        retours_existants = (
            MateriauxRetour.objects.filter(
                sortie__division=self.division
            )
            .aggregate(
                total=Sum("quantite")
            )["total"]
            or Decimal("0")
        )

        disponible = (
            self.division.quantite
            - sorties_existantes
            + retours_existants
        )

        if self.quantite > disponible:
            raise ValidationError({
                "quantite": (
                    f"Stock magasin insuffisant. "
                    f"Disponible : {disponible} "
                    f"{self.division.entree.materiau.unite}."
                )
            })

        # Le point doit appartenir au même projet.
        if self.point_projet_id and self.projet_id:
            if self.point_projet.projet_id != self.projet_id:
                raise ValidationError({
                    "point_projet": (
                        "Le point de chantier doit appartenir "
                        "au projet sélectionné."
                    )
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def quantite_transportee(self):
        return (
            self.transports.filter(
                type_transport=ActiviteTransport.MATERIAUX
            ).aggregate(
                total=Sum("quantite")
            )["total"]
            or Decimal("0")
        )

    @property
    def quantite_non_transportee(self):
        return max(
            self.quantite - self.quantite_transportee,
            Decimal("0"),
        )

    @property
    def quantite_retournee(self):
        return (
            self.retours.aggregate(
                total=Sum("quantite")
            )["total"]
            or Decimal("0")
        )

    def __str__(self):
        return (
            f"{self.division.entree.materiau.libelle} - "
            f"{self.quantite} "
            f"{self.division.entree.materiau.unite}"
        )


# ============================================================
# VÉHICULE
# ============================================================

class Vehicule(models.Model):
    immatriculation = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Immatriculation",
    )

    marque = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Marque",
    )

    modele = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Modèle",
    )

    kilometrage = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Kilométrage",
    )

    actif = models.BooleanField(
        default=True,
        verbose_name="Actif",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["immatriculation"]
        verbose_name = "Véhicule"
        verbose_name_plural = "Véhicules"

    def clean(self):
        if self.kilometrage is not None and self.kilometrage < 0:
            raise ValidationError({
                "kilometrage": (
                    "Le kilométrage ne peut pas être négatif."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def total_gasoil(self):
        return (
            self.depenses_gasoil.aggregate(
                total=Sum("total")
            )["total"]
            or Decimal("0")
        )

    @property
    def total_litres_gasoil(self):
        return (
            self.depenses_gasoil.aggregate(
                total=Sum("quantite_litre")
            )["total"]
            or Decimal("0")
        )

    @property
    def total_reparations(self):
        return (
            self.reparations.aggregate(
                total=Sum("montant_total_calcule")
            )["total"]
            or Decimal("0")
        )

    @property
    def total_depenses(self):
        return (
            self.depenses.aggregate(
                total=Sum("montant")
            )["total"]
            or Decimal("0")
        )

    @property
    def total_dockers(self):
        return (
            PaiementDocker.objects.filter(
                activite__vehicule=self
            ).aggregate(
                total=Sum("montant")
            )["total"]
            or Decimal("0")
        )

    @property
    def cout_total(self):
        return (
            self.total_gasoil
            + self.total_reparations
            + self.total_depenses
            + self.total_dockers
        )

    def __str__(self):
        return self.immatriculation


# ============================================================
# CATÉGORIE DE DÉPENSE
# ============================================================

class CategorieDepense(models.Model):
    nom = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nom",
    )

    description = models.TextField(
        blank=True,
        verbose_name="Description",
    )

    actif = models.BooleanField(
        default=True,
        verbose_name="Actif",
    )

    class Meta:
        ordering = ["nom"]
        verbose_name = "Catégorie de dépense"
        verbose_name_plural = "Catégories de dépenses"

    def __str__(self):
        return self.nom


# ============================================================
# ACTIVITÉ DE TRANSPORT
# ============================================================

class ActiviteTransport(models.Model):

    PERSONNEL = "PERSONNEL"
    MATERIELS = "MATERIELS"
    MATERIAUX = "MATERIAUX"

    TYPE_TRANSPORT_CHOICES = [
        (PERSONNEL, "Personnel"),
        (MATERIELS, "Matériels"),
        (MATERIAUX, "Matériaux"),
    ]

    date_activite = models.DateField(
        verbose_name="Date",
    )

    vehicule = models.ForeignKey(
        Vehicule,
        on_delete=models.PROTECT,
        related_name="activites_transport",
        verbose_name="Véhicule",
    )

    # Ancien champ conservé pour compatibilité
    conducteur = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Conducteur",
    )

    # Nouveau lien vers Personnel
    chauffeur_personnel = models.ForeignKey(
        "personnel.Personnel",
        on_delete=models.PROTECT,
        related_name="activites_transport",
        null=True,
        blank=True,
        verbose_name="Chauffeur",
    )

    mission = models.CharField(
        max_length=255,
        verbose_name="Mission",
    )

    lieu_depart = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Lieu de départ",
    )

    destination = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Destination",
    )

    type_transport = models.CharField(
        max_length=20,
        choices=TYPE_TRANSPORT_CHOICES,
        default=MATERIAUX,
        verbose_name="Type de transport",
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Quantité",
    )

    # --------------------------------------------------------
    # PROJET
    # --------------------------------------------------------

    projet = models.ForeignKey(
        "projet.Projet",
        on_delete=models.PROTECT,
        related_name="activites_transport",
        null=True,
        blank=True,
        verbose_name="Projet",
    )

    point_projet = models.ForeignKey(
        "projet.PointProjet",
        on_delete=models.PROTECT,
        related_name="activites_transport",
        null=True,
        blank=True,
        verbose_name="Point de chantier",
    )

    # --------------------------------------------------------
    # MATÉRIAU TRANSPORTÉ
    # --------------------------------------------------------

    sortie_materiau = models.ForeignKey(
        "materiaux.MateriauxOut",
        on_delete=models.PROTECT,
        related_name="transports",
        null=True,
        blank=True,
        verbose_name="Sortie matériau",
    )

    # --------------------------------------------------------
    # KILOMÉTRAGE
    # --------------------------------------------------------

    kilometrage_depart = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Km départ",
    )

    kilometrage_arrivee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Km arrivée",
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="activites_transport_enregistrees",
        verbose_name="Enregistré par",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_activite", "-id"]
        verbose_name = "Activité de transport"
        verbose_name_plural = "Activités de transport"

    def clean(self):
        errors = {}

        if self.quantite is not None and self.quantite < 0:
            errors["quantite"] = (
                "La quantité ne peut pas être négative."
            )

        if (
            self.kilometrage_depart is not None
            and self.kilometrage_depart < 0
        ):
            errors["kilometrage_depart"] = (
                "Le kilométrage de départ ne peut pas être négatif."
            )

        if (
            self.kilometrage_arrivee is not None
            and self.kilometrage_arrivee < 0
        ):
            errors["kilometrage_arrivee"] = (
                "Le kilométrage d'arrivée ne peut pas être négatif."
            )

        if (
            self.kilometrage_arrivee is not None
            and self.kilometrage_depart is not None
            and self.kilometrage_arrivee < self.kilometrage_depart
        ):
            errors["kilometrage_arrivee"] = (
                "Le kilométrage d'arrivée doit être supérieur "
                "ou égal au kilométrage de départ."
            )

        # ----------------------------------------------------
        # Un transport de matériaux doit être lié à une sortie.
        # ----------------------------------------------------

        if (
            self.type_transport == self.MATERIAUX
            and self.sortie_materiau_id
        ):
            sortie = self.sortie_materiau

            transports_existants = (
                sortie.transports
                .exclude(pk=self.pk)
                .filter(
                    type_transport=self.MATERIAUX
                )
                .aggregate(
                    total=Sum("quantite")
                )["total"]
                or Decimal("0")
            )

            disponible = (
                sortie.quantite
                - transports_existants
            )

            if self.quantite > disponible:
                errors["quantite"] = (
                    f"Quantité trop élevée. "
                    f"Disponible pour transport : "
                    f"{disponible} "
                    f"{sortie.division.entree.materiau.unite}."
                )

        # ----------------------------------------------------
        # Cohérence Projet / Point
        # ----------------------------------------------------

        if self.point_projet_id and self.projet_id:
            if self.point_projet.projet_id != self.projet_id:
                errors["point_projet"] = (
                    "Le point sélectionné n'appartient pas "
                    "au projet sélectionné."
                )

        # ----------------------------------------------------
        # Cohérence Projet / Sortie matériau
        # ----------------------------------------------------

        if self.sortie_materiau_id and self.projet_id:
            if (
                self.sortie_materiau.projet_id
                and self.sortie_materiau.projet_id != self.projet_id
            ):
                errors["sortie_materiau"] = (
                    "La sortie de matériau appartient à un autre projet."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def distance_km(self):
        return max(
            (
                self.kilometrage_arrivee
                - self.kilometrage_depart
            ),
            Decimal("0"),
        )

    @property
    def materiau(self):
        if self.sortie_materiau_id:
            return self.sortie_materiau.division.entree.materiau
        return None

    def __str__(self):
        designation = (
            self.mission
            or self.get_type_transport_display()
        )

        return (
            f"{self.date_activite} - "
            f"{self.vehicule.immatriculation} - "
            f"{designation}"
        )


# ============================================================
# RÉCEPTION DES MATÉRIAUX AU POINT DE CHANTIER
# ============================================================

class ReceptionMateriau(models.Model):

    transport = models.ForeignKey(
        ActiviteTransport,
        on_delete=models.PROTECT,
        related_name="receptions_materiaux",
        verbose_name="Transport",
    )

    projet = models.ForeignKey(
        "projet.Projet",
        on_delete=models.PROTECT,
        related_name="receptions_materiaux",
        verbose_name="Projet",
    )

    point = models.ForeignKey(
        "projet.PointProjet",
        on_delete=models.PROTECT,
        related_name="receptions_materiaux",
        verbose_name="Point de chantier",
    )

    quantite_recue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Quantité reçue",
    )

    date_reception = models.DateField(
        verbose_name="Date de réception",
    )

    responsable = models.ForeignKey(
        "personnel.Personnel",
        on_delete=models.PROTECT,
        related_name="receptions_materiaux",
        verbose_name="Responsable",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_reception", "-id"]
        verbose_name = "Réception de matériau"
        verbose_name_plural = "Réceptions de matériaux"

    def clean(self):
        errors = {}

        if self.quantite_recue is None or self.quantite_recue <= 0:
            errors["quantite_recue"] = (
                "La quantité reçue doit être supérieure à zéro."
            )

        if self.transport_id:
            transport = self.transport

            if transport.type_transport != ActiviteTransport.MATERIAUX:
                errors["transport"] = (
                    "Le transport sélectionné ne transporte pas "
                    "des matériaux."
                )

            receptions_existantes = (
                transport.receptions_materiaux
                .exclude(pk=self.pk)
                .aggregate(
                    total=Sum("quantite_recue")
                )["total"]
                or Decimal("0")
            )

            disponible = (
                transport.quantite
                - receptions_existantes
            )

            if (
                self.quantite_recue is not None
                and self.quantite_recue > disponible
            ):
                errors["quantite_recue"] = (
                    f"Quantité reçue supérieure à la quantité "
                    f"transportée. Disponible : {disponible}."
                )

        if self.projet_id and self.point_id:
            if self.point.projet_id != self.projet_id:
                errors["point"] = (
                    "Le point n'appartient pas à ce projet."
                )

        if self.transport_id and self.projet_id:
            if (
                self.transport.projet_id
                and self.transport.projet_id != self.projet_id
            ):
                errors["projet"] = (
                    "Le transport appartient à un autre projet."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def quantite_utilisee(self):
        return (
            self.utilisations.aggregate(
                total=Sum("quantite_utilisee")
            )["total"]
            or Decimal("0")
        )

    @property
    def quantite_retournee(self):
        return (
            self.retours.aggregate(
                total=Sum("quantite")
            )["total"]
            or Decimal("0")
        )

    @property
    def quantite_restante(self):
        return (
            self.quantite_recue
            - self.quantite_utilisee
            - self.quantite_retournee
        )

    def __str__(self):
        return (
            f"{self.point} - "
            f"{self.quantite_recue}"
        )


# ============================================================
# UTILISATION DES MATÉRIAUX SUR LE CHANTIER
# ============================================================

class UtilisationMateriau(models.Model):

    reception = models.ForeignKey(
        ReceptionMateriau,
        on_delete=models.PROTECT,
        related_name="utilisations",
        verbose_name="Réception",
    )

    quantite_utilisee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Quantité utilisée",
    )

    date_utilisation = models.DateField(
        verbose_name="Date",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="utilisations_materiaux",
        verbose_name="Enregistré par",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_utilisation", "-id"]
        verbose_name = "Utilisation de matériau"
        verbose_name_plural = "Utilisations de matériaux"

    def clean(self):
        if not self.reception_id:
            return

        if (
            self.quantite_utilisee is None
            or self.quantite_utilisee <= 0
        ):
            raise ValidationError({
                "quantite_utilisee": (
                    "La quantité utilisée doit être "
                    "supérieure à zéro."
                )
            })

        utilisations_existantes = (
            self.reception.utilisations
            .exclude(pk=self.pk)
            .aggregate(
                total=Sum("quantite_utilisee")
            )["total"]
            or Decimal("0")
        )

        retours_existants = (
            self.reception.retours
            .aggregate(
                total=Sum("quantite")
            )["total"]
            or Decimal("0")
        )

        disponible = (
            self.reception.quantite_recue
            - utilisations_existantes
            - retours_existants
        )

        if self.quantite_utilisee > disponible:
            raise ValidationError({
                "quantite_utilisee": (
                    f"Quantité insuffisante sur le chantier. "
                    f"Disponible : {disponible}."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.reception} - "
            f"{self.quantite_utilisee}"
        )


# ============================================================
# RETOUR DU RELIQUAT AU MAGASIN
# ============================================================

class MateriauxRetour(models.Model):

    sortie = models.ForeignKey(
        MateriauxOut,
        on_delete=models.PROTECT,
        related_name="retours",
        verbose_name="Sortie magasin",
    )

    reception = models.ForeignKey(
        ReceptionMateriau,
        on_delete=models.PROTECT,
        related_name="retours",
        null=True,
        blank=True,
        verbose_name="Réception chantier",
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Quantité retournée",
    )

    date_retour = models.DateField(
        verbose_name="Date du retour",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="retours_materiaux",
        verbose_name="Enregistré par",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_retour", "-id"]
        verbose_name = "Retour matériau"
        verbose_name_plural = "Retours matériaux"

    def clean(self):
        errors = {}

        if self.quantite is None or self.quantite <= 0:
            errors["quantite"] = (
                "La quantité retournée doit être supérieure à zéro."
            )

        if self.sortie_id:
            retours_existants = (
                self.sortie.retours
                .exclude(pk=self.pk)
                .aggregate(
                    total=Sum("quantite")
                )["total"]
                or Decimal("0")
            )

            disponible = (
                self.sortie.quantite
                - retours_existants
            )

            if (
                self.quantite is not None
                and self.quantite > disponible
            ):
                errors["quantite"] = (
                    f"Quantité retournée trop élevée. "
                    f"Maximum disponible : {disponible}."
                )

        # Si le retour est lié à une réception,
        # le retour ne peut pas dépasser son reliquat.
        if self.reception_id:
            if (
                self.reception.transport_id
                and self.sortie_id
                and self.reception.transport.sortie_materiau_id
                and self.reception.transport.sortie_materiau_id
                != self.sortie_id
            ):
                errors["reception"] = (
                    "La réception ne correspond pas "
                    "à la sortie magasin."
                )

            retours_reception = (
                self.reception.retours
                .exclude(pk=self.pk)
                .aggregate(
                    total=Sum("quantite")
                )["total"]
                or Decimal("0")
            )

            utilisations = (
                self.reception.utilisations
                .aggregate(
                    total=Sum("quantite_utilisee")
                )["total"]
                or Decimal("0")
            )

            disponible_reception = (
                self.reception.quantite_recue
                - utilisations
                - retours_reception
            )

            if (
                self.quantite is not None
                and self.quantite > disponible_reception
            ):
                errors["quantite"] = (
                    f"Le reliquat disponible au point est "
                    f"de {disponible_reception}."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Retour - "
            f"{self.sortie.division.entree.materiau.libelle} - "
            f"{self.quantite}"
        )


# ============================================================
# PAIEMENT DOCKER
# ============================================================

class PaiementDocker(models.Model):

    date_activite = models.DateField(
        verbose_name="Date",
    )

    activite = models.ForeignKey(
        ActiviteTransport,
        on_delete=models.PROTECT,
        related_name="paiements_dockers",
        verbose_name="Activité",
    )

    # Projet directement accessible pour les rapports.
    projet = models.ForeignKey(
        "projet.Projet",
        on_delete=models.PROTECT,
        related_name="paiements_dockers",
        null=True,
        blank=True,
        verbose_name="Projet",
    )

    montant = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Montant",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="paiements_dockers",
        verbose_name="Enregistré par",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_creation", "-id"]
        verbose_name = "Paiement docker"
        verbose_name_plural = "Paiements dockers"

    def clean(self):
        errors = {}

        if self.montant is None or self.montant <= 0:
            errors["montant"] = (
                "Le montant doit être supérieur à zéro."
            )

        if self.activite_id and self.projet_id:
            if (
                self.activite.projet_id
                and self.activite.projet_id != self.projet_id
            ):
                errors["projet"] = (
                    "Le projet ne correspond pas "
                    "au projet de l'activité."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Si le projet n'est pas renseigné mais que
        # l'activité est liée à un projet, on le récupère.
        if (
            not self.projet_id
            and self.activite_id
            and self.activite.projet_id
        ):
            self.projet_id = self.activite.projet_id

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.activite.vehicule.immatriculation} - "
            f"{self.montant}"
        )


# ============================================================
# DÉPENSE GÉNÉRALE
# ============================================================

class Depense(models.Model):

    date_depense = models.DateField(
        verbose_name="Date",
    )

    designation = models.CharField(
        max_length=255,
        verbose_name="Désignation",
    )

    categorie = models.ForeignKey(
        CategorieDepense,
        on_delete=models.PROTECT,
        related_name="depenses",
        blank=True,
        null=True,
        verbose_name="Catégorie",
    )

    vehicule = models.ForeignKey(
        Vehicule,
        on_delete=models.PROTECT,
        related_name="depenses",
        blank=True,
        null=True,
        verbose_name="Véhicule",
    )

    projet = models.ForeignKey(
        "projet.Projet",
        on_delete=models.PROTECT,
        related_name="depenses",
        blank=True,
        null=True,
        verbose_name="Projet",
    )

    montant = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Montant",
    )

    localisation = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Localisation",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="depenses_materiaux",
        verbose_name="Enregistré par",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_depense", "-id"]
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"

    def clean(self):
        if self.montant is None or self.montant <= 0:
            raise ValidationError({
                "montant": (
                    "Le montant doit être supérieur à zéro."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.designation} - {self.montant}"


# ============================================================
# GASOIL
# ============================================================

class DepenseGasoil(models.Model):

    date_gasoil = models.DateField(
        verbose_name="Date",
    )

    vehicule = models.ForeignKey(
        Vehicule,
        on_delete=models.PROTECT,
        related_name="depenses_gasoil",
        verbose_name="Véhicule",
    )

    projet = models.ForeignKey(
        "projet.Projet",
        on_delete=models.PROTECT,
        related_name="depenses_gasoil",
        blank=True,
        null=True,
        verbose_name="Projet",
    )

    quantite_litre = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Quantité (litres)",
    )

    prix_unitaire = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Prix / litre",
    )

    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        editable=False,
        verbose_name="Total",
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="depenses_gasoil",
        verbose_name="Enregistré par",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_gasoil", "-id"]
        verbose_name = "Dépense gasoil"
        verbose_name_plural = "Dépenses gasoil"

    def clean(self):
        errors = {}

        if (
            self.quantite_litre is None
            or self.quantite_litre <= 0
        ):
            errors["quantite_litre"] = (
                "La quantité de gasoil doit être "
                "supérieure à zéro."
            )

        if (
            self.prix_unitaire is None
            or self.prix_unitaire < 0
        ):
            errors["prix_unitaire"] = (
                "Le prix unitaire ne peut pas être négatif."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.total = (
            self.quantite_litre
            * self.prix_unitaire
        )

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.vehicule.immatriculation} - "
            f"{self.quantite_litre} L - "
            f"{self.total}"
        )


# ============================================================
# RÉPARATION VÉHICULE
# ============================================================

class ReparationVehicule(models.Model):

    REPARATION = "REPARATION"
    CHANGEMENT = "CHANGEMENT"

    TYPE_REPARATION_CHOICES = [
        (REPARATION, "Réparation"),
        (CHANGEMENT, "Changement"),
    ]

    date_reparation = models.DateField(
        verbose_name="Date",
    )

    vehicule = models.ForeignKey(
        Vehicule,
        on_delete=models.PROTECT,
        related_name="reparations",
        verbose_name="Véhicule",
    )

    # Ancien champ conservé.
    chauffeur = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Chauffeur",
    )

    # Nouveau lien vers Personnel.
    chauffeur_personnel = models.ForeignKey(
        "personnel.Personnel",
        on_delete=models.PROTECT,
        related_name="reparations_vehicules",
        null=True,
        blank=True,
        verbose_name="Chauffeur",
    )

    projet = models.ForeignKey(
        "projet.Projet",
        on_delete=models.PROTECT,
        related_name="reparations_vehicules",
        null=True,
        blank=True,
        verbose_name="Projet",
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
        default=Decimal("1"),
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
        default=Decimal("0"),
        verbose_name="Prix unitaire",
    )

    montant_main_oeuvre = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Main d'œuvre",
    )

    # Ancien champ conservé pour compatibilité.
    Cout = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Coût historique",
    )

    # Ancien champ conservé pour compatibilité.
    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        editable=False,
        verbose_name="Total pièce historique",
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="reparations_vehicules",
        verbose_name="Enregistré par",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
    )

    date_modification = models.DateTimeField(
        auto_now=True,
    )

    photo_piece_remplacee = models.ImageField(
        upload_to="reparations/pieces_remplacees/",
        blank=True,
        null=True,
        verbose_name="Photo pièce remplacée",
    )

    photo_piece_remplacante = models.ImageField(
        upload_to="reparations/pieces_remplacantes/",
        blank=True,
        null=True,
        verbose_name="Photo pièce remplacée par",
    )

    class Meta:
        ordering = ["-date_reparation", "-id"]
        verbose_name = "Réparation véhicule"
        verbose_name_plural = "Réparations véhicules"

    @property
    def montant_piece(self):
        return (
            (self.quantite or Decimal("0"))
            * (self.prix_unitaire or Decimal("0"))
        )

    @property
    def montant_total_calcule(self):
        return (
            self.montant_piece
            + (
                self.montant_main_oeuvre
                or Decimal("0")
            )
        )

    @property
    def montant_total(self):
        return self.montant_total_calcule

    def clean(self):
        errors = {}

        if self.quantite is None or self.quantite <= 0:
            errors["quantite"] = (
                "La quantité doit être supérieure à zéro."
            )

        if (
            self.prix_unitaire is None
            or self.prix_unitaire < 0
        ):
            errors["prix_unitaire"] = (
                "Le prix unitaire ne peut pas être négatif."
            )

        if (
            self.montant_main_oeuvre is None
            or self.montant_main_oeuvre < 0
        ):
            errors["montant_main_oeuvre"] = (
                "La main d'œuvre ne peut pas être négative."
            )

        if self.Cout is not None and self.Cout < 0:
            errors["Cout"] = (
                "Le coût ne peut pas être négatif."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.total = self.montant_piece

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.vehicule.immatriculation} - "
            f"{self.designation} - "
            f"{self.montant_total_calcule}"
        )