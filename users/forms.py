from django import forms

from .models import AppUser, H_AppUser
from personnel.models import Personnel, H_Personnel


# ============================================================
# FORMULAIRE UTILISATEUR PRINCIPAL
# Source : Personnel
# ============================================================
class UserForm(forms.ModelForm):

    password = forms.CharField(
        label="Mot de passe",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password",
        }),
    )

    confirm_password = forms.CharField(
        label="Confirmer le mot de passe",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password",
        }),
    )

    class Meta:
        model = AppUser
        fields = [
            "personnel",
            "username",
            "email",
            "password",
            "confirm_password",
            "role",
            "photo",
        ]

        widgets = {
            "personnel": forms.Select(attrs={
                "class": "form-select",
            }),
            "username": forms.TextInput(attrs={
                "class": "form-control",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
            }),
            "role": forms.Select(attrs={
                "class": "form-select",
            }),
            "photo": forms.ClearableFileInput(attrs={
                "class": "form-control",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Liste exclusivement issue de Personnel.
        queryset = Personnel.objects.all().order_by(
            "nom", "prenom"
        )

        # Exclure les personnels déjà liés à un autre AppUser.
        queryset = queryset.exclude(user__isnull=False)

        # En modification, conserver le personnel du compte actuel.
        if self.instance.pk and self.instance.personnel_id:
            queryset = (
                Personnel.objects.filter(
                    pk=self.instance.personnel_id
                ) | queryset
            )

        self.fields["personnel"].queryset = queryset.distinct()
        self.fields["personnel"].label = "Personnel"
        self.fields["personnel"].required = True

        if not self.instance.pk:
            self.fields["password"].required = True
            self.fields["confirm_password"].required = True

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if not self.instance.pk:
            if not password:
                self.add_error(
                    "password",
                    "Le mot de passe est obligatoire."
                )

            if not confirm:
                self.add_error(
                    "confirm_password",
                    "Veuillez confirmer le mot de passe."
                )

        if password and password != confirm:
            self.add_error(
                "confirm_password",
                "Les mots de passe ne correspondent pas."
            )

        return cleaned_data


# ============================================================
# FORMULAIRE UTILISATEUR H
# Source : H_Personnel
# ============================================================
class H_UserForm(forms.ModelForm):

    password = forms.CharField(
        label="Mot de passe",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password",
        }),
    )

    class Meta:
        model = H_AppUser
        fields = [
            "personnel",
            "username",
            "email",
            "password",
            "role",
            "photo",
        ]

        widgets = {
            "personnel": forms.Select(attrs={
                "class": "form-select",
            }),
            "username": forms.TextInput(attrs={
                "class": "form-control",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
            }),
            "role": forms.Select(attrs={
                "class": "form-select",
            }),
            "photo": forms.ClearableFileInput(attrs={
                "class": "form-control",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # IMPORTANT : uniquement H_Personnel.
        queryset = H_Personnel.objects.all().order_by(
            "nom", "prenom"
        )

        # Exclure les personnes déjà associées à un autre H_AppUser.
        queryset = queryset.exclude(
            historique_user__isnull=False
        )

        # En modification, conserver le personnel H du compte actuel.
        if self.instance.pk and self.instance.personnel_id:
            queryset = (
                H_Personnel.objects.filter(
                    pk=self.instance.personnel_id
                ) | queryset
            )

        self.fields["personnel"].queryset = queryset.distinct()
        self.fields["personnel"].label = "Personnel H"
        self.fields["personnel"].required = True

        if not self.instance.pk:
            self.fields["password"].required = True

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")

        if not self.instance.pk and not password:
            self.add_error(
                "password",
                "Le mot de passe est obligatoire."
            )

        return cleaned_data