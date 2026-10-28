from io import BytesIO
import hashlib
import json
import logging
import os
import uuid
from io import StringIO
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.core import serializers
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.core.management import call_command
from django.db import DEFAULT_DB_ALIAS, IntegrityError, transaction
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import redirect, render
from django.utils import timezone as django_timezone
from django.utils.text import get_valid_filename
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods
from django.core.paginator import Paginator
from django.utils import timezone
from .models import JournalSauvegarde

logger = logging.getLogger(__name__)

FORMAT_NAME = "TRANSIT_PROJECT_SECURE_BACKUP"
FORMAT_VERSION = 1
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
SESSION_TOKEN_KEY = "transit_sauvegarde_import_token"
STAGING_DIR_NAME = ".private_imports"

EXCLUDED_MODELS = {
    "sessions.session",
    "admin.logentry",
}


class BackupValidationError(Exception):
    """Erreur de validation d'une sauvegarde."""


def _fernet():
    key = os.environ.get("TRANSIT_BACKUP_KEY", "").strip()

    if not key:
        raise ImproperlyConfigured(
            "La variable d'environnement TRANSIT_BACKUP_KEY "
            "n'est pas configurée dans le processus Django."
        )

    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ImproperlyConfigured(
            "TRANSIT_BACKUP_KEY doit contenir une clé Fernet valide."
        ) from exc
def _index_url_name(request):
    """Retourne la page de sauvegarde correspondant à l'entreprise."""
    match = getattr(request, "resolver_match", None)

    if match and (match.url_name or "").startswith("h_"):
        return "sauvegarde:h_index"

    if request.session.get("h_user_id") and not request.session.get("user_id"):
        return "sauvegarde:h_index"

    return "sauvegarde:index"

def _project_fingerprint():
    secret = str(getattr(settings, "SECRET_KEY", ""))

    if not secret:
        raise ImproperlyConfigured("SECRET_KEY n'est pas configurée.")

    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _actor(request):
    """Accepte les sessions Django, GALAXY et H/MCCR."""
    try:
        from users.models import AppUser, H_AppUser
    except (ImportError, RuntimeError):
        AppUser = None
        H_AppUser = None

    if request.user.is_authenticated:
        return {
            "id": str(request.user.pk),
            "name": str(request.user.get_username()),
            "session": "django_auth",
        }

    user_id = request.session.get("user_id")

    if user_id and AppUser is not None:
        user = AppUser.objects.filter(pk=user_id).first()

        if user is not None:
            return {
                "id": str(user.pk),
                "name": str(
                    getattr(user, "username", "")
                    or getattr(user, "nom_utilisateur", "")
                    or request.session.get("username", "")
                    or f"Utilisateur {user.pk}"
                ),
                "session": "GALAXY",
            }

    h_user_id = request.session.get("h_user_id")

    if h_user_id and H_AppUser is not None:
        user = H_AppUser.objects.filter(pk=h_user_id).first()

        if user is not None:
            return {
                "id": str(user.pk),
                "name": str(
                    getattr(user, "username", "")
                    or getattr(user, "nom_utilisateur", "")
                    or request.session.get("h_username", "")
                    or f"Utilisateur H {user.pk}"
                ),
                "session": "H/MCCR",
            }

    return None


def _require_actor(request):
    actor = _actor(request)

    if actor is None:
        messages.error(
            request,
            "Session invalide ou expirée. Veuillez vous reconnecter.",
        )
        return None

    return actor


def _journal(
    actor,
    action,
    statut="OK",
    fichier="",
    empreinte="",
    details="",
):
    """Enregistre une opération sans exposer la clé de chiffrement."""
    try:
        JournalSauvegarde.objects.create(
            utilisateur_id=(actor or {}).get("id", ""),
            utilisateur=(actor or {}).get("name", "Inconnu")[:150],
            source_session=(actor or {}).get("session", "")[:30],
            action=action,
            statut=statut[:20],
            fichier=fichier[:255],
            empreinte_sha256=empreinte[:64],
            details=str(details)[:4000],
        )
    except Exception:
        logger.exception("Impossible d'écrire le journal de sauvegarde.")


def _staging_dir():
    """Crée le répertoire privé des archives validées."""
    path = Path(settings.BASE_DIR) / STAGING_DIR_NAME
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    return path


def _clear_staged_import(request):
    token = request.session.pop(SESSION_TOKEN_KEY, None)

    if not token or not isinstance(token, str):
        return

    try:
        uuid.UUID(token)
        (_staging_dir() / f"{token}.enc").unlink(missing_ok=True)
    except (ValueError, OSError):
        logger.warning("Impossible de nettoyer le fichier d'import temporaire.")


def _build_fixture():
    """Exporte les modèles Django installés dans une fixture JSON."""
    output = StringIO()

    call_command(
        "dumpdata",
        "--natural-foreign",
        "--natural-primary",
        "--exclude=sessions",
        "--exclude=admin.logentry",
        "--indent=2",
        stdout=output,
        verbosity=0,
    )

    return output.getvalue()




def _make_encrypted_archive():
    payload = {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "project_fingerprint": _project_fingerprint(),
        "created_at": django_timezone.now().isoformat(),
        "django_version": str(getattr(settings, "DJANGO_VERSION", "")),
        "fixture": _build_fixture(),
    }

    raw = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    encrypted = _fernet().encrypt(raw)

    return (
        encrypted,
        hashlib.sha256(encrypted).hexdigest(),
        payload["created_at"],
    )


def _read_and_validate_archive(encrypted):
    """Authentifie et valide l'archive avant toute écriture."""
    if not encrypted or len(encrypted) > MAX_UPLOAD_BYTES:
        raise BackupValidationError(
            "Fichier vide ou trop volumineux (limite : 100 Mo)."
        )

    try:
        raw = _fernet().decrypt(encrypted)
    except InvalidToken as exc:
        raise BackupValidationError(
            "Archive invalide, altérée ou chiffrée avec une autre clé."
        ) from exc

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupValidationError(
            "Le contenu déchiffré n'est pas un JSON valide."
        ) from exc

    if not isinstance(payload, dict):
        raise BackupValidationError("Format d'archive incorrect.")

    if payload.get("format") != FORMAT_NAME:
        raise BackupValidationError(
            "Cette archive n'est pas une sauvegarde TRANSIT_PROJECT."
        )

    if payload.get("version") != FORMAT_VERSION:
        raise BackupValidationError(
            "Version d'archive non prise en charge."
        )

    if payload.get("project_fingerprint") != _project_fingerprint():
        raise BackupValidationError(
            "Cette sauvegarde appartient à une installation ayant "
            "une autre SECRET_KEY."
        )

    fixture = payload.get("fixture")

    if not isinstance(fixture, str) or not fixture.strip():
        raise BackupValidationError(
            "La sauvegarde ne contient aucune fixture exploitable."
        )

    try:
        parsed = json.loads(fixture)
    except json.JSONDecodeError as exc:
        raise BackupValidationError(
            "La fixture JSON est invalide."
        ) from exc

    if not isinstance(parsed, list):
        raise BackupValidationError(
            "La fixture doit contenir une liste d'enregistrements."
        )

    return payload, parsed


def _model_for_label(label):
    """Vérifie qu'un modèle de l'archive est autorisé."""
    try:
        model = apps.get_model(label)
    except (LookupError, ValueError) as exc:
        raise BackupValidationError(
            f"Modèle inconnu dans l'archive : {label}."
        ) from exc

    if model is None or model._meta.proxy or model._meta.swapped:
        raise BackupValidationError(
            f"Modèle non importable : {label}."
        )

    if model._meta.label_lower in EXCLUDED_MODELS:
        raise BackupValidationError(
            f"Modèle interdit dans l'archive : {label}."
        )

    return model


def _same_record(existing, incoming_obj, m2m_data):
    """Compare les champs concrets et les relations M2M."""
    for field in existing._meta.concrete_fields:
        if (
            getattr(existing, field.attname)
            != getattr(incoming_obj, field.attname)
        ):
            return False

    for field_name, incoming_values in (m2m_data or {}).items():
        manager = getattr(existing, field_name)

        current_ids = set(manager.values_list("pk", flat=True))
        incoming_ids = {
            getattr(value, "pk", value)
            for value in incoming_values
        }

        if current_ids != incoming_ids:
            return False

    return True


def _find_existing(item, alias=DEFAULT_DB_ALIAS):
    """
    Recherche un enregistrement existant par PK, puis par clé naturelle.
    Retourne None lorsqu'aucun enregistrement correspondant n'est trouvé.
    """
    model = item.object.__class__
    obj = item.object

    if obj.pk is not None:
        existing = (
            model._default_manager.using(alias)
            .filter(pk=obj.pk)
            .first()
        )

        if existing is not None:
            return existing

    natural_key = getattr(obj, "natural_key", None)

    if callable(natural_key):
        try:
            natural = natural_key()

            if natural is not None:
                return model._default_manager.using(
                    alias
                ).get_by_natural_key(*natural)

        except (
            ObjectDoesNotExist,
            AttributeError,
            TypeError,
            ValueError,
        ):
            pass

    return None


def _inspect_fixture(fixture_text):
    """
    Analyse l'archive sans modifier la base.

    Les journaux de sauvegarde de l'archive sont ignorés.
    Les conflits de PK sont comptabilisés sans bloquer la fusion.
    """
    try:
        deserialized = list(
            serializers.deserialize(
                "json",
                fixture_text,
                ignorenonexistent=False,
                handle_forward_references=True,
            )
        )
    except Exception as exc:
        raise BackupValidationError(
            "Les données ou relations de l'archive sont invalides."
        ) from exc

    new_count = 0
    identical_count = 0
    conflict_count = 0
    ignored_journals = 0

    for item in deserialized:
        model = _model_for_label(item.object._meta.label)

        if model._meta.label_lower == JournalSauvegarde._meta.label_lower:
            ignored_journals += 1
            continue

        existing = _find_existing(item)

        if existing is None:
            new_count += 1
        elif _same_record(existing, item.object, item.m2m_data):
            identical_count += 1
        else:
            conflict_count += 1

    return (
        deserialized,
        new_count,
        identical_count,
        conflict_count,
        ignored_journals,
    )


def _import_fixture(fixture_text):
    """
    Fusionne une archive sans mettre à jour les objets existants.

    Les journaux d'archive sont ignorés. Les collisions d'insertion sont
    comptabilisées. Les erreurs de relations différées annulent la fusion.
    """
    (
        deserialized,
        _new_estimate,
        _same_estimate,
        _conflict_estimate,
        _ignored_estimate,
    ) = _inspect_fixture(fixture_text)

    alias = DEFAULT_DB_ALIAS
    created = 0
    skipped_identical = 0
    skipped_conflicts = 0
    skipped_journals = 0
    pending = []

    with transaction.atomic(using=alias):
        for item in deserialized:
            model = _model_for_label(item.object._meta.label)

            if model._meta.label_lower == JournalSauvegarde._meta.label_lower:
                skipped_journals += 1
                continue

            existing = _find_existing(item, alias=alias)

            if existing is not None:
                if _same_record(existing, item.object, item.m2m_data):
                    skipped_identical += 1
                else:
                    skipped_conflicts += 1
                continue

            try:
                with transaction.atomic(using=alias):
                    item.save(
                        using=alias,
                        force_insert=True,
                        save_m2m=False,
                    )
            except IntegrityError:
                # Collision PK/unique : aucune mise à jour de l'existant.
                skipped_conflicts += 1
                logger.warning(
                    "Insertion ignorée pour %s, PK=%s : collision d'intégrité.",
                    model._meta.label,
                    item.object.pk,
                )
                continue

            pending.append(item)
            created += 1

        # Résoudre les FK différées après les insertions.
        for item in pending:
            if getattr(item, "deferred_fields", None):
                item.save_deferred_fields(using=alias)

        # Ajouter les relations M2M des objets insérés.
        for item in pending:
            for field_name, related_values in (item.m2m_data or {}).items():
                getattr(item.object, field_name).set(related_values)

    skipped = skipped_identical + skipped_conflicts + skipped_journals

    return (
        created,
        skipped,
        skipped_identical,
        skipped_conflicts,
        skipped_journals,
    )


def _create_database_backup():
    """Crée une copie SQLite cohérente avant l'importation."""
    db_config = settings.DATABASES.get(DEFAULT_DB_ALIAS, {})
    engine = db_config.get("ENGINE", "")

    if not engine.endswith("sqlite3"):
        return None

    db_name = db_config.get("NAME")

    if not db_name or str(db_name) == ":memory:":
        return None

    from django.db import connections

    connection = connections[DEFAULT_DB_ALIAS]
    connection.ensure_connection()

    backup_name = (
        f"transit_avant_import_"
        f"{django_timezone.now():%Y%m%d_%H%M%S}_"
        f"{uuid.uuid4().hex}.sqlite3"
    )

    backup_path = Path(settings.BASE_DIR) / backup_name

    # La destination doit être inexistante pour VACUUM INTO.
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA wal_checkpoint(FULL)")
        cursor.execute("VACUUM INTO %s", [str(backup_path)])

    try:
        os.chmod(backup_path, 0o600)
    except OSError:
        pass

    return str(backup_path)


@never_cache
@require_http_methods(["GET"])
def index(request):
    actor = _require_actor(request)

    if actor is None:
        return redirect("users:login")

    # Déterminer les routes correspondant à l'entreprise connectée.
    index_url_name = _index_url_name(request)
    is_mccr = index_url_name == "sauvegarde:h_index"

    exporter_url_name = (
        "sauvegarde:h_exporter"
        if is_mccr
        else "sauvegarde:exporter"
    )
    valider_import_url_name = (
        "sauvegarde:h_valider_import"
        if is_mccr
        else "sauvegarde:valider_import"
    )
    importer_url_name = (
        "sauvegarde:h_importer"
        if is_mccr
        else "sauvegarde:importer"
    )

    # Historique complet : les filtres sont appliqués avant la pagination.
    journal = JournalSauvegarde.objects.all()

    recherche = request.GET.get("q", "").strip()
    utilisateur = request.GET.get("utilisateur", "").strip()
    action = request.GET.get("action", "").strip()
    statut = request.GET.get("statut", "").strip()
    date_debut = request.GET.get("date_debut", "").strip()
    date_fin = request.GET.get("date_fin", "").strip()

    if recherche:
        journal = journal.filter(
            Q(fichier__icontains=recherche)
            | Q(details__icontains=recherche)
            | Q(utilisateur__icontains=recherche)
            | Q(utilisateur_id__icontains=recherche)
        )

    if utilisateur:
        journal = journal.filter(utilisateur=utilisateur)

    actions_valides = {
        valeur for valeur, libelle in JournalSauvegarde.ACTION_CHOICES
    }
    if action in actions_valides:
        journal = journal.filter(action=action)

    statuts_valides = set(
        JournalSauvegarde.objects.values_list(
            "statut", flat=True
        ).distinct()
    )
    if statut in statuts_valides:
        journal = journal.filter(statut=statut)

    from datetime import date

    try:
        if date_debut:
            date_debut_valide = date.fromisoformat(date_debut)
            journal = journal.filter(
                date_operation__date__gte=date_debut_valide
            )
        else:
            date_debut = ""
    except ValueError:
        date_debut = ""

    try:
        if date_fin:
            date_fin_valide = date.fromisoformat(date_fin)
            journal = journal.filter(
                date_operation__date__lte=date_fin_valide
            )
        else:
            date_fin = ""
    except ValueError:
        date_fin = ""

    journal = journal.order_by("-date_operation")

    # Pagination : 20 opérations par page.
    paginator = Paginator(journal, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    utilisateurs = (
        JournalSauvegarde.objects.exclude(utilisateur="")
        .values_list("utilisateur", flat=True)
        .distinct()
        .order_by("utilisateur")
    )

    statuts = (
        JournalSauvegarde.objects.values_list("statut", flat=True)
        .distinct()
        .order_by("statut")
    )

    # Conserver les filtres dans les liens de pagination.
    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_string = query_params.urlencode()

    # Vérifier si une archive validée attend une confirmation.
    pending_token = request.session.get(SESSION_TOKEN_KEY)
    pending_exists = False

    if pending_token:
        try:
            uuid.UUID(pending_token)
            pending_exists = (
                _staging_dir() / f"{pending_token}.enc"
            ).is_file()
        except ValueError:
            request.session.pop(SESSION_TOKEN_KEY, None)

    context = {
        "journal_sauvegardes": page_obj,
        "page_obj": page_obj,
        "pending_import": pending_exists,
        "recherche": recherche,
        "filtre_utilisateur": utilisateur,
        "filtre_action": action,
        "filtre_statut": statut,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "utilisateurs": utilisateurs,
        "actions_sauvegarde": JournalSauvegarde.ACTION_CHOICES,
        "statuts": statuts,
        "query_string": query_string,

        # Routes indispensables au template.
        "is_mccr": is_mccr,
        "index_url_name": index_url_name,
        "exporter_url_name": exporter_url_name,
        "valider_import_url_name": valider_import_url_name,
        "importer_url_name": importer_url_name,
    }

    return render(
        request,
        "sauvegarde/index.html",
        context,
    )


@never_cache
@require_POST
def exporter(request):
    actor = _require_actor(request)

    if actor is None:
        return redirect("users:login")

    try:
        encrypted, digest, created_at = _make_encrypted_archive()

        _journal(
            actor,
            "EXPORT",
            fichier="transit_project.transitbak",
            empreinte=digest,
            details=f"Archive chiffrée créée le {created_at}.",
        )

        
        response = FileResponse(
            BytesIO(encrypted),
            content_type="application/octet-stream",
            as_attachment=True,
            filename="transit_project.transitbak",
        )


        response["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response["Pragma"] = "no-cache"
        response["X-Content-Type-Options"] = "nosniff"

        return response

    except Exception as exc:
        logger.exception("Échec de l'exportation sécurisée.")

        _journal(
            actor,
            "ERROR",
            statut="ECHEC",
            details=f"Export : {type(exc).__name__}",
        )

        messages.error(
            request,
            f"Exportation impossible : {exc}",
        )
        return redirect(_index_url_name(request))


@never_cache
@require_POST
def valider_import(request):
    actor = _require_actor(request)

    if actor is None:
        return redirect("users:login")

    uploaded = request.FILES.get("fichier_sauvegarde")

    if uploaded is None:
        messages.error(request, "Choisissez une archive à vérifier.")
        return redirect(_index_url_name(request))

    if uploaded.size <= 0 or uploaded.size > MAX_UPLOAD_BYTES:
        messages.error(
            request,
            "Le fichier est vide ou dépasse la limite de 100 Mo.",
        )
        return redirect(_index_url_name(request))

    try:
        encrypted = uploaded.read(MAX_UPLOAD_BYTES + 1)

        if len(encrypted) > MAX_UPLOAD_BYTES:
            raise BackupValidationError(
                "Fichier trop volumineux (limite : 100 Mo)."
            )

        payload, _parsed = _read_and_validate_archive(encrypted)

        (
            _deserialized,
            new_count,
            identical_count,
            conflict_count,
            ignored_journals,
        ) = _inspect_fixture(payload["fixture"])

        _clear_staged_import(request)

        token = str(uuid.uuid4())
        staged_path = _staging_dir() / f"{token}.enc"
        staged_path.write_bytes(encrypted)

        try:
            os.chmod(staged_path, 0o600)
        except OSError:
            pass

        request.session[SESSION_TOKEN_KEY] = token
        request.session.modified = True

        digest = hashlib.sha256(encrypted).hexdigest()

        _journal(
            actor,
            "PREVIEW",
            fichier=get_valid_filename(uploaded.name)[:255],
            empreinte=digest,
            details=(
                f"Validation réussie. Nouveaux : {new_count}; "
                f"identiques : {identical_count}; "
                f"conflits : {conflict_count}; "
                f"journaux ignorés : {ignored_journals}."
            ),
        )

        messages.success(
            request,
            f"Archive authentifiée et valide. "
            f"Nouveaux enregistrements estimés : {new_count}; "
            f"enregistrements identiques : {identical_count}; "
            f"conflits qui seront ignorés : {conflict_count}; "
            f"journaux de sauvegarde non réimportés : {ignored_journals}. "
            "Confirmez l'importation ci-dessous.",
        )

    except (BackupValidationError, ImproperlyConfigured) as exc:
        _journal(
            actor,
            "ERROR",
            statut="INVALIDE",
            fichier=get_valid_filename(uploaded.name)[:255],
            details=str(exc),
        )
        messages.error(request, str(exc))

    except Exception as exc:
        logger.exception("Erreur lors de la validation de l'archive.")

        _journal(
            actor,
            "ERROR",
            statut="ECHEC",
            fichier=get_valid_filename(uploaded.name)[:255],
            details=type(exc).__name__,
        )

        messages.error(
            request,
            f"Validation impossible : {type(exc).__name__}. "
            "Consultez le journal serveur.",
        )

    return redirect(_index_url_name(request))


@never_cache
@require_POST
def importer(request):
    actor = _require_actor(request)

    if actor is None:
        return redirect("users:login")

    token = request.session.get(SESSION_TOKEN_KEY)

    if not token:
        messages.error(
            request,
            "Aucune archive validée en attente. "
            "Importez et validez un fichier.",
        )
        return redirect(_index_url_name(request))

    try:
        uuid.UUID(token)

        staged_path = _staging_dir() / f"{token}.enc"
        encrypted = staged_path.read_bytes()
        payload, _parsed = _read_and_validate_archive(encrypted)

        # Sauvegarde préalable avant toute écriture métier.
        backup_path = _create_database_backup()

        (
            created,
            skipped,
            skipped_identical,
            skipped_conflicts,
            skipped_journals,
        ) = _import_fixture(payload["fixture"])

        digest = hashlib.sha256(encrypted).hexdigest()

        _journal(
            actor,
            "IMPORT",
            fichier=staged_path.name,
            empreinte=digest,
            details=(
                f"Fusion terminée. Ajoutés : {created}; "
                f"identiques ignorés : {skipped_identical}; "
                f"conflits ignorés : {skipped_conflicts}; "
                f"journaux non réimportés : {skipped_journals}; "
                f"sauvegarde préalable : "
                f"{backup_path or 'non applicable'}."
            ),
        )

        messages.success(
            request,
            f"Fusion terminée : {created} enregistrement(s) ajouté(s), "
            f"{skipped_identical} enregistrement(s) identique(s) ignoré(s), "
            f"{skipped_conflicts} conflit(s) ignoré(s), "
            f"{skipped_journals} journal/journaux non réimporté(s). "
            + (
                f"Sauvegarde préalable : {Path(backup_path).name}."
                if backup_path
                else ""
            ),
        )

    except (BackupValidationError, ImproperlyConfigured) as exc:
        _journal(
            actor,
            "ERROR",
            statut="INVALIDE",
            details=str(exc),
        )
        messages.error(request, str(exc))

    except IntegrityError:
        logger.exception("Contrainte de base lors de l'import fusion.")

        _journal(
            actor,
            "ERROR",
            statut="ANNULE",
            details="Contrainte d'intégrité : transaction annulée.",
        )

        messages.error(
            request,
            "Importation annulée : une contrainte d'intégrité empêche "
            "de terminer la fusion. La transaction métier a été annulée.",
        )

    except Exception as exc:
        logger.exception("Échec de l'importation sécurisée.")

        _journal(
            actor,
            "ERROR",
            statut="ECHEC",
            details=f"Import : {type(exc).__name__}",
        )

        messages.error(
            request,
            f"Importation impossible ({type(exc).__name__}). "
            "Consultez le journal serveur.",
        )

    finally:
        _clear_staged_import(request)
        

    return redirect(_index_url_name(request))