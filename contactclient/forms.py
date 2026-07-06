from django import forms
from .models import ContactClient, CompteBancaire

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactClient
        fields = "__all__"