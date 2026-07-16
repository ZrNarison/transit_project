from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from personnel.models import Personnel
from .models import Salaire


class SalaireModuleTests(TestCase):
    def test_salaire_list_route_exists(self):
        response = self.client.get(reverse('salaire:salaire_list'))
        self.assertEqual(response.status_code, 200)

    def test_salaire_search_filters_by_provided_fields(self):
        personnel = Personnel.objects.create(nom='Rakoto', prenom='Jean', telephone='0320000000', fonction='Employé', categorie='User', photo='images/Personnel/default.png')
        salaire = Salaire.objects.create(personnel=personnel, montant=Decimal('250.00'), reste=Decimal('50.00'))
        other_personnel = Personnel.objects.create(nom='Rabe', prenom='Paul', telephone='0340000000', fonction='Employé', categorie='User', photo='images/Personnel/default.png')
        Salaire.objects.create(personnel=other_personnel, montant=Decimal('300.00'), reste=Decimal('20.00'))

        response = self.client.get(reverse('salaire:salaire_list'), {'personnel': 'Rakoto', 'montant': '250', 'reste': '50'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['salaires']), [salaire])

    def test_salaire_add_requires_personnel(self):
        personnel = Personnel.objects.create(nom='Rajaona', prenom='Alice', telephone='0340000000', fonction='Employé', categorie='User', photo='images/Personnel/default.png')

        response = self.client.post(
            reverse('salaire:salaire_add'),
            {'personnel': personnel.id, 'montant': '300', 'reste': '100'},
        )

        self.assertEqual(response.status_code, 302)
        salaire = Salaire.objects.get(personnel=personnel)
        self.assertEqual(salaire.personnel, personnel)
