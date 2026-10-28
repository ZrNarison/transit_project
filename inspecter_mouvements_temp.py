from projet.models import MouvementMateriauProjet

for m in MouvementMateriauProjet.objects.filter(
    materiau_projet__projet_id=1
).select_related("materiau_projet").order_by("id"):
    print(
        f"ID={m.pk} | "
        f"Matériau={m.materiau_projet.materiau} | "
        f"Unité={m.materiau_projet.unite} | "
        f"Type={m.type_mouvement} | "
        f"Quantité={m.quantite} | "
        f"Prix unitaire={m.prix_unitaire} | "
        f"Point départ={m.point_depart_id} | "
        f"Point arrivée={m.point_arrivee_id}"
    )
