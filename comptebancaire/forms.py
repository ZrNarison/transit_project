from django import forms
from .models import CompteBancaire

class CompteForm(forms.ModelForm):
    class Meta:
        model = CompteBancaire
        fields = "__all__"