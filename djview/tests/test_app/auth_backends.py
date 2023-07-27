from django.contrib.auth.backends import ModelBackend


class DummyModelBackend(ModelBackend):
    def authenticate(self, request, **kwargs):
        id = request.META.get("HTTP_USER_ID")

        if id is None:
            return None

        return self.get_user(id)
