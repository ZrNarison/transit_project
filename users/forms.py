from django import forms
from .models import AppUser


class UserForm(forms.ModelForm):

    password = forms.CharField(
        label="Mot de passe",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control"
            }
        )
    )


    confirm_password = forms.CharField(
        label="Confirmation mot de passe",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control"
            }
        )
    )


    class Meta:

        model = AppUser

        fields = [
            "personnel",
            "role",
            "username",
            "email",
            "password",
            "photo",
        ]


        widgets = {

            "personnel": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),


            "role": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),


            "username": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),


            "email": forms.EmailInput(
                attrs={
                    "class": "form-control"
                }
            ),


            "photo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control"
                }
            ),
        }



    def clean(self):

        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")
        personnel = cleaned_data.get("personnel")


        # Vérification mot de passe

        if self.instance.pk:

            if password or confirm:

                if password != confirm:

                    raise forms.ValidationError(
                        "Les mots de passe ne correspondent pas."
                    )


        else:

            if not password:

                raise forms.ValidationError(
                    "Le mot de passe est obligatoire."
                )


            if password != confirm:

                raise forms.ValidationError(
                    "Les mots de passe ne correspondent pas."
                )



        # Un seul compte par personnel

        if personnel:

            existe = AppUser.objects.filter(
                personnel=personnel
            )


            if self.instance.pk:

                existe = existe.exclude(
                    pk=self.instance.pk
                )


            if existe.exists():

                raise forms.ValidationError(
                    "Ce personnel possède déjà un compte utilisateur."
                )


        return cleaned_data