from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'

    @classmethod
    def limite_role(cls, role):

        limites = {
            "Admin": 2,
            "SuperAdmin": 2,
            "Superviseur": 4,
            "UserMica": 10,
            "UserEntreprise": 10,
            "UserProjet": 50,
        }

        return limites.get(role)