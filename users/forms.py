from django import forms
from .models import AppUser
from personnel.models import Personnel


class UserForm(forms.ModelForm):

    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class":"form-control"
            }
        )
    )


    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class":"form-control"
            }
        )
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

            "personnel": forms.Select(
                attrs={
                    "class":"form-select"
                }
            ),


            "username": forms.TextInput(
                attrs={
                    "class":"form-control"
                }
            ),


            "email": forms.EmailInput(
                attrs={
                    "class":"form-control"
                }
            ),


            "role": forms.Select(
                attrs={
                    "class":"form-select"
                }
            ),


            "photo": forms.ClearableFileInput(
                attrs={
                    "class":"form-control"
                }
            ),
        }


    def __init__(self,*args,**kwargs):

        super().__init__(*args,**kwargs)

        self.fields["personnel"].queryset = (
            Personnel.objects
            .order_by("nom","prenom")
        )


    def clean(self):

        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")


        if password and password != confirm:

            raise forms.ValidationError(
                "Les mots de passe ne correspondent pas."
            )


        return cleaned_data