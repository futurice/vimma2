from django.contrib.auth.models import User
from django.db import transaction

from vimma.models import Profile
from vimma.perms import Perms


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


def hasPerm(user, perm):
    """
    Return True if user (User object) has perm (string), False otherwise.

    The omnipotent permission grants any perm.
    Throws an exception if the user has no Profile (that's an incorrect state,
    so fail-fast; don't hide the problem).
    """
    for r in user.profile.roles.filter():
        if r.permissions.filter(name=Perms.OMNIPOTENT).exists():
            return True
        if r.permissions.filter(name=perm).exists():
            return True
    return False
