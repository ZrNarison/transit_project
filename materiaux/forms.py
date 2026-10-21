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
    MateriauxRetour,
    PaiementDocker,
    ReceptionMateriau,
    ReparationVehicule,
    UtilisationMateriau,
    Vehicule,
)


class BootstrapModelForm(forms.ModelForm):
    """Style Bootstrap commun aux formulaires du module MCCR."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = (widget.attrs.get("class", "") + " " + css).strip()
            if isinstance(widget, forms.DateInput):
                widget.attrs.setdefault("type", "date")
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("rows", 3)
            # Empêche de sélectionner des objets GALAXY dans les formulaires MCCR.
            if hasattr(field, "queryset"):
                related_model = field.queryset.model
                if any(
                    model_field.name == "entreprise"
                    for model_field in related_model._meta.fields
                ):
                    field.queryset = field.queryset.filter(entreprise="MCCR")


class MateriauxForm(BootstrapModelForm):
    class Meta:
        model = Materiaux
        fields = ["libelle", "unite"]


class MateriauxEntreeForm(BootstrapModelForm):
    class Meta:
        model = MateriauxEntree
        fields = ["materiau", "entree", "date_entree", "destination", "vehicule"]
        widgets = {
            "date_entree": forms.DateInput(attrs={"type": "date"}),
            "entree": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
        }

    def clean_entree(self):
        value = self.cleaned_data["entree"]
        if value <= 0:
            raise forms.ValidationError(
                "La quantité entrée doit être supérieure à zéro."
            )
        return value


class MateriauxDivisionForm(BootstrapModelForm):
    class Meta:
        model = MateriauxDivision
        fields = ["entree", "destination", "quantite", "date_division"]
        widgets = {
            "date_division": forms.DateInput(attrs={"type": "date"}),
            "quantite": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
        }

    def clean_quantite(self):
        value = self.cleaned_data["quantite"]
        if value <= 0:
            raise forms.ValidationError("La quantité doit être supérieure à zéro.")
        return value


class MateriauxOutForm(BootstrapModelForm):
    class Meta:
        model = MateriauxOut
        fields = [
            "division",
            "quantite",
            "date_sortie",
            "destination",
            "vehicule",
            "projet",
            "point_projet",
        ]
        widgets = {
            "date_sortie": forms.DateInput(attrs={"type": "date"}),
            "quantite": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
        }

    def clean_quantite(self):
        value = self.cleaned_data["quantite"]
        if value <= 0:
            raise forms.ValidationError(
                "La quantité sortie doit être supérieure à zéro."
            )
        return value


class VehiculeForm(BootstrapModelForm):
    class Meta:
        model = Vehicule
        fields = ["immatriculation", "marque", "modele", "kilometrage", "actif"]
        widgets = {"kilometrage": forms.NumberInput(attrs={"min": "0", "step": "0.01"})}


class CategorieDepenseForm(BootstrapModelForm):
    class Meta:
        model = CategorieDepense
        fields = ["nom", "description", "actif"]


class ActiviteTransportForm(BootstrapModelForm):
    class Meta:
        model = ActiviteTransport
        fields = [
            "date_activite",
            "vehicule",
            "conducteur",
            "chauffeur_personnel",
            "mission",
            "lieu_depart",
            "destination",
            "type_transport",
            "quantite",
            "projet",
            "point_projet",
            "sortie_materiau",
            "kilometrage_depart",
            "kilometrage_arrivee",
        ]
        widgets = {
            "date_activite": forms.DateInput(attrs={"type": "date"}),
            "quantite": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "kilometrage_depart": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "kilometrage_arrivee": forms.NumberInput(
                attrs={"min": "0", "step": "0.01"}
            ),
        }


class ReceptionMateriauForm(BootstrapModelForm):
    class Meta:
        model = ReceptionMateriau
        fields = [
            "transport",
            "projet",
            "point",
            "quantite_recue",
            "date_reception",
            "responsable",
            "observation",
        ]
        widgets = {
            "date_reception": forms.DateInput(attrs={"type": "date"}),
            "quantite_recue": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
        }


class UtilisationMateriauForm(BootstrapModelForm):
    class Meta:
        model = UtilisationMateriau
        fields = ["reception", "quantite_utilisee", "date_utilisation", "observation"]
        widgets = {
            "date_utilisation": forms.DateInput(attrs={"type": "date"}),
            "quantite_utilisee": forms.NumberInput(
                attrs={"min": "0.01", "step": "0.01"}
            ),
        }


class MateriauxRetourForm(BootstrapModelForm):
    class Meta:
        model = MateriauxRetour
        fields = ["sortie", "reception", "quantite", "date_retour", "observation"]
        widgets = {
            "date_retour": forms.DateInput(attrs={"type": "date"}),
            "quantite": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
        }


class PaiementDockerForm(BootstrapModelForm):
    class Meta:
        model = PaiementDocker
        fields = ["date_activite", "activite", "projet", "montant", "observation"]
        widgets = {
            "date_activite": forms.DateInput(attrs={"type": "date"}),
            "montant": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
        }


class DepenseForm(BootstrapModelForm):
    class Meta:
        model = Depense
        fields = [
            "date_depense",
            "designation",
            "categorie",
            "vehicule",
            "projet",
            "montant",
            "localisation",
            "observation",
        ]
        widgets = {
            "date_depense": forms.DateInput(attrs={"type": "date"}),
            "montant": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
        }


class DepenseGasoilForm(BootstrapModelForm):
    class Meta:
        model = DepenseGasoil
        fields = [
            "date_gasoil",
            "vehicule",
            "projet",
            "quantite_litre",
            "prix_unitaire",
        ]
        widgets = {
            "date_gasoil": forms.DateInput(attrs={"type": "date"}),
            "quantite_litre": forms.NumberInput(
                attrs={"min": "0.001", "step": "0.001"}
            ),
            "prix_unitaire": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }


class ReparationVehiculeForm(BootstrapModelForm):
    class Meta:
        model = ReparationVehicule
        fields = [
            "date_reparation",
            "vehicule",
            "chauffeur",
            "chauffeur_personnel",
            "projet",
            "designation",
            "type_reparation",
            "garage",
            "quantite",
            "unite",
            "prix_unitaire",
            "montant_main_oeuvre",
            "Cout",
            "photo_piece_remplacee",
            "photo_piece_remplacante",
        ]
        widgets = {
            "date_reparation": forms.DateInput(attrs={"type": "date"}),
            "quantite": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
            "prix_unitaire": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "montant_main_oeuvre": forms.NumberInput(
                attrs={"min": "0", "step": "0.01"}
            ),
            "Cout": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }
