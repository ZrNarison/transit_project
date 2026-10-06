from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Recalculate and update `reste` for all Salaire records.'

    def handle(self, *args, **options):
        from salaire.models import Salaire

        updated = 0
        total = Salaire.objects.count()
        self.stdout.write(f'Found {total} salaire(s).')

        for s in Salaire.objects.all():
            calc = s.calculate_reste()
            if s.reste != calc:
                s.reste = calc
                s.save()
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Updated {updated} salaire(s).'))