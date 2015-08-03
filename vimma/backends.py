from django.contrib.auth.backends import RemoteUserBackend

class RemoteNoUnknownUserBackend(RemoteUserBackend):
    """
    RemoteUserBackend which does not auto-create non-existing users.
    """
    create_unknown_user = False
