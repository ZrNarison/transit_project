from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Depot


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
