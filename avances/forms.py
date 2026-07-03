from django import forms
from .models import Avance

class AvanceForm(forms.ModelForm):
    class Meta:
        model = Avance
        fields = ['id_client', 'motifAv', 'montantAv', 'typeAv']