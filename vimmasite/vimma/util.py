from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction

from vimma.models import Profile
from vimma.perms import Perms


@transaction.atomic
def create_vimma_user(username, email, password, first_name='', last_name=''):
    """
    Create a User and the associated Profile and return the User.

    You should use this function to create users, to make sure the profile is
    also created.
    """
    u = User.objects.create_user(username, email, password,
            first_name=first_name, last_name=last_name)
    u.profile = Profile.objects.create(user=u)
    return u


def has_perm(user, perm):
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


def login_required_or_forbidden(view_func):
    """
    Decorator raises PermissionDenied if the user is not logged in.

    This is similar to Django's login_required, only that one redirects to the
    login page.
    """
    def wrapped_view(request, *posargs, **kwargs):
        if not request.user.is_authenticated():
            raise PermissionDenied('You must be logged in')
        return view_func(request, *posargs, **kwargs)
    return wrapped_view
