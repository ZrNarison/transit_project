from decimal import Decimal
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "transit_project.settings")
django.setup()

from produit.models import Produit, PaiementProduit
from depot.models import Distribution

print("\n=== PRODUITS 3, 5, 6 ===")
for p in Produit.objects.filter(id__in=[3, 5, 6]).order_by("id"):
    total = sum(
        (x.montant for x in PaiementProduit.objects.filter(produit=p)),
        Decimal("0"),
    )
    print(
        "Produit {} | client={} | net={} | paye={} | paiements={}".format(
            p.id, p.client_id, p.montant_net, p.paye, total
        )
    )

print("\n=== DISTRIBUTIONS A SOLDE POSITIF ===")
total_solde = Decimal("0")

for d in Distribution.objects.select_related("depot").order_by("depot__date", "id"):
    solde = d.solde
    if solde > 0:
        total_solde += solde
        print(
            "Distribution {} | depot={} | montant={} | depenses={} | "
            "avances={} | paiements={} | solde={}".format(
                d.id,
                d.depot_id,
                d.montant,
                d.montant_depenses,
                d.montant_avances,
                d.montant_produits,
                solde,
            )
        )

print("\nTOTAL DES SOLDES POSITIFS : {} Ar".format(total_solde))
