from django.db.models import Sum
from projet.models import Projet, MateriauProjet, ReceptionMateriauProjet

for projet in Projet.objects.all().order_by("id"):
    print("\n=== PROJET {} : {} ===".format(projet.pk, projet.titre))

    materiaux = MateriauProjet.objects.filter(projet_id=projet.pk).order_by("materiau", "id")

    if not materiaux.exists():
        print("AUCUN MATERIAU ENREGISTRE")
        continue

    for materiau in materiaux:
        recu = ReceptionMateriauProjet.objects.filter(
            materiau_projet_id=materiau.pk
        ).aggregate(total=Sum("quantite_recue"))["total"]

        print(
            "ID={} | Materiau={} | Unite={} | Prevu={} | Recu={}".format(
                materiau.pk,
                materiau.materiau,
                materiau.unite,
                materiau.quantite_prevue,
                recu or 0,
            )
        )
