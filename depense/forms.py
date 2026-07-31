from django import forms

from .models import Depense
from depot.models import Distribution



class DepenseForm(forms.ModelForm):

    class Meta:

        model = Depense

        fields = [            'titre',
            'distribution',
            'montant',
            'description'
        ]


        widgets = {

            'titre': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Titre de la dépense'
                }
            ),


            'distribution': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),


            'montant': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01'
                }
            ),


            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3
                }
            ),

        }



    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)


        self.fields['distribution'].queryset = (
            Distribution.objects
            .select_related(
                'distributeur',
                'depot'
            )
            .order_by(
                '-depot__date'
            )
        )


        self.fields['distribution'].label_from_instance = (
            lambda obj:
            f"{obj.distributeur} - {obj.montant:,.0f} Ar"
        )



    def clean(self):

        cleaned = super().clean()


        distribution = cleaned.get(
            'distribution'
        )

        montant = cleaned.get(
            'montant'
        )


        if distribution and montant:


            from django.db.models import Sum


            total = Depense.objects.filter(
                distribution=distribution
            )


            if self.instance.pk:

                total = total.exclude(
                    pk=self.instance.pk
                )


            deja_depense = total.aggregate(
                somme=Sum('montant')
            )['somme'] or 0



            reste = (
                distribution.montant
                -
                deja_depense
            )



            if montant > reste:

                self.add_error(
                    'montant',
                    f"Disponible pour {distribution.distributeur} : {reste:,.0f} Ar"
                )


        return cleaned