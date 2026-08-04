from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from depot.models import Depot
from .forms import DepenseForm
from .models import Depense


class DepenseModuleTests(TestCase):
    def test_depense_list_route_exists(self):
        response = self.client.get(reverse('depense:depense_list'))
        self.assertEqual(response.status_code, 200)

    def test_depense_search_filters_by_provided_fields(self):
        depense = Depense.objects.create(titre='Transport', montant=Decimal('150.00'), description='Taxi')
        Depense.objects.create(titre='Loyer', montant=Decimal('500.00'), description='Location')

        response = self.client.get(reverse('depense:depense_list'), {'titre': 'Trans', 'montant': '150', 'description': 'Taxi'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['depenses']), [depense])


    def test_depense_validation_uses_total_available_amount_across_all_depots(self):
        depot_1 = Depot.objects.create(nom='Dépôt 1', montant=Decimal('5.00'))
        Depot.objects.create(nom='Dépôt 2', montant=Decimal('6.00'))
        Depot.objects.create(nom='Dépôt 3', montant=Decimal('4.00'))

        form = DepenseForm(data={
            'titre': 'Achat',
            'depot': depot_1.id,
            'montant': '6.00',
            'description': 'Test',
        })

        self.assertTrue(form.is_valid(), form.errors)
