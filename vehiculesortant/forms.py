from django import forms
from .models import VehiculeSortant


class VehiculeSortantForm(forms.ModelForm):
    class Meta:
        model = VehiculeSortant
        fields = '__all__'
        widgets = {
            'chauffeur': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chauffeur'}),
            'cin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro CIN', 'maxlength': '12'}),
            'num_vehicule': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro véhicule', 'maxlength': '8'}),
            'permis': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro permis'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro téléphone', 'maxlength': '10'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Adresse', 'rows': 3}),
            'remorque': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Remorque'}),

            "montant": forms.NumberInput(attrs={"class": "form-control","placeholder": "Montant transporter","min": "0"}),

            'ticket': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ticket'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
