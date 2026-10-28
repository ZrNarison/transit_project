import os
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "transit_project.settings")
django.setup()

from produit.models import Produit, PaiementProduit
from avanceclient.models import AvanceClient, UtilisationAvanceClient
from depot.models import Distribution

ids = [3, 5, 6]
zero = Decimal("0")

print("\n=== PRODUITS ET PAIEMENTS ===")
for p in Produit.objects.filter(id__in=ids).select_related("client").order_by("id"):
    paiements = PaiementProduit.objects.filter(produit=p)
    total = paiements.aggregate(total=__import__("django.db.models", fromlist=["Sum"]).Sum("montant"))["total"] or zero

    print(
        f"\nProduit {p.id} | Client {p.client_id} | "
        f"Net={p.montant_net} | Payé={p.paye} | "
        f"Paiements={total}"
    )

    avances = AvanceClient.objects.filter(client_id=p.client_id).order_by("date", "id")
    for a in avances:
        utilisations = UtilisationAvanceClient.objects.filter(avance=a).aggregate(
            total=__import__("django.db.models", fromlist=["Sum"]).Sum("montant")
        )["total"] or zero

        print(
            f"  Avance {a.id} | montant={a.montant} | "
            f"utilisé={a.montant_utilise} | retours={a.montant_retour} | "
            f"reste={a.reste} | utilisations liées={utilisations}"
        )

print("\n=== DISTRIBUTIONS AVEC SOLDE POSITIF ===")
total = zero
for d in Distribution.objects.select_related("depot", "distributeur").order_by("depot__date", "id"):
    if d.solde > zero:
        total += d.solde
        print(
            f"Distribution {d.id} | dépôt={d.depot_id} | "
            f"distributeur={d.distributeur} | montant={d.montant} | "
            f"solde={d.solde}"
        )

print(f"\nTOTAL DES SOLDES POSITIFS : {total} Ar")
