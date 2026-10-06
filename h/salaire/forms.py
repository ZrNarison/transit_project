from decimal import Decimal

from django import forms

from personnel.models import h_Personnel

from .models import h_Salaire


ZERO = Decimal("0")


# =============================================================
# FORMULAIRE SALAIRE
# =============================================================

class h_SalaireForm(forms.ModelForm):

    # =========================================================
    # NOMBRE DE JOURS
    # =========================================================

    nombre_jours = forms.IntegerField(
        required=False,
        min_value=1,
        label="Nombre de jours travaillés",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "placeholder": "Nombre de jours",
                "min": "1",
                "step": "1",
            }
        ),
    )

    # =========================================================
    # SALAIRE CONTRACTUEL AFFICHÉ
    # =========================================================

    salaire_contractuel_affichage = forms.CharField(
        required=False,
        label="Salaire contractuel",
        disabled=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "readonly": "readonly",
            }
        ),
    )

    class Meta:

        model = h_Salaire

        fields = [
            "personnel",
            "nombre_jours",
            "salaire_contractuel_affichage",
            "montant",
            "date_paiement",
        ]

        labels = {
            "personnel": "Personnel",
            "nombre_jours": (
                "Nombre de jours travaillés"
            ),
            "montant": (
                "Salaire réellement payé"
            ),
            "date_paiement": (
                "Date de paiement"
            ),
        }

        widgets = {
            "personnel": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "montant": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Montant réellement payé"
                    ),
                    "min": "0",
                    "step": "1",
                }
            ),

            "date_paiement": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),
        }

    # =========================================================
    # INITIALISATION
    # =========================================================

    def __init__(
        self,
        *args,
        **kwargs
    ):

        role = kwargs.pop(
            "role",
            None
        )

        super().__init__(
            *args,
            **kwargs
        )

        # =====================================================
        # PERSONNEL
        # =====================================================

        queryset = (
            h_Personnel.objects
            .all()
            .order_by(
                "nom",
                "prenom",
            )
        )

        # =====================================================
        # FILTRE PAR ROLE
        # =====================================================

        if role == "UserMica":

            queryset = queryset.filter(
                typeTravail="Mica"
            )

        elif role == "UserEntreprise":

            queryset = queryset.filter(
                typeTravail="Construction"
            )

        elif role in [
            "Admin",
            "SuperAdmin",
            "Superviseur",
        ]:

            pass

        else:

            queryset = (
                h_Personnel.objects.none()
            )

        self.fields[
            "personnel"
        ].queryset = queryset

        # =====================================================
        # CHAMPS OBLIGATOIRES
        # =====================================================

        self.fields[
            "personnel"
        ].required = True

        self.fields[
            "montant"
        ].required = True

        self.fields[
            "date_paiement"
        ].required = True

        # =====================================================
        # DATE EN ÉDITION
        # =====================================================

        if (
            self.instance
            and self.instance.pk
            and self.instance.date_paiement
        ):

            self.initial[
                "date_paiement"
            ] = self.instance.date_paiement

        # =====================================================
        # RÉCUPÉRATION DU PERSONNEL
        # =====================================================

        personnel = None

        # -----------------------------------------------------
        # Priorité à l'instance existante
        #
        # C'est important en mode modification.
        # -----------------------------------------------------

        if (
            self.instance
            and self.instance.pk
            and self.instance.personnel_id
        ):

            personnel = (
                self.instance.personnel
            )

        # -----------------------------------------------------
        # Si initial contient personnel
        # -----------------------------------------------------

        if personnel is None:

            initial_personnel = (
                self.initial.get(
                    "personnel"
                )
            )

            personnel = (
                self._resoudre_personnel(
                    initial_personnel
                )
            )

        # -----------------------------------------------------
        # Actualisation
        # -----------------------------------------------------

        if personnel:

            self.initial[
                "personnel"
            ] = personnel.pk

            self._actualiser_infos_personnel(
                personnel
            )

        # =====================================================
        # CLASSES BOOTSTRAP
        # =====================================================

        for field in self.fields.values():

            field.widget.attrs.setdefault(
                "class",
                "form-control",
            )

    # =========================================================
    # RÉSOUDRE UN PERSONNEL
    # =========================================================

    def _resoudre_personnel(
        self,
        valeur,
    ):
        """
        Transforme :

            Personnel
            ID entier
            chaîne contenant un ID

        en :

            objet Personnel
        """

        if not valeur:
            return None

        # -----------------------------------------------------
        # Déjà un objet Personnel
        # -----------------------------------------------------

        if isinstance(
            valeur,
            h_Personnel
        ):
            return valeur

        # -----------------------------------------------------
        # ID entier
        # -----------------------------------------------------

        try:

            personnel_id = int(
                valeur
            )

        except (
            ValueError,
            TypeError
        ):

            return None

        # -----------------------------------------------------
        # Recherche
        # -----------------------------------------------------

        return (
            h_Personnel.objects
            .filter(
                pk=personnel_id
            )
            .first()
        )

    # =========================================================
    # INFORMATIONS PERSONNEL
    # =========================================================

    def _actualiser_infos_personnel(
        self,
        h_personnel,
    ):

        # =====================================================
        # SÉCURITÉ
        # =====================================================

        h_personnel = (
            self._resoudre_personnel(
                h_personnel
            )
        )

        if not h_personnel:
            return

        # =====================================================
        # CONTRAT
        # =====================================================

        type_contrat = getattr(
            h_personnel,
            "typeContrat",
            None,
        )

        taux = Decimal(
            str(
                getattr(
                    h_personnel,
                    "psalaire",
                    ZERO,
                )
                or ZERO
            )
        )

        # =====================================================
        # JOURNALIER
        # =====================================================

        if type_contrat == "Journalier":

            self.fields[
                "nombre_jours"
            ].required = True

            jours = (
                self.initial.get(
                    "nombre_jours"
                )
            )

            if not jours:

                jours = getattr(
                    self.instance,
                    "nombre_jours",
                    1,
                ) or 1

            try:

                jours = int(
                    jours
                )

            except (
                ValueError,
                TypeError
            ):

                jours = 1

            salaire_contractuel = (
                taux
                * Decimal(jours)
            )

        # =====================================================
        # CDI / CDD / STAGE
        # =====================================================

        else:

            self.fields[
                "nombre_jours"
            ].required = False

            salaire_contractuel = taux

        # =====================================================
        # AFFICHAGE
        # =====================================================

        self.fields[
            "salaire_contractuel_affichage"
        ].initial = (
            f"{salaire_contractuel:,.0f} Ar"
        )

    # =========================================================
    # PERSONNEL
    # =========================================================

    def clean_personnel(self):

        personnel = (
            self.cleaned_data.get(
                "personnel"
            )
        )

        if not personnel:

            raise forms.ValidationError(
                "Veuillez sélectionner un personnel."
            )

        return personnel

    # =========================================================
    # NOMBRE DE JOURS
    # =========================================================

    def clean_nombre_jours(self):

        personnel = (
            self.cleaned_data.get(
                "personnel"
            )
        )

        jours = (
            self.cleaned_data.get(
                "nombre_jours"
            )
        )

        # -----------------------------------------------------
        # Sécurité supplémentaire
        # -----------------------------------------------------

        personnel = (
            self._resoudre_personnel(
                personnel
            )
        )

        if (
            personnel
            and getattr(
                personnel,
                "typeContrat",
                None
            ) == "Journalier"
        ):

            if not jours:

                raise forms.ValidationError(
                    "Veuillez saisir le nombre de jours "
                    "travaillés pour un personnel journalier."
                )

            if jours <= 0:

                raise forms.ValidationError(
                    "Le nombre de jours doit être "
                    "supérieur à 0."
                )

            return jours

        # -----------------------------------------------------
        # CDI / CDD / STAGE
        # -----------------------------------------------------

        return jours or 1

    # =========================================================
    # MONTANT
    # =========================================================

    def clean_montant(self):

        montant = (
            self.cleaned_data.get(
                "montant"
            )
        )

        if montant is None:

            raise forms.ValidationError(
                "Veuillez saisir le montant "
                "réellement payé."
            )

        if montant < 0:

            raise forms.ValidationError(
                "Le salaire payé ne peut pas être négatif."
            )

        return montant

    # =========================================================
    # DATE
    # =========================================================

    def clean_date_paiement(self):

        date_paiement = (
            self.cleaned_data.get(
                "date_paiement"
            )
        )

        if not date_paiement:

            raise forms.ValidationError(
                "Veuillez sélectionner la date de paiement."
            )

        return date_paiement

    # =========================================================
    # VALIDATION GLOBALE
    # =========================================================

    def clean(self):

        cleaned_data = super().clean()

        personnel = (
            cleaned_data.get(
                "personnel"
            )
        )

        jours = (
            cleaned_data.get(
                "nombre_jours"
            )
        )

        date_paiement = (
            cleaned_data.get(
                "date_paiement"
            )
        )

        if not personnel:
            return cleaned_data

        # =====================================================
        # CONTRAT
        # =====================================================

        debut = getattr(
            personnel,
            "debutContrat",
            None,
        )

        fin = getattr(
            personnel,
            "finContrat",
            None,
        )

        type_contrat = getattr(
            personnel,
            "typeContrat",
            None,
        )

        # =====================================================
        # AVANT DÉBUT DU CONTRAT
        # =====================================================

        if (
            date_paiement
            and debut
            and date_paiement < debut
        ):

            raise forms.ValidationError(
                "Le paiement ne peut pas être antérieur "
                f"au début du contrat "
                f"({debut.strftime('%d/%m/%Y')})."
            )

        # =====================================================
        # APRÈS FIN CDD / STAGE
        # =====================================================

        if (
            date_paiement
            and fin
            and type_contrat in [
                "CDD",
                "Stage",
            ]
            and date_paiement > fin
        ):

            raise forms.ValidationError(
                "Le paiement ne peut pas être postérieur "
                f"à la fin du contrat "
                f"({fin.strftime('%d/%m/%Y')})."
            )

        # =====================================================
        # SALAIRE CONTRACTUEL
        # =====================================================

        taux = Decimal(
            str(
                personnel.psalaire
                or ZERO
            )
        )

        if type_contrat == "Journalier":

            if not jours:

                raise forms.ValidationError(
                    "Le nombre de jours travaillés "
                    "est obligatoire pour un journalier."
                )

            salaire_contractuel = (
                taux
                * Decimal(jours)
            )

        else:

            salaire_contractuel = taux

        # =====================================================
        # MONTANT PAYÉ
        # =====================================================

        montant = (
            cleaned_data.get(
                "montant"
            )
            or ZERO
        )

        # =====================================================
        # STOCKAGE POUR SAVE
        # =====================================================

        cleaned_data[
            "_salaire_contractuel"
        ] = salaire_contractuel

        return cleaned_data

    # =========================================================
    # SAVE
    # =========================================================

    def save(
        self,
        commit=True
    ):

        instance = super().save(
            commit=False
        )

        personnel = (
            self.cleaned_data.get(
                "personnel"
            )
        )

        jours = (
            self.cleaned_data.get(
                "nombre_jours"
            )
            or 1
        )

        if personnel:

            instance.salaire_contractuel = (
                Salaire.calculer_salaire_contractuel(
                    personnel,
                    jours,
                )
            )

        instance.nombre_jours = jours

        if commit:

            instance.save()

        return instance