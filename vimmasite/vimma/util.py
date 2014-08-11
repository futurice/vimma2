from django.contrib.auth.models import User
from django.db import transaction

from vimma.models import Profile


@transaction.atomic
def createUser(username, email, password, first_name='', last_name=''):
    """
    Create a User and the associated Profile and return the User.

    You should use this function to create users, to make sure the profile is
    also created.
    """
    u = User.objects.create_user(username, email, password,
            first_name=first_name, last_name=last_name)
    u.profile = Profile.objects.create(user=u)
    return u
