import os

import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "transit_project.settings",
)
django.setup()

from projet.models import EquipeProjet, PersonnelExecutionProjet

for execution in PersonnelExecutionProjet.objects.filter(
    type_class__in=["CHEF_EQUIPE", "MINIER"]
).select_related("projet"):
    print("-" * 50)
    print("ID :", execution.pk)
    print("Type :", execution.type_class)
    print("Nom :", execution.nom)
    print("Projet :", execution.projet_id)
    print("Date début :", execution.date_debut)
    print("Date fin :", execution.date_fin)

    affectations = EquipeProjet.objects.filter(
        projet=execution.projet,
        personnel_execution=execution,
    )

    print("Affectations existantes :", affectations.count())
    print(
        "Affectations :",
        list(affectations.values("id", "fonction", "date_debut", "date_fin")),
    )
