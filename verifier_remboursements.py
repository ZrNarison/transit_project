from decimal import Decimal, ROUND_HALF_UP
from produit.models import Produit
from avanceclient.models import AvanceClient

print("\n=== PRODUITS IMPAYÉS ===")
produits = Produit.objects.filter(paye=False).order_by("id")[:20]

for p in produits:
    montant = p.montant_net.quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )
    print(
        f"Produit={p.id} | Client={p.client_id} "
        f"| Montant net arrondi={montant} Ar"
    )

print("\n=== AVANCES DISPONIBLES ===")
avances = AvanceClient.objects.order_by("client_id", "date", "id")

for a in avances:
    if a.reste > 0:
        print(
            f"Avance={a.id} | Client={a.client_id} "
            f"| Montant={a.montant} "
            f"| Utilisé={a.montant_utilise} "
            f"| Retourné={a.montant_retour} "
            f"| Reste={a.reste} Ar"
        )
