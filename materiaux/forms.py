from django import forms

from .models import (
    ActiviteTransport,
    CategorieDepense,
    Depense,
    DepenseGasoil,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():

            widget = field.widget

            if isinstance(widget, forms.Select):
                widget.attrs.setdefault(
                    "class",
                    "form-select"
                )

            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault(
                    "class",
                    "form-check-input"
                )

            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault(
                    "class",
                    "form-control"
                )
                widget.attrs.setdefault(
                    "rows",
                    3
                )

            else:
                widget.attrs.setdefault(
                    "class",
                    "form-control"
                )


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
            "entree": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "date_entree": forms.DateInput(
                attrs={
                    "type": "date",
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

    def clean_entree(self):
        entree = self.cleaned_data.get("entree")

        if entree is not None and entree <= 0:
            raise forms.ValidationError(
                "La quantité entrée doit être supérieure à zéro."
            )

        return entree


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

    def clean_quantite(self):
        quantite = self.cleaned_data.get("quantite")

        if quantite is not None and quantite <= 0:
            raise forms.ValidationError(
                "La quantité doit être supérieure à zéro."
            )

        return quantite


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
                    "placeholder": "Destination / utilisation",
                }
            ),
            "vehicule": forms.TextInput(
                attrs={
                    "placeholder": "Véhicule",
                }
            ),
        }

    def clean_quantite(self):
        quantite = self.cleaned_data.get("quantite")

        if quantite is not None and quantite <= 0:
            raise forms.ValidationError(
                "La quantité doit être supérieure à zéro."
            )

        return quantite


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

    def clean_immatriculation(self):
        immatriculation = self.cleaned_data.get(
            "immatriculation"
        )

        if immatriculation:
            immatriculation = immatriculation.strip().upper()

        return immatriculation


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
# ACTIVITÉ DE TRANSPORT / DÉPLACEMENT VÉHICULE
# ==========================================================

class ActiviteTransportForm(BootstrapModelForm):

    class Meta:
        model = ActiviteTransport

        fields = [
            "date_activite",
            "vehicule",
            "conducteur",
            "mission",
            "lieu_depart",
            "destination",
            "type_transport",
            "quantite",
        ]

        widgets = {
            "date_activite": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),

            "vehicule": forms.Select(),

            "conducteur": forms.TextInput(
                attrs={
                    "placeholder": "Nom du chauffeur",
                }
            ),

            "mission": forms.TextInput(
                attrs={
                    "placeholder": "Mission",
                }
            ),

            "quantite": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Nombre",
                }
            ),

            "lieu_depart": forms.TextInput(
                attrs={
                    "placeholder": "Lieu de départ",
                }
            ),

            "destination": forms.TextInput(
                attrs={
                    "placeholder": "Destination",
                }
            ),

            "type_transport": forms.Select(),

            
        }

        labels = {
            "date_activite": "Date",
            "vehicule": "N° Auto",
            "conducteur": "Chauffeur",
            "mission": "Mission",
            "lieu_depart": "Départ",
            "destination": "Destination",
            "type_transport": (
                "Personnel / Matériels / Matériaux"
            ),
            # "designation": "Désignation",
            "quantite": "Nombre",
        }

    def clean_quantite(self):
        quantite = self.cleaned_data.get("quantite")

        if quantite is not None and quantite < 0:
            raise forms.ValidationError(
                "Le nombre ne peut pas être négatif."
            )

        return quantite

# ==========================================================
# PAIEMENT DOCKER
# ==========================================================

class PaiementDockerForm(BootstrapModelForm):

    class Meta:
        model = PaiementDocker

        fields = [
            "date_activite",
            "activite",
            "montant",
            "observation",
        ]

        widgets = {
            "date_activite": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "activite": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "montant": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "Montant du paiement",
                }
            ),
            "observation": forms.TextInput(
                attrs={
                    "placeholder": "Observation",
                }
            ),
        }

    def clean_montant(self):
        montant = self.cleaned_data.get("montant")

        if montant is None or montant <= 0:
            raise forms.ValidationError(
                "Le montant doit être supérieur à zéro."
            )

        return montant


# ==========================================================
# DÉPENSE
# ==========================================================

class DepenseForm(BootstrapModelForm):

    class Meta:
        model = Depense

        fields = [
            "date_depense",
            "designation",
            "montant",
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
                    "placeholder": "Ex : pièce, jour, litre",
                }
            ),
            "prix_unitaire": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "vehicule": forms.Select(),
            "activite": forms.Select(),
            "materiau": forms.Select(),
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
            "quantite_litre",
        ]

        widgets = {
            "date_gasoil": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "vehicule": forms.Select(),
            "quantite_litre": forms.NumberInput(
                attrs={
                    "step": "0.001",
                    "min": "0.001",
                    "placeholder": "Litres",
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
                "La quantité de gasoil doit être supérieure à zéro."
            )

        return cleaned_data


# ==========================================================
# RÉPARATION / CHANGEMENT DE PIÈCE VÉHICULE
# ==========================================================
class ReparationVehiculeForm(BootstrapModelForm):
    class Meta:
        model = ReparationVehicule

        fields = [
            "date_reparation",
            "vehicule",
            "chauffeur",
            "designation",
            "type_reparation",
            "garage",
            "quantite",
            "unite",
            "prix_unitaire",
            "montant_main_oeuvre",
            "photo_piece_remplacee",
            "photo_piece_remplacante",
        ]

        widgets = {
            "date_reparation": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            "vehicule": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "chauffeur": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom du chauffeur",
                }
            ),

            "designation": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex : réparation moteur",
                }
            ),

            "type_reparation": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "garage": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom du garage",
                }
            ),

            "quantite": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0.01",
                }
            ),

            "unite": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex : pièce, litre, jeu...",
                }
            ),

            "prix_unitaire": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "montant_main_oeuvre": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "photo_piece_remplacee": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),

            "photo_piece_remplacante": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
        }

        labels = {
            "date_reparation": "Date",
            "vehicule": "Véhicule",
            "chauffeur": "Chauffeur",
            "designation": "Désignation",
            "type_reparation": "Type de réparation",
            "garage": "Garage",
            "quantite": "Quantité",
            "unite": "Unité",
            "prix_unitaire": "Prix unitaire",
            "montant_main_oeuvre": "Main d'œuvre",
            "photo_piece_remplacee": "Ancien piéce",
            "photo_piece_remplacante": "Nouveau piéce",
        }