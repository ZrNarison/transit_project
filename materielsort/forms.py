from django import forms
from .models import MaterielSort
from materiels.models import Materiels


class MaterielSortForm(forms.ModelForm):

    class Meta:
        model = MaterielSort
        fields = "__all__"

        widgets = {
            "id_Materiel": forms.Select(attrs={
                "class": "form-select"
            }),

            "demandeur": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nom du demandeur"
            }),

            "responsable_sortie": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Responsable de la sortie du matériel"
            }),

            "Nb_MatSort": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre de matériel à sortir"
            }),

            "observation": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Observations éventuelles",
                "rows": 3
            }),
        }


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        ids = []
        deja_vu = set()

        for m in Materiels.objects.order_by(
            "nom",
            "typeMat",
            "catMat"
        ):

            cle = (
                m.nom,
                m.typeMat,
                m.catMat
            )

            if cle not in deja_vu:
                deja_vu.add(cle)
                ids.append(m.id)


        self.fields["id_Materiel"].queryset = Materiels.objects.filter(
            id__in=ids
        ).order_by(
            "nom",
            "typeMat",
            "catMat"
        )