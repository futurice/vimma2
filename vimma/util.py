import importlib
import datetime
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.utils import OperationalError
from django.http import HttpResponse
from django.utils.timezone import utc
import json
import pytz
import random
import time

from vimma.actions import Actions
from vimma.audit import Auditor
from vimma.models import VM, User
from vimma.perms import Perms


aud = Auditor(__name__)

def get_import(module, thing):
    m = importlib.import_module(module)
    return getattr(m, thing)

@transaction.atomic
def create_vimma_user(username, email, password, first_name='', last_name=''):
    user,_ = User.objects.get_or_create(username=username, defaults=dict(email=email,
            first_name=first_name, last_name=last_name))
    if _ and password:
        user.set_password(password)
        user.save()
    return user


def has_perm(user, perm):
    """
    Return True if user (User object) has perm (string), False otherwise.

    The omnipotent permission grants any perm.
    """
    for r in user.roles.filter():
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


def get_http_json_err(errText, code):
    """
    Return HttpResponse with json {error: errText} and given status code.
    """
    return HttpResponse(json.dumps({'error': errText}),
            content_type="application/json", status=code)


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
    elif what == Actions.READ_ANY_PROJECT:
        return has_perm(user, Perms.READ_ANY_PROJECT)
    elif what == Actions.CREATE_VM_IN_PROJECT:
        prj = data
        return user.projects.filter(id=prj.id).count() > 0
    elif what == Actions.USE_PROVIDER:
        prov = data
        return (not prov.is_special or
                has_perm(user, Perms.USE_SPECIAL_PROVIDER))
    elif what == Actions.USE_VM_CONFIG:
        vmconf = data
        return (vmconf.is_special == False or
                has_perm(user, Perms.USE_SPECIAL_VM_CONFIG))
    elif what == Actions.POWER_ONOFF_REBOOT_DESTROY_VM_IN_PROJECT:
        prj = data
        return user.projects.filter(id=prj.id).count() > 0
    elif what == Actions.USE_SCHEDULE:
        schedule = data
        if not schedule.is_special:
            return True
        return has_perm(user, Perms.USE_SPECIAL_SCHEDULE)
    elif what == Actions.READ_ALL_AUDITS:
        return has_perm(user, Perms.READ_ALL_AUDITS)
    elif what == Actions.READ_ALL_POWER_LOGS:
        return has_perm(user, Perms.READ_ALL_POWER_LOGS)
    elif what == Actions.OVERRIDE_VM_SCHEDULE:
        vm = data
        return user.projects.filter(id=vm.project.id).count() > 0
    elif what == Actions.CHANGE_VM_SCHEDULE:
        vm, schedule = data['vm'], data['schedule']
        if user.projects.filter(id=vm.project.id).count() == 0:
            return False
        return can_do(user, Actions.USE_SCHEDULE, schedule)
    elif what == Actions.SET_ANY_EXPIRATION:
        # only omnipotent users can do this
        return False
    else:
        aud.warning('Unknown action “{}”'.format(action))
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



def retry_in_transaction(call, max_retries=5, start_delay_millis=100):
    """
    Call ‘call’ inside a transaction and return its result.

    If it raises an OperationalError, retry up to max_retries with exponential
    backoff.
    Wait random(start_delay_millis*2**(i-2), start_delay_millis*2**(i-1))
    before retry i, 1≤i≤max_retries.
    """
    while True:
        try:
            with transaction.atomic():
                return call()
        except OperationalError:
            if max_retries > 0:
                max_retries -= 1
                wait_millis = random.randint(start_delay_millis // 2,
                        start_delay_millis)
                time.sleep(wait_millis / 1000)
                start_delay_millis *= 2
            else:
                raise
