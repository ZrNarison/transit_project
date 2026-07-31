from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

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
