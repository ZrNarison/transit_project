from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from personnel.models import Personnel
from .models import Depot
from .views import DepotForm


class DepotModuleTests(TestCase):
    def test_depot_list_route_exists(self):
        response = self.client.get(reverse('depot:depot_list'))
        self.assertEqual(response.status_code, 200)

    def test_depot_search_filters_by_provided_fields(self):
        depot = Depot.objects.create(nom='Dépôt principal', montant=Decimal('300.00'), description='Versement mensuel')
        Depot.objects.create(nom='Dépôt secondaire', montant=Decimal('75.00'), description='Achat matériel')

        response = self.client.get(reverse('depot:depot_list'), {'nom': 'principal', 'montant': '300', 'description': 'mensuel'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['depots']), [depot])

    def test_depot_can_store_optional_distribution_between_personnels(self):
        personnel_un = Personnel.objects.create(
            nom='Rakoto',
            prenom='Jean',
            telephone='0340000000',
            photo='images/Personnel/default.png',
        )
        personnel_deux = Personnel.objects.create(
            nom='Rabe',
            prenom='Paul',
            telephone='0340000001',
            photo='images/Personnel/default.png',
        )

        depot = Depot.objects.create(
            nom='Dépôt réparti',
            montant=Decimal('5000000.00'),
            description='Répartition 3/2',
            personnel_1=personnel_un,
            personnel_2=personnel_deux,
            part_1=3,
            part_2=2,
        )

        self.assertEqual(depot.montant_reparti_1, Decimal('3000000.00'))
        self.assertEqual(depot.montant_reparti_2, Decimal('2000000.00'))

    def test_depot_form_rejects_parts_that_exceed_total_amount(self):
        form = DepotForm(data={
            'nom': 'Dépôt invalide',
            'montant': '5',
            'part_1': '3',
            'part_2': '3',
            'description': 'Répartition invalide',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('La somme des montants répartis dépasse le montant du dépôt. Réduisez les parts ou corrigez le montant total.', form.errors['__all__'])

    def test_same_personnel_is_removed_from_second_field_during_cleaning(self):
        personnel = Personnel.objects.create(
            nom='Rakoto',
            prenom='Jean',
            telephone='0340000000',
            photo='images/Personnel/default.png',
        )

        form = DepotForm(data={
            'nom': 'Dépôt simple',
            'montant': '100',
            'personnel_1': personnel.id,
            'personnel_2': personnel.id,
            'part_1': '100',
            'description': 'Répartition simple',
        })

        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data['personnel_2'])
