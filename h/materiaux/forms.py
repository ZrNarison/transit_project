from django import forms

from .models import (
    ActiviteTransport,
    CategorieDepense,
    Depense,
    DepenseGasoil,
    Docker,
    Materiaux,
    MateriauxDivision,
    MateriauxEntree,
    MateriauxOut,
    PaiementDocker,
    ReparationVehicule,
    Vehicule,
)


# ==========================================================
# STYLE BOOTSTRAP
# ==========================================================

class BootstrapModelForm(forms.ModelForm):
    """
    Formulaire de base avec styles Bootstrap.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():

            widget = field.widget

            # --------------------------------------------------
            # SELECT
            # --------------------------------------------------
            if isinstance(widget, forms.Select):
                widget.attrs.setdefault(
                    "class",
                    "form-select"
                )

            # --------------------------------------------------
            # CHECKBOX
            # --------------------------------------------------
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault(
                    "class",
                    "form-check-input"
                )

            # --------------------------------------------------
            # TEXTAREA
            # --------------------------------------------------
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault(
                    "class",
                    "form-control"
                )
                widget.attrs.setdefault(
                    "rows",
                    3
                )

            # --------------------------------------------------
            # AUTRES CHAMPS
            # --------------------------------------------------
            else:
                widget.attrs.setdefault(
                    "class",
                    "form-control"
                )

            # --------------------------------------------------
            # PLACEHOLDER
            # --------------------------------------------------
            if (
                not isinstance(widget, forms.CheckboxInput)
                and not isinstance(widget, forms.Select)
                and not widget.attrs.get("placeholder")
            ):
                field.label = field.label or name.replace(
                    "_",
                    " "
                ).capitalize()


# ==========================================================
# MATÉRIAUX
# ==========================================================

class MateriauxForm(BootstrapModelForm):

    class Meta:
        model = Materiaux

        fields = [
            "libelle",
            "unite",
        ]

        widgets = {
            "libelle": forms.TextInput(
                attrs={
                    "placeholder": "Ex : Ciment",
                }
            ),
            "unite": forms.TextInput(
                attrs={
                    "placeholder": "Ex : sac, tonne, m³, kg",
                }
            ),
        }


# ==========================================================
# ENTRÉE ENTREPÔT
# ==========================================================

class MateriauxEntreeForm(BootstrapModelForm):

    class Meta:
        model = MateriauxEntree

        fields = [
            "materiau",
            "entree",
            "date_entree",
            "destination",
            "vehicule",
        ]

        widgets = {
            "date_entree": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "entree": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "destination": forms.TextInput(
                attrs={
                    "placeholder": "Provenance / fournisseur",
                }
            ),
            "vehicule": forms.TextInput(
                attrs={
                    "placeholder": "Véhicule",
                }
            ),
        }


# ==========================================================
# DIVISION ENTREPÔT → MAGASIN
# ==========================================================

class MateriauxDivisionForm(BootstrapModelForm):

    class Meta:
        model = MateriauxDivision

        fields = [
            "entree",
            "destination",
            "quantite",
            "date_division",
        ]

        widgets = {
            "destination": forms.TextInput(
                attrs={
                    "placeholder": "Magasin / Chantier",
                }
            ),
            "quantite": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "date_division": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
        }


# ==========================================================
# SORTIE MAGASIN
# ==========================================================

class MateriauxOutForm(BootstrapModelForm):

    class Meta:
        model = MateriauxOut

        fields = [
            "division",
            "quantite",
            "date_sortie",
            "destination",
            "vehicule",
        ]

        widgets = {
            "quantite": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "date_sortie": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "destination": forms.TextInput(
                attrs={
                    "placeholder": "Destination / Utilisation",
                }
            ),
            "vehicule": forms.TextInput(
                attrs={
                    "placeholder": "Véhicule",
                }
            ),
        }


# ==========================================================
# VÉHICULE
# ==========================================================

class VehiculeForm(BootstrapModelForm):

    class Meta:
        model = Vehicule

        fields = [
            "immatriculation",
            "marque",
            "modele",
            "kilometrage",
            "actif",
        ]

        widgets = {
            "immatriculation": forms.TextInput(
                attrs={
                    "placeholder": "Ex : 1234 TAB",
                }
            ),
            "marque": forms.TextInput(
                attrs={
                    "placeholder": "Ex : Mercedes",
                }
            ),
            "modele": forms.TextInput(
                attrs={
                    "placeholder": "Ex : Actros",
                }
            ),
            "kilometrage": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "actif": forms.CheckboxInput(),
        }


# ==========================================================
# DOCKER
# ==========================================================

class DockerForm(BootstrapModelForm):

    class Meta:
        model = Docker

        fields = [
            "nom",
            "telephone",
            "actif",
        ]

        widgets = {
            "nom": forms.TextInput(
                attrs={
                    "placeholder": "Nom du docker",
                }
            ),
            "telephone": forms.TextInput(
                attrs={
                    "placeholder": "Téléphone",
                }
            ),
            "actif": forms.CheckboxInput(),
        }


# ==========================================================
# CATÉGORIE DE DÉPENSE
# ==========================================================

class CategorieDepenseForm(BootstrapModelForm):

    class Meta:
        model = CategorieDepense

        fields = [
            "nom",
            "description",
            "actif",
        ]

        widgets = {
            "nom": forms.TextInput(
                attrs={
                    "placeholder": "Ex : Transport",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Description",
                }
            ),
            "actif": forms.CheckboxInput(),
        }


# ==========================================================
# ACTIVITÉ DE TRANSPORT
# ==========================================================

class ActiviteTransportForm(BootstrapModelForm):

    class Meta:
        model = ActiviteTransport

        fields = [
            "date_activite",
            "vehicule",
            "materiau",
            "quantite",
            "unite",
            "lieu_chargement",
            "destination",
            "montant_transport",
            "conducteur",
            "observation",
        ]

        widgets = {
            "date_activite": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "quantite": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "montant_transport": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "unite": forms.TextInput(
                attrs={
                    "placeholder": "Ex : tonne, m³",
                }
            ),
            "lieu_chargement": forms.TextInput(
                attrs={
                    "placeholder": "Lieu de chargement",
                }
            ),
            "destination": forms.TextInput(
                attrs={
                    "placeholder": "Destination",
                }
            ),
            "conducteur": forms.TextInput(
                attrs={
                    "placeholder": "Nom du conducteur",
                }
            ),
            "observation": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        quantite = cleaned_data.get("quantite")
        montant = cleaned_data.get("montant_transport")

        if quantite is not None and quantite < 0:
            self.add_error(
                "quantite",
                "La quantité ne peut pas être négative."
            )

        if montant is not None and montant < 0:
            self.add_error(
                "montant_transport",
                "Le montant ne peut pas être négatif."
            )

        return cleaned_data


# ==========================================================
# PAIEMENT DOCKER
# ==========================================================

class PaiementDockerForm(BootstrapModelForm):

    class Meta:
        model = PaiementDocker

        fields = [
            "activite",
            "docker",
            "montant",
            "observation",
        ]

        widgets = {
            "montant": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "observation": forms.TextInput(
                attrs={
                    "placeholder": "Observation",
                }
            ),
        }


# ==========================================================
# DÉPENSE GÉNÉRALE
# ==========================================================

class DepenseForm(BootstrapModelForm):

    class Meta:
        model = Depense

        fields = [
            "date_depense",
            "categorie",
            "designation",
            "quantite",
            "unite",
            "prix_unitaire",
            "vehicule",
            "activite",
            "materiau",
            "localisation",
            "observation",
        ]

        widgets = {
            "date_depense": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "designation": forms.TextInput(
                attrs={
                    "placeholder": "Désignation de la dépense",
                }
            ),
            "quantite": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "unite": forms.TextInput(
                attrs={
                    "placeholder": "Ex : unité, litre, kg",
                }
            ),
            "prix_unitaire": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "localisation": forms.TextInput(
                attrs={
                    "placeholder": "Lieu / chantier",
                }
            ),
            "observation": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        quantite = cleaned_data.get("quantite")
        prix_unitaire = cleaned_data.get("prix_unitaire")

        if quantite is not None and quantite < 0:
            self.add_error(
                "quantite",
                "La quantité ne peut pas être négative."
            )

        if prix_unitaire is not None and prix_unitaire < 0:
            self.add_error(
                "prix_unitaire",
                "Le prix unitaire ne peut pas être négatif."
            )

        return cleaned_data


# ==========================================================
# DÉPENSE GASOIL
# ==========================================================

class DepenseGasoilForm(BootstrapModelForm):

    class Meta:
        model = DepenseGasoil

        fields = [
            "date_gasoil",
            "vehicule",
            "activite",
            "quantite_litre",
            "prix_litre",
            "station",
            "kilometrage",
            "observation",
        ]

        widgets = {
            "date_gasoil": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "quantite_litre": forms.NumberInput(
                attrs={
                    "step": "0.001",
                    "min": "0.001",
                }
            ),
            "prix_litre": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "station": forms.TextInput(
                attrs={
                    "placeholder": "Station / fournisseur",
                }
            ),
            "kilometrage": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "observation": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        quantite = cleaned_data.get("quantite_litre")
        prix = cleaned_data.get("prix_litre")

        if quantite is not None and quantite <= 0:
            self.add_error(
                "quantite_litre",
                "La quantité doit être supérieure à zéro."
            )

        if prix is not None and prix < 0:
            self.add_error(
                "prix_litre",
                "Le prix du litre ne peut pas être négatif."
            )

        return cleaned_data


# ==========================================================
# RÉPARATION / ENTRETIEN VÉHICULE
# ==========================================================

class ReparationVehiculeForm(BootstrapModelForm):

    class Meta:
        model = ReparationVehicule

        fields = [
            "date_reparation",
            "vehicule",
            "activite",
            "type_reparation",
            "designation",
            "quantite",
            "unite",
            "prix_unitaire",
            "garage",
            "kilometrage",
            "observation",
        ]

        widgets = {
            "date_reparation": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "type_reparation": forms.Select(),
            "designation": forms.TextInput(
                attrs={
                    "placeholder": (
                        "Ex : Pneu, huile moteur, embrayage..."
                    ),
                }
            ),
            "quantite": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "unite": forms.TextInput(
                attrs={
                    "placeholder": "Ex : pièce, litre",
                }
            ),
            "prix_unitaire": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "garage": forms.TextInput(
                attrs={
                    "placeholder": "Garage / fournisseur",
                }
            ),
            "kilometrage": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "observation": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        quantite = cleaned_data.get("quantite")
        prix = cleaned_data.get("prix_unitaire")

        if quantite is not None and quantite <= 0:
            self.add_error(
                "quantite",
                "La quantité doit être supérieure à zéro."
            )

        if prix is not None and prix < 0:
            self.add_error(
                "prix_unitaire",
                "Le prix unitaire ne peut pas être négatif."
            )

        return cleaned_data