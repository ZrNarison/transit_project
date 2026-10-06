from django import forms
from .models import h_DepenseSoc


class h_DepenseSocForm(forms.ModelForm):

    titre = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Titre de la dépense"
            }
        )
    )

    montant = forms.DecimalField(
        required=True,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "step": "1",
                "placeholder": "Montant"
            }
        )
    )

    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Description"
            }
        )
    )

    date = forms.DateField(
        required=True,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date"
            }
        )
    )

    class Meta:
        model = DepenseSoc

        fields = [
            "titre",
            "montant",
            "description",
            "date",
        ]