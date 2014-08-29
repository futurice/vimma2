import datetime
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
import json
import logging
import pytz

from vimma.models import Profile
from vimma.perms import Perms
from vimma.actions import Actions


log = logging.getLogger(__name__)


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


def can_do(user, what, data=None):
    """
    Check if user is omnipotent or is allowed to do ‘what’.

    Some things, e.g. viewing a project, require parameters (which project).
    Use the optional ‘data’ arg for this.
    """
    if has_perm(user, Perms.OMNIPOTENT):
        return True

    if what == Actions.WRITE_SCHEDULES:
        return has_perm(user, Perms.EDIT_SCHEDULE)
    elif action == Actions.CREATE_VM_IN_PROJECT:
        # TODO: implement later
        return False
    else:
        log.warn('Unknown action “{}”'.format(action))
        return False


def schedule_at_tstamp(schedule, tstamp):
    """
    Returns True if schedule says ON at unix tstamp, else False.
    """
    tz = pytz.timezone(schedule.timezone.name)
    naive = datetime.datetime.utcfromtimestamp(tstamp)
    aware = pytz.utc.localize(naive)
    aware = aware.astimezone(tz)
    row = aware.weekday()
    col = aware.hour * 2 + aware.minute // 30
    return json.loads(schedule.matrix)[row][col]
