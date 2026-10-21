from django import forms

from categorie.models import Categorie

from .models import H_Personnel, Personnel


class PersonnelForm(forms.ModelForm):

    class Meta:
        model = Personnel

        fields = [
            "nom",
            "prenom",
            "adresse",
            "telephone",
            "fonction",
            "typeTravail",
            "typeContrat",
            "psalaire",
            "debutContrat",
            "finContrat",
            "lieuTravail",
            "categorie",
            "photo",
        ]

        widgets = {
            "nom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom",
                }
            ),
            "prenom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Prénom",
                }
            ),
            "adresse": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Adresse",
                    "style": "resize:none;",
                }
            ),
            "telephone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "maxlength": "10",
                    "placeholder": "034 01 000 01",
                    "pattern": "[0-9]{10}",
                    "inputmode": "numeric",
                }
            ),
            "fonction": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Fonction",
                }
            ),
            "typeTravail": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "typeContrat": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "psalaire": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Salaire",
                }
            ),
            "debutContrat": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "finContrat": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "lieuTravail": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Lieu de travail",
                }
            ),
            "categorie": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "photo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["categorie"].queryset = Categorie.objects.all().order_by("nom")

        # Champs facultatifs
        self.fields["prenom"].required = False
        self.fields["adresse"].required = False
        self.fields["finContrat"].required = False
        self.fields["lieuTravail"].required = False
        self.fields["categorie"].required = False

        # Classe Bootstrap pour tous les champs
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_nom(self):
        nom = self.cleaned_data.get("nom")

        if nom:
            return nom.strip().upper()

        return nom

    def clean_prenom(self):
        prenom = self.cleaned_data.get("prenom")

        if prenom:
            return prenom.strip().title()

        return prenom

    def clean_telephone(self):
        telephone = self.cleaned_data.get("telephone")

        if telephone:

            telephone = telephone.strip()

            if not telephone.isdigit():
                raise forms.ValidationError(
                    "Le téléphone doit contenir uniquement des chiffres."
                )

            if len(telephone) != 10:
                raise forms.ValidationError(
                    "Le numéro doit contenir exactement 10 chiffres."
                )

        return telephone

    def clean(self):
        cleaned_data = super().clean()

        debut = cleaned_data.get("debutContrat")
        fin = cleaned_data.get("finContrat")

        if debut and fin and fin < debut:
            raise forms.ValidationError(
                "La date de fin du contrat ne peut pas être "
                "antérieure à la date de début."
            )

        return cleaned_data


class H_PersonnelForm(forms.ModelForm):

    class Meta:
        model = H_Personnel

        fields = [
            "nom",
            "prenom",
            "adresse",
            "telephone",
            "cin",
            "salaire",
            "typeContrat",
            "debutContrat",
            "finContrat",
            "categorie",
        ]

        widgets = {
            "nom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom",
                }
            ),
            "prenom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Prénom",
                }
            ),
            "adresse": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Adresse",
                    "style": "resize:none;",
                }
            ),
            "telephone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Téléphone",
                    "maxlength": "10",
                }
            ),
            "cin": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Numéro CIN",
                    "maxlength": "10",
                    "title": "Le numéro CIN doit contenir exactement 10 caractères.",
                }
            ),
            "salaire": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Salaire",
                }
            ),
            "typeContrat": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "debutContrat": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "finContrat": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "categorie": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Le champ categorie est un CharField avec choices
        # défini dans le modèle H_Personnel.
        # Aucun queryset H_Categorie n'est nécessaire.

        self.fields["prenom"].required = False
        self.fields["adresse"].required = False
        self.fields["finContrat"].required = False
        self.fields["categorie"].required = False

        # Appliquer les classes Bootstrap
        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "form-control",
            )

    def clean_nom(self):
        nom = self.cleaned_data.get("nom")
        return nom.strip().upper() if nom else nom

    def clean_prenom(self):
        prenom = self.cleaned_data.get("prenom")
        return prenom.strip().title() if prenom else prenom

    def clean_cin(self):
        cin = self.cleaned_data.get("cin", "").strip()

        if len(cin) < 6 or cin[5] not in ("1", "2"):
            raise forms.ValidationError("Le 6e chiffre du CIN doit être 1 ou 2.")

        return cin

    def clean_telephone(self):
        telephone = self.cleaned_data.get("telephone")

        if telephone:
            telephone = telephone.strip()

            if not telephone.isdigit():
                raise forms.ValidationError(
                    "Le téléphone doit contenir uniquement des chiffres."
                )

            if len(telephone) != 10:
                raise forms.ValidationError(
                    "Le numéro doit contenir exactement 10 chiffres."
                )

        return telephone

    def clean_salaire(self):
        salaire = self.cleaned_data.get("salaire")

        if salaire is not None and salaire < 0:
            raise forms.ValidationError("Le salaire ne peut pas être négatif.")

        return salaire

    def clean(self):
        cleaned_data = super().clean()

        debut = cleaned_data.get("debutContrat")
        fin = cleaned_data.get("finContrat")

        if debut and fin and fin < debut:
            self.add_error(
                "finContrat",
                "La fin du contrat doit être postérieure "
                "ou égale à la date de début.",
            )

        return cleaned_data
