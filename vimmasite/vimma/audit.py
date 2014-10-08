from django.contrib.auth.models import User
from django.db import transaction
import logging
import traceback

from vimma.models import Audit, VM


log = logging.getLogger(__name__)


def getAuditor(name=None):
    """
    Create and return an AuditLogger.

    Usage:
        from vimma.audit import getAuditor
        aud = getAuditor(__name__)
        aud.warning(…)

    The returned object writes to both the DB and Python Standard Logging (to
    the logger with the name you provide).
    Usage is meant to be similar to standard logging:
        import logging
        log = logging.getLogger(__name__)
        log.warning(…)
    """
    return Auditor(name)


class Auditor():

    def __init__(self, name=None):
        self.name = name
        self.logger = logging.getLogger(self.name)

    def _std_log(self, level, msg, *args, vm_id=None, user_id=None):
        """
        Log to Python Standard Logging.

        Level is the Audit.* level.
        """
        if level in Audit.STD_LEVEL:
            std_lvl = Audit.STD_LEVEL[level]
        else:
            log.warning('Unknown Audit level ‘{}’'.format(level))
            std_lvl = logging.ERROR

        self.logger.log(std_lvl, '{}, vm_id={}, user_id={}'.format(
            msg, vm_id, user_id))

    def log(self, level, msg, *args, vm_id=None, user_id=None):
        """
        Log audit message with Audit.* level and VM and User with given IDs.

        The message goes to both a new Audit object and Python's Standard
        Logging.
        """
        try:
            with transaction.atomic():
                vm = VM.objects.get(id=vm_id) if vm_id else None
                user = User.objects.get(id=user_id) if user_id else None
                Audit.objects.create(level=level, text=msg,
                        vm=vm, user=user).full_clean()
        except:
            log.error(traceback.format_exc())
        finally:
            self._std_log(level, msg, vm_id=vm_id, user_id=user_id)

    def debug(self, *args, **kwargs):
        self.log(Audit.DEBUG, *args, **kwargs)

    def info(self, *args, **kwargs):
        self.log(Audit.INFO, *args, **kwargs)

    def warning(self, *args, **kwargs):
        self.log(Audit.WARNING, *args, **kwargs)

    def error(self, *args, **kwargs):
        self.log(Audit.ERROR, *args, **kwargs)
