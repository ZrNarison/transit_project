from django import forms
from .models import MaterielEntre


from django import forms
from .models import MaterielEntre


class MaterielEntreForm(forms.ModelForm):

    class Meta:
        model = MaterielEntre
        fields = "__all__"

        widgets = {
            "id_MaterielSort": forms.Select(attrs={
                "class": "form-select"
            }),

            "Nb_Entre": forms.NumberInput(attrs={
                "class": "form-control"
            }),

            "observation": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
            }),
        }

        # def __init__(self, *args, **kwargs):
        # super().__init__(*args, **kwargs)
        # self.fields["id_MaterielSort"].queryset = MaterielSort.objects.order_by("-dateAv")