from django.db.models import Q
from projet.models import (
    Projet,
    MateriauProjet,
    ReceptionMateriauProjet,
    DistributionMateriauProjet,
    ConsommationMateriauProjet,
    RetourMateriauProjet,
    MouvementMateriauProjet,
)

for projet in Projet.objects.all().order_by("id"):
    materiaux = MateriauProjet.objects.filter(projet=projet)
    receptions = ReceptionMateriauProjet.objects.filter(
        materiau_projet__projet=projet
    )
    distributions = DistributionMateriauProjet.objects.filter(
        materiau_projet__projet=projet
    )
    consommations = ConsommationMateriauProjet.objects.filter(
        Q(distribution__materiau_projet__projet=projet)
        | Q(reception_directe__materiau_projet__projet=projet)
    )
    retours = RetourMateriauProjet.objects.filter(
        Q(distribution__materiau_projet__projet=projet)
        | Q(reception_directe__materiau_projet__projet=projet)
    )
    mouvements = MouvementMateriauProjet.objects.filter(
        materiau_projet__projet=projet
    )

    print(f"\nProjet {projet.pk} : {projet.titre}")
    print(f"  Matériaux             : {materiaux.count()}")
    print(f"  Réceptions classiques : {receptions.count()}")
    print(f"  Distributions         : {distributions.count()}")
    print(f"  Consommations         : {consommations.count()}")
    print(f"  Retours               : {retours.count()}")
    print(f"  Mouvements unifiés    : {mouvements.count()}")
