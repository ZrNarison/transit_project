from salaire.models import Salaire

updated = 0
for s in Salaire.objects.all():
    calc = s.calculate_reste()
    if s.reste != calc:
        s.reste = calc
        s.save()
        updated += 1

print('updated', updated)
