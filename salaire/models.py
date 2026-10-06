from decimal import Decimal

from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

from personnel.models import Personnel
from avances.models import Avance
from users.models import AppUser


ZERO = Decimal("0")


# =============================================================
# SALAIRE
# =============================================================

class Salaire(models.Model):

    class Meta:
        app_label = "salaire"
        ordering = ["-date_paiement", "-created_at"]
        verbose_name = "Salaire"
        verbose_name_plural = "Salaires"

    # =========================================================
    # PERSONNEL
    # =========================================================

    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="salaires",
    )

    # =========================================================
    # SALAIRE CONTRACTUEL
    # =========================================================

    salaire_contractuel = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO,
    )

    # =========================================================
    # NOMBRE DE JOURS
    # =========================================================

    nombre_jours = models.PositiveIntegerField(
        default=1,
    )

    # =========================================================
    # MONTANT RÉELLEMENT PAYÉ
    # =========================================================

    montant = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO,
    )

    # =========================================================
    # RESTE
    #
    # Positif  = montant encore dû
    # Zéro     = situation équilibrée
    # Négatif  = trop-perçu
    # =========================================================

    reste = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO,
    )

    # =========================================================
    # TROP-PERÇU
    # =========================================================

    trop_percu = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=ZERO,
    )

    # =========================================================
    # DATE DU PAIEMENT
    # =========================================================

    date_paiement = models.DateField(
        default=timezone.localdate,
    )

    # =========================================================
    # DATE D'ENREGISTREMENT
    # =========================================================

    date = models.DateField(
        auto_now_add=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    # =========================================================
    # ENREGISTREUR
    # =========================================================

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="salaires_enregistres",
    )

    # =========================================================
    # AFFICHAGE
    # =========================================================

    def __str__(self):
        target = self.personnel or "Sans personnel"
        return f"{target} - {self.montant} Ar"

    # =========================================================
    # CALCUL SALAIRE CONTRACTUEL
    # =========================================================

    @staticmethod
    def calculer_salaire_contractuel(
        personnel,
        nombre_jours=1,
    ):
        """
        CDI / CDD / Stage :
            salaire = psalaire

        Journalier :
            salaire = psalaire × nombre_jours
        """

        if not personnel:
            return ZERO

        taux = Decimal(
            str(personnel.psalaire or ZERO)
        )

        type_contrat = getattr(
            personnel,
            "typeContrat",
            None,
        )

        if type_contrat == "Journalier":
            try:
                jours = int(nombre_jours or 0)
            except (ValueError, TypeError):
                jours = 0

            if jours < 0:
                jours = 0

            return taux * Decimal(jours)

        return taux

    # =========================================================
    # TOTAL DES AVANCES AFFECTÉES
    # =========================================================

    def montant_avances_affectees(self):
        total = (
            self.affectations_avances
            .aggregate(total=Sum("montant"))
            ["total"]
        )

        return total or ZERO

    # =========================================================
    # TOTAL RÉELLEMENT REÇU
    #
    # Salaire payé + toutes les avances affectées
    # =========================================================

    def montant_total_recu(self):
        avances = Decimal(
            str(
                self.montant_avances_affectees()
                or ZERO
            )
        )

        salaire_paye = Decimal(
            str(
                self.montant or ZERO
            )
        )

        return salaire_paye + avances

    # =========================================================
    # CALCUL DE LA SITUATION
    # =========================================================

    def calculer_situation(self):
        """
        Formule exacte :

            reste =
                salaire contractuel
                - salaire réellement payé
                - avances affectées

        Exemple DASY :

            Contractuel : 200 000
            Salaire     : 100 000
            Avance      : 200 000

            Reste = 200 000
                    - 100 000
                    - 200 000

                  = -100 000
        """

        contractuel = Decimal(
            str(
                self.salaire_contractuel
                or ZERO
            )
        )

        salaire_paye = Decimal(
            str(
                self.montant or ZERO
            )
        )

        avances = Decimal(
            str(
                self.montant_avances_affectees()
                or ZERO
            )
        )

        reste = (
            contractuel
            - salaire_paye
            - avances
        )

        trop_percu = (
            abs(reste)
            if reste < ZERO
            else ZERO
        )

        return reste, trop_percu

    # =========================================================
    # RECALCUL DU RESTE
    # =========================================================

    def recalculer_reste(self):

        reste, trop_percu = (
            self.calculer_situation()
        )

        Salaire.objects.filter(
            pk=self.pk
        ).update(
            reste=reste,
            trop_percu=trop_percu,
        )

        self.reste = reste
        self.trop_percu = trop_percu

        return reste

    # =========================================================
    # SAVE
    # =========================================================

    def save(self, *args, **kwargs):

        if self.personnel:

            if not self.nombre_jours:
                self.nombre_jours = 1

            # -------------------------------------------------
            # Calcul initial du salaire contractuel
            # -------------------------------------------------

            if (
                self._state.adding
                or not self.salaire_contractuel
            ):
                self.salaire_contractuel = (
                    self.calculer_salaire_contractuel(
                        self.personnel,
                        self.nombre_jours,
                    )
                )

        # -----------------------------------------------------
        # Sécurité montant
        # -----------------------------------------------------

        if self.montant is None:
            self.montant = ZERO

        # -----------------------------------------------------
        # Calcul initial du reste
        #
        # Les avances seront affectées ensuite par
        # recalculer_situation_personnel().
        # -----------------------------------------------------

        if self._state.adding:

            contractuel = Decimal(
                str(
                    self.salaire_contractuel
                    or ZERO
                )
            )

            salaire_paye = Decimal(
                str(
                    self.montant
                    or ZERO
                )
            )

            self.reste = (
                contractuel
                - salaire_paye
            )

            self.trop_percu = (
                abs(self.reste)
                if self.reste < ZERO
                else ZERO
            )

        super().save(
            *args,
            **kwargs
        )


# =============================================================
# AFFECTATION DES AVANCES AUX SALAIRES
# =============================================================

class PaiementAvanceSalaire(models.Model):
    """
    Lie une avance à un salaire.

    Une avance disponible est affectée au salaire
    conformément à l'ordre chronologique.

    IMPORTANT :

    L'avance est affectée EN TOTALITÉ lorsqu'elle devient
    disponible pour un salaire.

    Exemple :

        Avance DASY = 200 000
        Salaire DASY = 100 000

        Affectation = 200 000

        Reste salaire :
            200 000 - 100 000 - 200 000
            = -100 000
    """

    avance = models.ForeignKey(
        Avance,
        on_delete=models.CASCADE,
        related_name="affectations_salaires",
    )

    salaire = models.ForeignKey(
        Salaire,
        on_delete=models.CASCADE,
        related_name="affectations_avances",
    )

    montant = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["id"]

        verbose_name = (
            "Affectation avance salaire"
        )

        verbose_name_plural = (
            "Affectations avances salaires"
        )

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "avance",
                    "salaire",
                ],
                name="unique_avance_salaire",
            )
        ]

    def __str__(self):
        return (
            f"Avance #{self.avance_id} "
            f"→ Salaire #{self.salaire_id} : "
            f"{self.montant} Ar"
        )


# =============================================================
# RECALCUL COMPLET D'UN PERSONNEL
# =============================================================

def recalculer_situation_personnel(personnel):

    """
    Recalcule toute la situation salariale d'un personnel.

    LOGIQUE EXACTE :

    1. Tous les salaires du personnel sont récupérés.
    2. Toutes ses avances sont récupérées.
    3. Les anciennes affectations sont supprimées.
    4. Les salaires sont traités dans l'ordre chronologique.
    5. Une avance n'est disponible que si :
           avance.dateAv <= salaire.date_paiement
    6. Lorsqu'une avance devient disponible pour un salaire,
       SON MONTANT COMPLET est affecté.
    7. Une avance déjà affectée n'est plus disponible.
    8. Le salaire payé est toujours compté séparément.
    9. Le reste est :

           contractuel
           - salaire payé
           - avances affectées

    10. Un reste négatif est un trop-perçu.
    """

    if not personnel:
        return

    with transaction.atomic():

        # =====================================================
        # SALAIRES
        # =====================================================

        salaires = list(
            Salaire.objects
            .filter(
                personnel=personnel
            )
            .order_by(
                "date_paiement",
                "date",
                "created_at",
                "id",
            )
        )

        # =====================================================
        # AVANCES
        # =====================================================

        avances = list(
            Avance.objects
            .filter(
                personnel=personnel
            )
            .order_by(
                "dateAv",
                "id",
            )
        )

        # =====================================================
        # SUPPRESSION DES ANCIENNES AFFECTATIONS
        # =====================================================

        PaiementAvanceSalaire.objects.filter(
            salaire__personnel=personnel
        ).delete()

        # =====================================================
        # SOLDE INITIAL DE CHAQUE AVANCE
        # =====================================================

        soldes_avances = {}

        for avance in avances:

            montant = Decimal(
                str(
                    avance.montantAv
                    or ZERO
                )
            )

            if montant < ZERO:
                montant = ZERO

            soldes_avances[
                avance.id
            ] = montant

        # =====================================================
        # TRAITEMENT DES SALAIRES
        # =====================================================

        for salaire in salaires:

            # =================================================
            # SALAIRE CONTRACTUEL
            # =================================================

            if not salaire.salaire_contractuel:

                salaire.salaire_contractuel = (
                    Salaire.calculer_salaire_contractuel(
                        salaire.personnel,
                        salaire.nombre_jours,
                    )
                )

                Salaire.objects.filter(
                    pk=salaire.pk
                ).update(
                    salaire_contractuel=(
                        salaire.salaire_contractuel
                    )
                )

            salaire_contractuel = Decimal(
                str(
                    salaire.salaire_contractuel
                    or ZERO
                )
            )

            # =================================================
            # SALAIRE RÉELLEMENT PAYÉ
            # =================================================

            salaire_paye = Decimal(
                str(
                    salaire.montant
                    or ZERO
                )
            )

            # =================================================
            # DATE DU SALAIRE
            # =================================================

            date_paiement = (
                salaire.date_paiement
            )

            # =================================================
            # AFFECTATION DES AVANCES
            # =================================================

            for avance in avances:

                # -------------------------------------------------
                # Avance déjà totalement utilisée
                # -------------------------------------------------

                solde_avance = soldes_avances.get(
                    avance.id,
                    ZERO,
                )

                if solde_avance <= ZERO:
                    continue

                # -------------------------------------------------
                # Sécurité personnel
                # -------------------------------------------------

                if avance.personnel_id != personnel.id:
                    continue

                # -------------------------------------------------
                # DATE DE L'AVANCE
                # -------------------------------------------------

                date_avance = avance.dateAv

                if hasattr(
                    date_avance,
                    "date"
                ):
                    date_avance = date_avance.date()

                # -------------------------------------------------
                # Une avance future ne peut jamais être utilisée
                # -------------------------------------------------

                if date_avance > date_paiement:
                    continue

                # =================================================
                # LOGIQUE IMPORTANTE
                #
                # Toute l'avance disponible est affectée.
                #
                # PAS :
                #
                #     min(besoin, solde)
                #
                # mais :
                #
                #     montant_affecte = solde_avance
                #
                # C'est ce qui donne :
                #
                # DASY :
                # 200 000 avance
                # 100 000 salaire
                # => 200 000 avance affectée
                # => reste -100 000
                # =================================================

                montant_affecte = (
                    solde_avance
                )

                if montant_affecte <= ZERO:
                    continue

                # -------------------------------------------------
                # Création de l'affectation
                # -------------------------------------------------

                PaiementAvanceSalaire.objects.create(
                    avance=avance,
                    salaire=salaire,
                    montant=montant_affecte,
                )

                # -------------------------------------------------
                # L'avance est entièrement consommée
                # -------------------------------------------------

                soldes_avances[
                    avance.id
                ] = ZERO

            # =====================================================
            # TOTAL DES AVANCES AFFECTÉES
            # =====================================================

            avances_affectees = (
                PaiementAvanceSalaire.objects
                .filter(
                    salaire=salaire
                )
                .aggregate(
                    total=Sum("montant")
                )["total"]
                or ZERO
            )

            avances_affectees = Decimal(
                str(
                    avances_affectees
                )
            )

            # =====================================================
            # TOTAL RÉELLEMENT REÇU
            # =====================================================

            total_recu = (
                salaire_paye
                + avances_affectees
            )

            # =====================================================
            # RESTE SIGNÉ
            # =====================================================

            reste = (
                salaire_contractuel
                - total_recu
            )

            # =====================================================
            # TROP-PERÇU
            # =====================================================

            trop_percu = (
                abs(reste)
                if reste < ZERO
                else ZERO
            )

            # =====================================================
            # SAUVEGARDE
            # =====================================================

            Salaire.objects.filter(
                pk=salaire.pk
            ).update(
                salaire_contractuel=(
                    salaire_contractuel
                ),
                reste=reste,
                trop_percu=trop_percu,
            )

            salaire.salaire_contractuel = (
                salaire_contractuel
            )

            salaire.reste = reste

            salaire.trop_percu = (
                trop_percu
            )

        # =====================================================
        # MISE À JOUR DES AVANCES
        # =====================================================

        for avance in avances:

            montant_avance = Decimal(
                str(
                    avance.montantAv
                    or ZERO
                )
            )

            solde = soldes_avances.get(
                avance.id,
                montant_avance,
            )

            if solde < ZERO:
                solde = ZERO

            montant_recupere = (
                montant_avance
                - solde
            )

            if montant_recupere < ZERO:
                montant_recupere = ZERO

            # -------------------------------------------------
            # Mise à jour de l'avance
            # -------------------------------------------------

            Avance.objects.filter(
                pk=avance.pk
            ).update(
                montant_recupere=(
                    montant_recupere
                ),
                reste=solde,
            )