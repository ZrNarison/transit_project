from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response


    def __call__(self, request):

        public_paths = [
            reverse("users:login"),
            "/admin/",
        ]


        if not request.session.get("user_id"):

            if request.path not in public_paths:

                return redirect(
                    "users:login"
                )


        response = self.get_response(request)

        return response