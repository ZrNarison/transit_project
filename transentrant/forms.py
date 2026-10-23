from django import forms

from .models import Transentrant


class TransentrantForm(forms.ModelForm):
    class Meta:
        model = Transentrant
        fields = "__all__"

        widgets = {
            # "id_client": forms.Select(attrs={"class": "form-control"}),
            "chauffeur": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Chauffeur"}
            ),
            "cin": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Numéro Carte d'identité National",
                    "maxlength": "12",
                }
            ),
            "num_vehicule": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Numéro véhicule",
                    "maxlength": "8",
                }
            ),
            "permis": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Numéro permis"}
            ),
            "telephone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Numéro télephone",
                    "maxlength": "10",
                }
            ),
            "adresse": forms.Textarea(
                attrs={"class": "form-control", "placeholder": "Adresse", "rows": 3}
            ),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean_cin(self):
            cin = self.cleaned_data.get("cin", "").strip()
    
            if len(cin) < 6 or cin[5] not in ("1", "2"):
                raise forms.ValidationError("Le 6e chiffre du CIN doit être 1 ou 2.")
    
            return cin
