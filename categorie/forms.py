from django import forms
from .models import categorie

class categorieForm(forms.ModelForm):
    class Meta:
        model = categorie
        fields = [
            'nom'
        ]
        widgets = {
            "nom":forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Tapez ici le class d'utilisateur"
            })
        }
        