from django.contrib.auth.models import User
from django.db import transaction
import logging
import traceback

from vimma.models import Audit, VM


log = logging.getLogger(__name__)


class Auditor():
    """
    Auditor logs messages to both the DB and Python Standard Logging.

    Standard library logging uses the logger with the name you provide.
    Intended usage:
        from vimma.audit import Auditor
        aud = Auditor(__name__)
        …
        aud.warning(…)
    meant to be similar to standard logging usage:
        import logging
        log = logging.getLogger(__name__)
        …
        log.warning(…)
    """

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
        This method tries to suppress all exceptions raised from its
        implementation (other than incorrect usage of this method itself).
        """
        if args:
            raise TypeError('{} extra positional args'.format(len(args)))

        try:
            text = '{}: {}'.format(self.name, msg)
            with transaction.atomic():
                vm = VM.objects.get(id=vm_id) if vm_id else None
                user = User.objects.get(id=user_id) if user_id else None
                Audit.objects.create(level=level, text=text,
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

    def ctx_mgr(self, *args, user_id=None, vm_id=None):
        """
        Return a new Context Manager which audits if an exception is raised.

        Usage (args are optional):
            with aud.ctx_mgr(user_id=…, vm_id=…):
                «code»

        If the with-block doesn't raise an exception, nothing is audited.
        If the with-block raises an exception, the context manager calls
        aud.error(…) on this Audit object then lets the exception be re-raised
        by the with-statement.
        """
        if args:
            raise TypeError('{} extra positional args'.format(len(args)))

        return _CtxMgr(self, user_id=user_id, vm_id=vm_id)


class _CtxMgr():
    """
    Context Manager, meant to be used via Auditor(…).ctx_mgr(…).
    """

    def __init__(self, auditor, *args, user_id=None, vm_id=None):
        self.auditor = auditor
        self.user_id = user_id
        self.vm_id = vm_id

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None and exc_value is None and tb is None:
            return
        msg = ''.join(traceback.format_exception(exc_type, exc_value, tb))
        self.auditor.error(msg, vm_id=self.vm_id, user_id=self.user_id)
        return False
