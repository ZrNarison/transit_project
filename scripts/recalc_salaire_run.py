import os
import sys

proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transit_project.settings')

import django
django.setup()

from salaire.models import Salaire

updated = 0
for s in Salaire.objects.all():
    calc = s.calculate_reste()
    if s.reste != calc:
        s.reste = calc
        s.save()
        updated += 1

print('updated', updated)
