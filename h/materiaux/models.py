from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from users.models import AppUser


# ==========================================================
# MATÉRIAUX
# ==========================================================

class Materiaux(models.Model):
    libelle = models.CharField(
        max_length=100
    )

    unite = models.CharField(
        max_length=50
    )

    def __str__(self):
        return f"{self.libelle} ({self.unite})"

    # ------------------------------------------------------
    # CALCULS GLOBAUX DU MATÉRIAU
    # ------------------------------------------------------

    @property
    def total_entrees(self):
        return sum(
            (
                entree.entree
                for entree in self.entrees.all()
            ),
            Decimal("0")
        )

    @property
    def total_divisions(self):
        return sum(
            (
                division.quantite
                for entree in self.entrees.all()
                for division in entree.divisions.all()
            ),
            Decimal("0")
        )

    @property
    def total_sorties(self):
        return sum(
            (
                sortie.quantite
                for entree in self.entrees.all()
                for division in entree.divisions.all()
                for sortie in division.sorties.all()
            ),
            Decimal("0")
        )

    @property
    def stock_entrepot(self):
        return (
            self.total_entrees
            - self.total_divisions
        )

    @property
    def stock_magasin(self):
        return (
            self.total_divisions
            - self.total_sorties
        )

    @property
    def stock_total(self):
        return (
            self.stock_entrepot
            + self.stock_magasin
        )

    class Meta:
        ordering = ["libelle"]
        verbose_name = "Matériau"
        verbose_name_plural = "Matériaux"


# ==========================================================
# ENTRÉE ENTREPÔT
# ==========================================================

class MateriauxEntree(models.Model):
    """
    Entrée d'un matériau dans l'entrepôt.
    """

    materiau = models.ForeignKey(
        Materiaux,
        on_delete=models.PROTECT,
        related_name="entrees",
        verbose_name="Matériau"
    )

    entree = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Quantité entrée"
    )

    date_entree = models.DateField(
        verbose_name="Date d'entrée"
    )

    destination = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Provenance"
    )

    vehicule = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Véhicule"
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="materiaux_entrees",
        verbose_name="Enregistreur"
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    # ------------------------------------------------------
    # CALCULS
    # ------------------------------------------------------

    @property
    def quantite_divisee(self):
        return sum(
            (
                division.quantite
                for division in self.divisions.all()
            ),
            Decimal("0")
        )

    @property
    def stock_entrepot(self):
        return (
            self.entree
            - self.quantite_divisee
        )

    @property
    def total_sorties(self):
        return sum(
            (
                sortie.quantite
                for division in self.divisions.all()
                for sortie in division.sorties.all()
            ),
            Decimal("0")
        )

    def __str__(self):
        return (
            f"{self.materiau.libelle} - "
            f"{self.entree} {self.materiau.unite}"
        )

    class Meta:
        ordering = ["-date_entree", "-id"]
        verbose_name = "Entrée entrepôt"
        verbose_name_plural = "Entrées entrepôt"


# ==========================================================
# DIVISION ENTREPÔT → MAGASIN
# ==========================================================

class MateriauxDivision(models.Model):
    """
    Division d'une entrée entrepôt vers un magasin,
    chantier ou autre destination.
    """

    entree = models.ForeignKey(
        MateriauxEntree,
        on_delete=models.PROTECT,
        related_name="divisions",
        verbose_name="Entrée entrepôt"
    )

    destination = models.CharField(
        max_length=100,
        verbose_name="Magasin / Chantier"
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Quantité divisée"
    )

    date_division = models.DateField(
        verbose_name="Date de division"
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="materiaux_divisions",
        verbose_name="Enregistreur"
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    def clean(self):
        if not self.entree_id:
            return

        total_divisions = (
            MateriauxDivision.objects
            .filter(
                entree=self.entree
            )
            .exclude(
                pk=self.pk
            )
            .aggregate(
                total=models.Sum("quantite")
            )["total"]
            or Decimal("0")
        )

        stock_disponible = (
            self.entree.entree
            - total_divisions
        )

        if self.quantite <= 0:
            raise ValidationError({
                "quantite":
                    "La quantité doit être supérieure à zéro."
            })

        if self.quantite > stock_disponible:
            raise ValidationError({
                "quantite": (
                    "Stock entrepôt insuffisant. "
                    f"Disponible : {stock_disponible} "
                    f"{self.entree.materiau.unite}."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    # ------------------------------------------------------
    # CALCULS
    # ------------------------------------------------------

    @property
    def quantite_sortie(self):
        return sum(
            (
                sortie.quantite
                for sortie in self.sorties.all()
            ),
            Decimal("0")
        )

    @property
    def stock_restant(self):
        return (
            self.quantite
            - self.quantite_sortie
        )

    def __str__(self):
        return (
            f"{self.entree.materiau.libelle} - "
            f"{self.destination} - "
            f"{self.quantite}"
        )

    class Meta:
        ordering = ["-date_division", "-id"]
        verbose_name = "Division matériau"
        verbose_name_plural = "Divisions matériaux"


# ==========================================================
# SORTIE MAGASIN
# ==========================================================

class MateriauxOut(models.Model):
    """
    Sortie d'un matériau depuis un magasin.
    """

    division = models.ForeignKey(
        MateriauxDivision,
        on_delete=models.PROTECT,
        related_name="sorties",
        verbose_name="Stock magasin"
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Quantité sortie"
    )

    date_sortie = models.DateField(
        verbose_name="Date de sortie"
    )

    destination = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Destination / Utilisation"
    )

    vehicule = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Véhicule"
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="materiaux_sorties",
        verbose_name="Enregistreur"
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    def clean(self):
        if not self.division_id:
            return

        total_sorties = (
            MateriauxOut.objects
            .filter(
                division=self.division
            )
            .exclude(
                pk=self.pk
            )
            .aggregate(
                total=models.Sum("quantite")
            )["total"]
            or Decimal("0")
        )

        stock_disponible = (
            self.division.quantite
            - total_sorties
        )

        if self.quantite <= 0:
            raise ValidationError({
                "quantite":
                    "La quantité doit être supérieure à zéro."
            })

        if self.quantite > stock_disponible:
            raise ValidationError({
                "quantite": (
                    "Stock magasin insuffisant. "
                    f"Disponible : {stock_disponible} "
                    f"{self.division.entree.materiau.unite}."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.division.entree.materiau.libelle} - "
            f"{self.quantite}"
        )

    class Meta:
        ordering = ["-date_sortie", "-id"]
        verbose_name = "Sortie matériau"
        verbose_name_plural = "Sorties matériaux"


# ==========================================================
# VÉHICULE
# ==========================================================

class Vehicule(models.Model):
    """
    Véhicule utilisé pour le transport et/ou les activités
    de l'entreprise.
    """

    immatriculation = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Immatriculation"
    )

    marque = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Marque"
    )

    modele = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Modèle"
    )

    kilometrage = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Kilométrage"
    )

    actif = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    # ------------------------------------------------------
    # CALCULS DU VÉHICULE
    # ------------------------------------------------------

    @property
    def total_gasoil(self):
        return sum(
            (
                depense.total
                for depense in self.depenses_gasoil.all()
            ),
            Decimal("0")
        )

    @property
    def total_reparations(self):
        return sum(
            (
                depense.total
                for depense in self.reparations.all()
            ),
            Decimal("0")
        )

    @property
    def total_depenses(self):
        return sum(
            (
                depense.montant
                for depense in self.depenses.all()
            ),
            Decimal("0")
        )

    @property
    def cout_total(self):
        return (
            self.total_gasoil
            + self.total_reparations
            + self.total_depenses
        )

    def __str__(self):
        return self.immatriculation

    class Meta:
        ordering = ["immatriculation"]
        verbose_name = "Véhicule"
        verbose_name_plural = "Véhicules"


# ==========================================================
# DOCKER
# ==========================================================

class Docker(models.Model):
    """
    Personne travaillant au chargement/déchargement
    des matériaux.
    """

    nom = models.CharField(
        max_length=100,
        verbose_name="Nom"
    )

    telephone = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Téléphone"
    )

    actif = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    @property
    def total_paiements(self):
        return sum(
            (
                ligne.montant
                for ligne in self.paiements.all()
            ),
            Decimal("0")
        )

    def __str__(self):
        return self.nom

    class Meta:
        ordering = ["nom"]
        verbose_name = "Docker"
        verbose_name_plural = "Dockers"


# ==========================================================
# CATÉGORIE DE DÉPENSE
# ==========================================================

class CategorieDepense(models.Model):
    """
    Catégories générales de dépenses.
    """

    nom = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Catégorie"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )

    actif = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )

    def __str__(self):
        return self.nom

    class Meta:
        ordering = ["nom"]
        verbose_name = "Catégorie de dépense"
        verbose_name_plural = "Catégories de dépenses"


# ==========================================================
# ACTIVITÉ DE TRANSPORT
# ==========================================================

class ActiviteTransport(models.Model):
    """
    Enregistre une activité de transport de matériaux
    ou toute autre activité réalisée avec un véhicule.
    """

    date_activite = models.DateField(
        verbose_name="Date"
    )

    vehicule = models.ForeignKey(
        Vehicule,
        on_delete=models.PROTECT,
        related_name="activites_transport",
        verbose_name="Véhicule"
    )

    materiau = models.ForeignKey(
        Materiaux,
        on_delete=models.PROTECT,
        related_name="activites_transport",
        null=True,
        blank=True,
        verbose_name="Matériau"
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Quantité"
    )

    unite = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Unité"
    )

    lieu_chargement = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Lieu de chargement"
    )

    destination = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Destination"
    )

    montant_transport = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Montant transport"
    )

    conducteur = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Conducteur"
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation"
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="activites_transport",
        verbose_name="Enregistreur"
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    # ------------------------------------------------------
    # CALCULS
    # ------------------------------------------------------

    @property
    def total_gasoil(self):
        return sum(
            (
                depense.total
                for depense in self.depenses_gasoil.all()
            ),
            Decimal("0")
        )

    @property
    def total_reparations(self):
        return sum(
            (
                depense.total
                for depense in self.reparations.all()
            ),
            Decimal("0")
        )

    @property
    def total_dockers(self):
        return sum(
            (
                paiement.montant
                for paiement in self.paiements_dockers.all()
            ),
            Decimal("0")
        )

    @property
    def total_depenses(self):
        return sum(
            (
                depense.montant
                for depense in self.depenses.all()
            ),
            Decimal("0")
        )

    @property
    def cout_exploitation(self):
        return (
            self.total_gasoil
            + self.total_reparations
            + self.total_dockers
            + self.total_depenses
        )

    @property
    def resultat_transport(self):
        return (
            self.montant_transport
            - self.cout_exploitation
        )

    @property
    def prix_unitaire_transport(self):
        if self.quantite <= 0:
            return Decimal("0")

        return (
            self.montant_transport
            / self.quantite
        )

    def __str__(self):
        return (
            f"{self.date_activite} - "
            f"{self.vehicule.immatriculation} - "
            f"{self.destination}"
        )

    class Meta:
        ordering = ["-date_activite", "-id"]
        verbose_name = "Activité de transport"
        verbose_name_plural = "Activités de transport"


# ==========================================================
# PAIEMENT DOCKER
# ==========================================================

class PaiementDocker(models.Model):
    """
    Paiement effectué à un docker dans le cadre
    d'une activité de transport.
    """

    activite = models.ForeignKey(
        ActiviteTransport,
        on_delete=models.PROTECT,
        related_name="paiements_dockers",
        verbose_name="Activité"
    )

    docker = models.ForeignKey(
        Docker,
        on_delete=models.PROTECT,
        related_name="paiements",
        verbose_name="Docker"
    )

    montant = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Montant"
    )

    observation = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Observation"
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="paiements_dockers",
        verbose_name="Enregistreur"
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    def clean(self):
        if self.montant <= 0:
            raise ValidationError({
                "montant":
                    "Le montant doit être supérieur à zéro."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.docker.nom} - "
            f"{self.montant}"
        )

    class Meta:
        ordering = ["-id"]
        verbose_name = "Paiement docker"
        verbose_name_plural = "Paiements dockers"


# ==========================================================
# DÉPENSE GÉNÉRALE
# ==========================================================

class Depense(models.Model):
    """
    Dépense générale de l'entreprise.

    Peut être liée à :
    - un véhicule
    - une activité de transport
    - un matériau
    - une catégorie
    """

    date_depense = models.DateField(
        verbose_name="Date"
    )

    categorie = models.ForeignKey(
        CategorieDepense,
        on_delete=models.PROTECT,
        related_name="depenses",
        verbose_name="Catégorie"
    )

    designation = models.CharField(
        max_length=200,
        verbose_name="Désignation"
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("1"),
        verbose_name="Quantité"
    )

    unite = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Unité"
    )

    prix_unitaire = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Prix unitaire"
    )

    montant = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Montant"
    )

    vehicule = models.ForeignKey(
        Vehicule,
        on_delete=models.PROTECT,
        related_name="depenses",
        null=True,
        blank=True,
        verbose_name="Véhicule"
    )

    activite = models.ForeignKey(
        ActiviteTransport,
        on_delete=models.PROTECT,
        related_name="depenses",
        null=True,
        blank=True,
        verbose_name="Activité de transport"
    )

    materiau = models.ForeignKey(
        Materiaux,
        on_delete=models.PROTECT,
        related_name="depenses",
        null=True,
        blank=True,
        verbose_name="Matériau"
    )

    localisation = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Localisation"
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation"
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="depenses_materiaux",
        verbose_name="Enregistreur"
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    def clean(self):

        if self.quantite < 0:
            raise ValidationError({
                "quantite":
                    "La quantité ne peut pas être négative."
            })

        if self.prix_unitaire < 0:
            raise ValidationError({
                "prix_unitaire":
                    "Le prix unitaire ne peut pas être négatif."
            })

        if self.montant < 0:
            raise ValidationError({
                "montant":
                    "Le montant ne peut pas être négatif."
            })

    def save(self, *args, **kwargs):

        # Si quantité et prix unitaire sont renseignés,
        # calcul automatique du montant.
        if (
            self.quantite is not None
            and self.prix_unitaire is not None
        ):
            self.montant = (
                self.quantite
                * self.prix_unitaire
            )

        self.full_clean()

        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.designation} - "
            f"{self.montant}"
        )

    class Meta:
        ordering = ["-date_depense", "-id"]
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"


# ==========================================================
# DÉPENSE GASOIL
# ==========================================================

class DepenseGasoil(models.Model):
    """
    Achat/consommation de gasoil.
    """

    date_gasoil = models.DateField(
        verbose_name="Date"
    )

    vehicule = models.ForeignKey(
        Vehicule,
        on_delete=models.PROTECT,
        related_name="depenses_gasoil",
        verbose_name="Véhicule"
    )

    activite = models.ForeignKey(
        ActiviteTransport,
        on_delete=models.PROTECT,
        related_name="depenses_gasoil",
        null=True,
        blank=True,
        verbose_name="Activité de transport"
    )

    quantite_litre = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Quantité (litres)"
    )

    prix_litre = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Prix par litre"
    )

    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Total"
    )

    station = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Station / Localisation"
    )

    kilometrage = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Kilométrage"
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation"
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="depenses_gasoil",
        verbose_name="Enregistreur"
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    def clean(self):

        if self.quantite_litre <= 0:
            raise ValidationError({
                "quantite_litre":
                    "La quantité doit être supérieure à zéro."
            })

        if self.prix_litre < 0:
            raise ValidationError({
                "prix_litre":
                    "Le prix du litre ne peut pas être négatif."
            })

    def save(self, *args, **kwargs):

        self.total = (
            self.quantite_litre
            * self.prix_litre
        )

        self.full_clean()

        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Gasoil {self.vehicule.immatriculation} - "
            f"{self.quantite_litre} L"
        )

    class Meta:
        ordering = ["-date_gasoil", "-id"]
        verbose_name = "Dépense gasoil"
        verbose_name_plural = "Dépenses gasoil"


# ==========================================================
# RÉPARATION / ENTRETIEN AUTOMOBILE
# ==========================================================

class ReparationVehicule(models.Model):
    """
    Réparation ou entretien d'un véhicule.

    Exemples :
    - pneu
    - gonflage
    - embrayage
    - alternateur
    - tambour
    - rétroviseur
    - lockeed
    - huile moteur
    - soudure
    - main-d'œuvre
    """

    TYPE_CHOICES = [
        ("REPARATION", "Réparation"),
        ("ENTRETIEN", "Entretien"),
        ("PNEU", "Pneumatique"),
        ("PIECE", "Pièce détachée"),
        ("MAIN_OEUVRE", "Main-d'œuvre"),
        ("AUTRE", "Autre"),
    ]

    date_reparation = models.DateField(
        verbose_name="Date"
    )

    vehicule = models.ForeignKey(
        Vehicule,
        on_delete=models.PROTECT,
        related_name="reparations",
        verbose_name="Véhicule"
    )

    activite = models.ForeignKey(
        ActiviteTransport,
        on_delete=models.PROTECT,
        related_name="reparations",
        null=True,
        blank=True,
        verbose_name="Activité"
    )

    type_reparation = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default="REPARATION",
        verbose_name="Type"
    )

    designation = models.CharField(
        max_length=200,
        verbose_name="Désignation"
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("1"),
        verbose_name="Quantité"
    )

    unite = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Unité"
    )

    prix_unitaire = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Prix unitaire"
    )

    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Total"
    )

    garage = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Garage / Fournisseur"
    )

    kilometrage = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Kilométrage"
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation"
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="reparations_vehicules",
        verbose_name="Enregistreur"
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    def clean(self):

        if self.quantite <= 0:
            raise ValidationError({
                "quantite":
                    "La quantité doit être supérieure à zéro."
            })

        if self.prix_unitaire < 0:
            raise ValidationError({
                "prix_unitaire":
                    "Le prix unitaire ne peut pas être négatif."
            })

    def save(self, *args, **kwargs):

        self.total = (
            self.quantite
            * self.prix_unitaire
        )

        self.full_clean()

        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.vehicule.immatriculation} - "
            f"{self.designation}"
        )

    class Meta:
        ordering = ["-date_reparation", "-id"]
        verbose_name = "Réparation véhicule"
        verbose_name_plural = "Réparations véhicules"