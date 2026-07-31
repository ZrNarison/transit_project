from django import forms
from .models import Personnel

class PersonnelForm(forms.ModelForm):
    class Meta:
        model = Personnel
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
            "adresse": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Adresse",
                    "style": "resize:none;",
                }
            ),
            "fonction": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "maxlength": "10",
                    "placeholder": "fonction",
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

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "form-control"
            })