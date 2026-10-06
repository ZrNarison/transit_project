from django.db import migrations


# ============================================================
# CONVERSION :
#
# Ancien modèle :
#     VehiculeProjet.vehicule = CharField(...)
#
# Nouveau modèle :
#     VehiculeProjet.vehicule = ForeignKey(
#         "materiaux.Vehicule",
#         ...
#     )
#
# IMPORTANT :
# La table SQLite est reconstruite parce que l'ancien champ
# `vehicule` participe à la contrainte UNIQUE :
#
#     UNIQUE(projet_id, vehicule)
#
# SQLite ne permet pas de supprimer directement cette colonne.
# ============================================================


def convertir_vehicule(apps, schema_editor):
    """
    Convertit l'ancien champ texte `vehicule` en `vehicule_id`.

    Ancienne structure :

        projet_vehiculeprojet.vehicule
        VARCHAR(150)

    Nouvelle structure :

        projet_vehiculeprojet.vehicule_id
        BIGINT
        FK -> materiaux_vehicule.id

    Les données existantes sont conservées.
    """

    connection = schema_editor.connection

    # ========================================================
    # IMPORTANT
    #
    # Utilisation du curseur SQLite natif.
    #
    # Cela évite le problème Django 6.1 / Python 3.14 :
    #
    #     TypeError:
    #     not all arguments converted during string formatting
    #
    # provoqué par last_executed_query() avec les paramètres ?.
    # ========================================================

    cursor = connection.connection.cursor()

    # ========================================================
    # 1. Vérification des tables
    # ========================================================

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name IN (
              'projet_vehiculeprojet',
              'materiaux_vehicule'
          )
    """)

    tables = {row[0] for row in cursor.fetchall()}

    if "projet_vehiculeprojet" not in tables:
        raise RuntimeError(
            "La table 'projet_vehiculeprojet' est introuvable."
        )

    if "materiaux_vehicule" not in tables:
        raise RuntimeError(
            "La table 'materiaux_vehicule' est introuvable."
        )

    # ========================================================
    # 2. Lecture des anciens enregistrements
    # ========================================================

    cursor.execute("""
        SELECT
            id,
            date_debut,
            date_fin,
            kilometrage_initial,
            kilometrage_final,
            consommation_km_litre,
            actif,
            observation,
            created_at,
            updated_at,
            chauffeur_id,
            projet_id,
            vehicule
        FROM projet_vehiculeprojet
        ORDER BY id
    """)

    anciennes_lignes = cursor.fetchall()

    # ========================================================
    # 3. Lecture de tous les véhicules
    #
    # Exemple :
    #
    #     id = 1   immatriculation = 2040 FT
    #     id = 2   immatriculation = 0220 TG
    #
    # On construit un dictionnaire en mémoire.
    # ========================================================

    cursor.execute("""
        SELECT
            id,
            immatriculation
        FROM materiaux_vehicule
    """)

    vehicules = cursor.fetchall()

    vehicules_par_immatriculation = {}

    for vehicule_id, immatriculation in vehicules:

        if immatriculation is None:
            continue

        cle = str(immatriculation).strip().lower()

        vehicules_par_immatriculation[cle] = vehicule_id

    # ========================================================
    # 4. Préparation des correspondances
    #
    # Aucune modification de table n'est encore effectuée.
    #
    # Exemple :
    #
    #     "2040 ft" -> 1
    #     "0220 TG" -> 2
    # ========================================================

    correspondances = []

    for ligne in anciennes_lignes:

        (
            row_id,
            date_debut,
            date_fin,
            kilometrage_initial,
            kilometrage_final,
            consommation_km_litre,
            actif,
            observation,
            created_at,
            updated_at,
            chauffeur_id,
            projet_id,
            ancienne_immatriculation,
        ) = ligne

        if ancienne_immatriculation is None:
            raise RuntimeError(
                f"VehiculeProjet #{row_id} possède un véhicule NULL."
            )

        cle = str(
            ancienne_immatriculation
        ).strip().lower()

        vehicule_id = vehicules_par_immatriculation.get(cle)

        if vehicule_id is None:

            raise RuntimeError(
                "Impossible de convertir "
                f"VehiculeProjet #{row_id} : "
                f"le véhicule "
                f"'{ancienne_immatriculation}' "
                "n'existe pas dans "
                "materiaux_vehicule."
            )

        correspondances.append(
            (
                row_id,
                date_debut,
                date_fin,
                kilometrage_initial,
                kilometrage_final,
                consommation_km_litre,
                actif,
                observation,
                created_at,
                updated_at,
                chauffeur_id,
                projet_id,
                vehicule_id,
            )
        )

    # ========================================================
    # 5. Création de la nouvelle table
    #
    # Même structure que l'ancienne, sauf :
    #
    #     vehicule
    #
    # devient :
    #
    #     vehicule_id
    #
    # La contrainte UNIQUE devient :
    #
    #     UNIQUE(projet_id, vehicule_id)
    # ========================================================

    cursor.execute("""
        CREATE TABLE "projet_vehiculeprojet_new" (

            "id"
                integer
                NOT NULL
                PRIMARY KEY
                AUTOINCREMENT,

            "date_debut"
                date
                NOT NULL,

            "date_fin"
                date
                NOT NULL,

            "kilometrage_initial"
                decimal
                NOT NULL,

            "kilometrage_final"
                decimal
                NOT NULL,

            "consommation_km_litre"
                decimal
                NOT NULL,

            "actif"
                bool
                NOT NULL,

            "observation"
                text
                NOT NULL,

            "created_at"
                datetime
                NOT NULL,

            "updated_at"
                datetime
                NOT NULL,

            "chauffeur_id"
                bigint
                NULL
                REFERENCES
                    "personnel_personnel" ("id")
                DEFERRABLE
                INITIALLY DEFERRED,

            "projet_id"
                bigint
                NOT NULL
                REFERENCES
                    "projet_projet" ("id")
                DEFERRABLE
                INITIALLY DEFERRED,

            "vehicule_id"
                bigint
                NOT NULL
                REFERENCES
                    "materiaux_vehicule" ("id")
                DEFERRABLE
                INITIALLY DEFERRED,

            CONSTRAINT
                "unique_vehicule_projet"
                UNIQUE (
                    "projet_id",
                    "vehicule_id"
                )
        )
    """)

    # ========================================================
    # 6. Copie des données dans la nouvelle table
    # ========================================================

    for (
        row_id,
        date_debut,
        date_fin,
        kilometrage_initial,
        kilometrage_final,
        consommation_km_litre,
        actif,
        observation,
        created_at,
        updated_at,
        chauffeur_id,
        projet_id,
        vehicule_id,
    ) in correspondances:

        cursor.execute(
            """
            INSERT INTO "projet_vehiculeprojet_new" (
                "id",
                "date_debut",
                "date_fin",
                "kilometrage_initial",
                "kilometrage_final",
                "consommation_km_litre",
                "actif",
                "observation",
                "created_at",
                "updated_at",
                "chauffeur_id",
                "projet_id",
                "vehicule_id"
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                row_id,
                date_debut,
                date_fin,
                kilometrage_initial,
                kilometrage_final,
                consommation_km_litre,
                actif,
                observation,
                created_at,
                updated_at,
                chauffeur_id,
                projet_id,
                vehicule_id,
            ),
        )

    # ========================================================
    # 7. Suppression de l'ancienne table
    #
    # Cette fois, DROP TABLE est utilisé au lieu de
    # ALTER TABLE DROP COLUMN.
    #
    # La contrainte UNIQUE problématique disparaît donc
    # avec l'ancienne table.
    # ========================================================

    cursor.execute("""
        DROP TABLE "projet_vehiculeprojet"
    """)

    # ========================================================
    # 8. Renommage de la nouvelle table
    # ========================================================

    cursor.execute("""
        ALTER TABLE
            "projet_vehiculeprojet_new"
        RENAME TO
            "projet_vehiculeprojet"
    """)

    # ========================================================
    # 9. Recréation des index Django
    # ========================================================

    cursor.execute("""
        CREATE INDEX
        "projet_vehiculeprojet_projet_id_81fdb6d7"
        ON
        "projet_vehiculeprojet"
        ("projet_id")
    """)

    cursor.execute("""
        CREATE INDEX
        "projet_vehiculeprojet_chauffeur_id_d7cdf530"
        ON
        "projet_vehiculeprojet"
        ("chauffeur_id")
    """)

    # ========================================================
    # 10. Fermeture du curseur natif
    # ========================================================

    cursor.close()


def annuler_conversion(apps, schema_editor):
    """
    Annule la conversion.

    Recrée l'ancien champ texte :

        vehicule VARCHAR(150)

    à partir de :

        materiaux_vehicule.immatriculation
    """

    connection = schema_editor.connection

    # Curseur SQLite natif.
    cursor = connection.connection.cursor()

    # ========================================================
    # 1. Création de l'ancienne structure
    # ========================================================

    cursor.execute("""
        CREATE TABLE "projet_vehiculeprojet_old" (

            "id"
                integer
                NOT NULL
                PRIMARY KEY
                AUTOINCREMENT,

            "date_debut"
                date
                NOT NULL,

            "date_fin"
                date
                NOT NULL,

            "kilometrage_initial"
                decimal
                NOT NULL,

            "kilometrage_final"
                decimal
                NOT NULL,

            "consommation_km_litre"
                decimal
                NOT NULL,

            "actif"
                bool
                NOT NULL,

            "observation"
                text
                NOT NULL,

            "created_at"
                datetime
                NOT NULL,

            "updated_at"
                datetime
                NOT NULL,

            "chauffeur_id"
                bigint
                NULL
                REFERENCES
                    "personnel_personnel" ("id")
                DEFERRABLE
                INITIALLY DEFERRED,

            "projet_id"
                bigint
                NOT NULL
                REFERENCES
                    "projet_projet" ("id")
                DEFERRABLE
                INITIALLY DEFERRED,

            "vehicule"
                varchar(150)
                NOT NULL,

            CONSTRAINT
                "unique_vehicule_projet"
                UNIQUE (
                    "projet_id",
                    "vehicule"
                )
        )
    """)

    # ========================================================
    # 2. Restauration des données
    # ========================================================

    cursor.execute("""
        INSERT INTO "projet_vehiculeprojet_old" (
            "id",
            "date_debut",
            "date_fin",
            "kilometrage_initial",
            "kilometrage_final",
            "consommation_km_litre",
            "actif",
            "observation",
            "created_at",
            "updated_at",
            "chauffeur_id",
            "projet_id",
            "vehicule"
        )
        SELECT
            vp."id",
            vp."date_debut",
            vp."date_fin",
            vp."kilometrage_initial",
            vp."kilometrage_final",
            vp."consommation_km_litre",
            vp."actif",
            vp."observation",
            vp."created_at",
            vp."updated_at",
            vp."chauffeur_id",
            vp."projet_id",
            mv."immatriculation"
        FROM
            "projet_vehiculeprojet" vp
        INNER JOIN
            "materiaux_vehicule" mv
            ON
                mv."id" = vp."vehicule_id"
    """)

    # ========================================================
    # 3. Suppression de la nouvelle table
    # ========================================================

    cursor.execute("""
        DROP TABLE "projet_vehiculeprojet"
    """)

    # ========================================================
    # 4. Restauration du nom
    # ========================================================

    cursor.execute("""
        ALTER TABLE
            "projet_vehiculeprojet_old"
        RENAME TO
            "projet_vehiculeprojet"
    """)

    # ========================================================
    # 5. Recréation des index
    # ========================================================

    cursor.execute("""
        CREATE INDEX
        "projet_vehiculeprojet_projet_id_81fdb6d7"
        ON
        "projet_vehiculeprojet"
        ("projet_id")
    """)

    cursor.execute("""
        CREATE INDEX
        "projet_vehiculeprojet_chauffeur_id_d7cdf530"
        ON
        "projet_vehiculeprojet"
        ("chauffeur_id")
    """)

    # ========================================================
    # 6. Fermeture du curseur
    # ========================================================

    cursor.close()


# ============================================================
# MIGRATION
# ============================================================

class Migration(migrations.Migration):

    dependencies = [
        (
            "projet",
            "0004_equipeprojet_updated_at_pointprojet_updated_at_and_more",
        ),
        (
            "materiaux",
            "0014_activitetransport_point_projet_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(
            convertir_vehicule,
            annuler_conversion,
        ),
    ]