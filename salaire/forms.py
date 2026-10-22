from decimal import Decimal

from django import forms

from personnel.models import Personnel, H_Personnel

from .models import Salaire, H_Salaire

ZERO = Decimal("0")


# =============================================================
# FORMULAIRE SALAIRE GALAXY
# =============================================================


class SalaireForm(forms.ModelForm):
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
        model = Salaire
        fields = [
            "personnel",
            "nombre_jours",
            "salaire_contractuel_affichage",
            "montant",
            "date_paiement",
        ]
        labels = {
            "personnel": "Personnel",
            "nombre_jours": "Nombre de jours travaillés",
            "montant": "Salaire réellement payé",
            "date_paiement": "Date de paiement",
        }
        widgets = {
            "personnel": forms.Select(
                attrs={"class": "form-control"}
            ),
            "montant": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Montant réellement payé",
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

    def __init__(self, *args, **kwargs):
        role = kwargs.pop("role", None)
        super().__init__(*args, **kwargs)

        queryset = Personnel.objects.all().order_by("nom", "prenom")

        if role == "UserMica":
            queryset = queryset.filter(typeTravail="Mica")
        elif role == "UserEntreprise":
            queryset = queryset.filter(typeTravail="Construction")
        elif role in ["Admin", "SuperAdmin", "Superviseur"]:
            pass
        else:
            queryset = Personnel.objects.none()

        self.fields["personnel"].queryset = queryset
        self.fields["personnel"].required = True
        self.fields["montant"].required = True
        self.fields["date_paiement"].required = True

        if (
            self.instance
            and self.instance.pk
            and self.instance.date_paiement
        ):
            self.initial["date_paiement"] = self.instance.date_paiement

        personnel = None

        if (
            self.instance
            and self.instance.pk
            and self.instance.personnel_id
        ):
            personnel = self.instance.personnel

        if personnel is None:
            personnel = self._resoudre_personnel(
                self.initial.get("personnel")
            )

        if personnel:
            self.initial["personnel"] = personnel.pk
            self._actualiser_infos_personnel(personnel)

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def _resoudre_personnel(self, valeur):
        if not valeur:
            return None

        if isinstance(valeur, Personnel):
            return valeur

        try:
            personnel_id = int(valeur)
        except (ValueError, TypeError):
            return None

        return Personnel.objects.filter(pk=personnel_id).first()

    def _actualiser_infos_personnel(self, personnel):
        personnel = self._resoudre_personnel(personnel)

        if not personnel:
            return

        type_contrat = getattr(personnel, "typeContrat", None)

        taux = Decimal(
            str(getattr(personnel, "psalaire", ZERO) or ZERO)
        )

        if type_contrat == "Journalier":
            self.fields["nombre_jours"].required = True
            jours = self.initial.get("nombre_jours")

            if not jours:
                jours = (
                    getattr(self.instance, "nombre_jours", 1) or 1
                )

            try:
                jours = int(jours)
            except (ValueError, TypeError):
                jours = 1

            salaire_contractuel = taux * Decimal(jours)
        else:
            self.fields["nombre_jours"].required = False
            salaire_contractuel = taux

        self.fields[
            "salaire_contractuel_affichage"
        ].initial = f"{salaire_contractuel:,.0f} Ar"

    def clean_personnel(self):
        personnel = self.cleaned_data.get("personnel")

        if not personnel:
            raise forms.ValidationError(
                "Veuillez sélectionner un personnel."
            )

        return personnel

    def clean_nombre_jours(self):
        personnel = self.cleaned_data.get("personnel")
        jours = self.cleaned_data.get("nombre_jours")
        personnel = self._resoudre_personnel(personnel)

        if (
            personnel
            and getattr(personnel, "typeContrat", None) == "Journalier"
        ):
            if not jours:
                raise forms.ValidationError(
                    "Veuillez saisir le nombre de jours travaillés "
                    "pour un personnel journalier."
                )

            if jours <= 0:
                raise forms.ValidationError(
                    "Le nombre de jours doit être supérieur à 0."
                )

            return jours

        return jours or 1

    def clean_montant(self):
        montant = self.cleaned_data.get("montant")

        if montant is None:
            raise forms.ValidationError(
                "Veuillez saisir le montant réellement payé."
            )

        if montant < 0:
            raise forms.ValidationError(
                "Le salaire payé ne peut pas être négatif."
            )

        return montant

    def clean_date_paiement(self):
        date_paiement = self.cleaned_data.get("date_paiement")

        if not date_paiement:
            raise forms.ValidationError(
                "Veuillez sélectionner la date de paiement."
            )

        return date_paiement

    def clean(self):
        cleaned_data = super().clean()

        personnel = cleaned_data.get("personnel")
        jours = cleaned_data.get("nombre_jours")
        date_paiement = cleaned_data.get("date_paiement")

        if not personnel:
            return cleaned_data

        debut = getattr(personnel, "debutContrat", None)
        fin = getattr(personnel, "finContrat", None)
        type_contrat = getattr(personnel, "typeContrat", None)

        if date_paiement and debut and date_paiement < debut:
            raise forms.ValidationError(
                "Le paiement ne peut pas être antérieur au début "
                f"du contrat ({debut.strftime('%d/%m/%Y')})."
            )

        if (
            date_paiement
            and fin
            and type_contrat in ["CDD", "Stage"]
            and date_paiement > fin
        ):
            raise forms.ValidationError(
                "Le paiement ne peut pas être postérieur à la fin "
                f"du contrat ({fin.strftime('%d/%m/%Y')})."
            )

        taux = Decimal(str(personnel.psalaire or ZERO))

        if type_contrat == "Journalier":
            if not jours:
                raise forms.ValidationError(
                    "Le nombre de jours travaillés est obligatoire "
                    "pour un journalier."
                )

            salaire_contractuel = taux * Decimal(jours)
        else:
            salaire_contractuel = taux

        cleaned_data["_salaire_contractuel"] = salaire_contractuel
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        personnel = self.cleaned_data.get("personnel")
        jours = self.cleaned_data.get("nombre_jours") or 1

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


# =============================================================
# FORMULAIRE SALAIRE MCCR
# =============================================================


class H_SalaireForm(forms.ModelForm):
    """
    Formulaire des salaires MCCR.

    Utilise exclusivement H_Personnel et H_Salaire.

    Règles :
    - CDI / CDD / Stage : salaire contractuel = salaire de référence.
    - Journalier : salaire contractuel = salaire de référence
      multiplié par le nombre de jours.
    - Le montant correspond au salaire réellement payé.
    """

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
        model = H_Salaire
        fields = [
            "personnel",
            "nombre_jours",
            "salaire_contractuel_affichage",
            "montant",
            "date_paiement",
        ]
        labels = {
            "personnel": "Personnel MCCR",
            "nombre_jours": "Nombre de jours travaillés",
            "montant": "Salaire réellement payé",
            "date_paiement": "Date de paiement",
        }
        widgets = {
            "personnel": forms.Select(
                attrs={"class": "form-control"}
            ),
            "montant": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Montant réellement payé",
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

    def __init__(self, *args, **kwargs):
        # Le formulaire MCCR n'utilise pas les rôles GALAXY.
        kwargs.pop("role", None)
        super().__init__(*args, **kwargs)

        # Personnel exclusivement issu de MCCR.
        self.fields["personnel"].queryset = (
            H_Personnel.objects.all().order_by("nom", "prenom")
        )

        self.fields["personnel"].required = True
        self.fields["montant"].required = True
        self.fields["date_paiement"].required = True

        if self.instance and self.instance.pk:
            self.initial["date_paiement"] = (
                self.instance.date_paiement
            )

        personnel = None

        if self.instance and self.instance.pk:
            personnel = self.instance.personnel

        if personnel is None:
            valeur_personnel = (
                self.data.get("personnel")
                if self.is_bound
                else self.initial.get("personnel")
            )
            personnel = self._resoudre_personnel(valeur_personnel)

        if personnel:
            self.initial["personnel"] = personnel.pk

            jours = (
                self.data.get("nombre_jours")
                if self.is_bound
                else self.initial.get("nombre_jours")
            )

            if not jours and self.instance and self.instance.pk:
                jours = self.instance.nombre_jours

            self._actualiser_infos_personnel(
                personnel,
                jours=jours,
            )

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def _resoudre_personnel(self, valeur):
        if not valeur:
            return None

        if isinstance(valeur, H_Personnel):
            return valeur

        try:
            personnel_id = int(valeur)
        except (ValueError, TypeError):
            return None

        return H_Personnel.objects.filter(
            pk=personnel_id
        ).first()

    def _actualiser_infos_personnel(self, personnel, jours=1):
        personnel = self._resoudre_personnel(personnel)

        if not personnel:
            return

        # CORRECTION : H_Personnel possède "salaire", pas "psalaire".
        taux = Decimal(str(personnel.salaire or ZERO))

        type_contrat = getattr(personnel, "typeContrat", None)

        if type_contrat == "Journalier":
            self.fields["nombre_jours"].required = True

            try:
                jours = int(jours or 1)
            except (ValueError, TypeError):
                jours = 1

            jours = max(1, jours)
        else:
            self.fields["nombre_jours"].required = False
            jours = 1

        salaire_contractuel = H_Salaire.calculer_salaire_contractuel(
            personnel,
            jours,
        )

        self.fields[
            "salaire_contractuel_affichage"
        ].initial = f"{salaire_contractuel:,.0f} Ar"

    def clean_personnel(self):
        personnel = self.cleaned_data.get("personnel")

        if not personnel:
            raise forms.ValidationError(
                "Veuillez sélectionner un personnel MCCR."
            )

        if not H_Personnel.objects.filter(pk=personnel.pk).exists():
            raise forms.ValidationError(
                "Le personnel sélectionné n'appartient pas à MCCR."
            )

        return personnel

    def clean_nombre_jours(self):
        personnel = self.cleaned_data.get("personnel")
        jours = self.cleaned_data.get("nombre_jours")

        if (
            personnel
            and getattr(personnel, "typeContrat", None) == "Journalier"
        ):
            if jours is None or jours < 1:
                raise forms.ValidationError(
                    "Le nombre de jours doit être supérieur à zéro "
                    "pour un personnel journalier."
                )

            return jours

        return jours or 1

    def clean_montant(self):
        montant = self.cleaned_data.get("montant")

        if montant is None:
            raise forms.ValidationError(
                "Veuillez saisir le montant réellement payé."
            )

        if montant < ZERO:
            raise forms.ValidationError(
                "Le salaire payé ne peut pas être négatif."
            )

        return montant

    def clean_date_paiement(self):
        date_paiement = self.cleaned_data.get("date_paiement")

        if not date_paiement:
            raise forms.ValidationError(
                "Veuillez sélectionner la date de paiement."
            )

        return date_paiement

    def clean(self):
        cleaned_data = super().clean()

        personnel = cleaned_data.get("personnel")
        jours = cleaned_data.get("nombre_jours") or 1
        date_paiement = cleaned_data.get("date_paiement")

        if not personnel:
            return cleaned_data

        debut = getattr(personnel, "debutContrat", None)
        fin = getattr(personnel, "finContrat", None)
        type_contrat = getattr(personnel, "typeContrat", None)

        if (
            date_paiement
            and debut
            and date_paiement < debut
        ):
            raise forms.ValidationError(
                "Le paiement ne peut pas être antérieur au début "
                f"du contrat ({debut.strftime('%d/%m/%Y')})."
            )

        if (
            date_paiement
            and fin
            and type_contrat in ["CDD", "Stage"]
            and date_paiement > fin
        ):
            raise forms.ValidationError(
                "Le paiement ne peut pas être postérieur à la fin "
                f"du contrat ({fin.strftime('%d/%m/%Y')})."
            )

        salaire_contractuel = H_Salaire.calculer_salaire_contractuel(
            personnel,
            jours,
        )

        cleaned_data["_salaire_contractuel"] = salaire_contractuel
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        personnel = self.cleaned_data.get("personnel")
        jours = self.cleaned_data.get("nombre_jours") or 1

        if personnel:
            instance.salaire_contractuel = (
                H_Salaire.calculer_salaire_contractuel(
                    personnel,
                    jours,
                )
            )

        instance.nombre_jours = jours

        if commit:
            instance.save()

        return instance
