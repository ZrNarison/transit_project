from django import forms
from .models import Client

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = "__all__"

        widgets = {
            "nom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "type": "text",
                    "placeholder": "Nom",   # calendrier HTML5
                }
            ),
            "prenom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "type": "text",
                    "placeholder": "Prénom",   # calendrier HTML5
                }
            ),
            "date_naissance": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                    "placeholder": "Date de naissance",   # calendrier HTML5
                }
            ),
            "lieu_naissance": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "type": "text",
                    "placeholder": "Lieu de naissance",   # calendrier HTML5
                }
            ),
            "nom_pere": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "type": "text",
                    "placeholder": "Filiation père",   # calendrier HTML5
                }
            ),
            "nom_mere": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "type": "text",
                    "placeholder": "Filiation mere",   # calendrier HTML5
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
                    "placeholder": "0340100001",
                    "pattern": "[0-9]{10}",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            # Ne pas écraser les attributs déjà définis
            field.widget.attrs.setdefault("class", "form-control")