from django.db import migrations, models
import django.db.models.deletion


def convert_categorie(apps, schema_editor):

    Personnel = apps.get_model('personnel', 'Personnel')
    Categorie = apps.get_model('categorie', 'Categorie')

    for p in Personnel.objects.all():

        ancien_nom = p.categorie

        if ancien_nom:

            categorie, created = Categorie.objects.get_or_create(
                nom=ancien_nom,
                defaults={
                    "description": ancien_nom
                }
            )

            # On garde temporairement l'id dans le champ texte
            p.categorie = str(categorie.id)
            p.save()


class Migration(migrations.Migration):

    dependencies = [
        ('categorie', '0002_categorie_description_alter_categorie_nom'),
        ('personnel', '0008_alter_personnel_categorie_alter_personnel_photo'),
    ]

    operations = [

        migrations.RunPython(
            convert_categorie,
            migrations.RunPython.noop
        ),

        migrations.AlterField(
            model_name='personnel',
            name='categorie',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='categorie.categorie',
            ),
        ),
    ]