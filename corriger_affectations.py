
import os
import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "transit_project.settings",
)
django.setup()

from django.core.exceptions import ValidationError
from django.db import transaction

from projet.models import PersonnelExecutionProjet, EquipeProjet


TYPES_A_TRAITER = ["CHEF_EQUIPE", "MINIER"]


def creer_affectations():
    print("=" * 65)
    print("CORRECTION DES AFFECTATIONS DES CHEFS ET DES MINIERS")
    print("=" * 65)

    executions = (
        PersonnelExecutionProjet.objects
        .filter(type_class__in=TYPES_A_TRAITER)
        .select_related("projet")
        .order_by("projet_id", "type_class", "id")
    )

    for execution in executions:
        fonction = execution.type_class
        nom = execution.nom
        projet = execution.projet

        print("-" * 65)
        print(
            f"Personnel #{execution.pk} | {fonction} | "
            f"{nom} | Projet #{projet.pk}"
        )

        existante = EquipeProjet.objects.filter(
            projet=projet,
            personnel_execution=execution,
            fonction=fonction,
        ).first()

        if existante:
            print(
                f"EXISTANTE : affectation #{existante.pk}. "
                "Aucune création."
            )
            continue

        if not execution.date_debut:
            print(
                "IGNORÉE : la date réelle de début du travail "
                "n'est pas renseignée."
            )
            continue

        # La date de début réelle est conservée.
        # La date de fin du projet est utilisée uniquement
        # si aucune date de fin individuelle n'est renseignée.
        date_fin = execution.date_fin

        if date_fin is None:
            date_fin = projet.date_fin

        if date_fin is None:
            print(
                "IGNORÉE : aucune date de fin individuelle "
                "ni date de fin du projet n'est disponible."
            )
            continue

        if date_fin < execution.date_debut:
            print(
                "IGNORÉE : la date de fin est antérieure "
                "à la date de début."
            )
            continue

        try:
            with transaction.atomic():
                # Nouvelle vérification avant insertion.
                existante = EquipeProjet.objects.filter(
                    projet=projet,
                    personnel_execution=execution,
                    fonction=fonction,
                ).first()

                if existante:
                    print(
                        f"EXISTANTE : affectation #{existante.pk}. "
                        "Aucune création."
                    )
                    continue

                affectation = EquipeProjet(
                    projet=projet,
                    personnel_execution=execution,
                    fonction=fonction,
                    date_debut=execution.date_debut,
                    date_fin=date_fin,
                    actif=True,
                    observation=(
                        "Affectation créée depuis "
                        f"PersonnelExecutionProjet #{execution.pk}. "
                        + (
                            "Fin reprise de la fiche individuelle."
                            if execution.date_fin
                            else "Fin fixée à la date de fin du projet."
                        )
                    ),
                )

                affectation.full_clean()
                affectation.save()

            print(
                f"CRÉÉE : affectation #{affectation.pk} | "
                f"{fonction} | {nom} | "
                f"Début : {affectation.date_debut} | "
                f"Fin : {affectation.date_fin}"
            )

        except ValidationError as erreur:
            print(f"ERREUR DE VALIDATION pour {nom} :")
            for champ, messages in erreur.message_dict.items():
                print(f"  - {champ} : {', '.join(messages)}")

        except Exception as erreur:
            print(
                f"ERREUR pour {nom} : "
                f"{type(erreur).__name__} : {erreur}"
            )

    print()
    print("=" * 65)
    print("BILAN DES AFFECTATIONS")
    print("=" * 65)

    for fonction in TYPES_A_TRAITER:
        affectations = EquipeProjet.objects.filter(
            fonction=fonction
        ).select_related(
            "projet",
            "personnel_execution",
        )

        print(f"\n{fonction} : {affectations.count()} affectation(s)")

        for affectation in affectations:
            personne = affectation.personnel_execution
            nom_affiche = personne.nom if personne else "Non défini"

            print(
                f"  - #{affectation.pk} | {nom_affiche} | "
                f"Projet #{affectation.projet_id} | "
                f"Début : {affectation.date_debut} | "
                f"Fin : {affectation.date_fin}"
            )


if __name__ == "__main__":
    creer_affectations()
