from django import forms
from .models import Depot, Distribution


class DepotForm(forms.ModelForm):

    class Meta:
        model = Depot

        fields = [
            'montantG',
        ]

        widgets = {

            'montantG': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Montant global'
                }
            ),
        }


class DistributionForm(forms.ModelForm):

    class Meta:
        model = Distribution

        fields = [
            'distributeur',
            'montant',
        ]

        widgets = {

            'distributeur': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),

            'montant': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Montant reçu'
                }
            ),
        }