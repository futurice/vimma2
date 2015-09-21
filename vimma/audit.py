import celery.exceptions
import logging
import traceback

from vimma.models import Audit, User

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

    def __init__(self, name, obj=None, user=None):
        self.name = name
        self.obj = obj # VM
        self.user = user
        self.logger = logging.getLogger(self.name)

    def log(self, level, msg, *args, user_id=None):
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
            text = '{}'.format(msg)
            user_id = user_id or (self.user.pk if self.user else None)
            user = User.objects.get(id=user_id) if user_id else None
            project = self.obj.project if self.obj else None
            a = Audit.objects.create(text=text,
                    level=level,
                    user=user,
                    project=project,
                    content_object=self.obj)
        except:
            log.error(traceback.format_exc())
        finally:
            self._std_log(level, msg, vm_id=self.obj.id if self.obj else None, user_id=user_id)

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

    def debug(self, *args, **kwargs):
        self.log(Audit.DEBUG, *args, **kwargs)

    def info(self, *args, **kwargs):
        self.log(Audit.INFO, *args, **kwargs)

    def warning(self, *args, **kwargs):
        self.log(Audit.WARNING, *args, **kwargs)

    def error(self, *args, **kwargs):
        self.log(Audit.ERROR, *args, **kwargs)

    def ctx_mgr(self, *args, user_id=None, vm=None):
        """
        Return a new Context Manager which audits if an exception is raised.

        Usage (args are optional):
            with aud.ctx_mgr(user_id=…, vm=…):
                «code»

        If the with-block doesn't raise an exception, nothing is audited.
        If the with-block raises an exception, the context manager calls
        aud.error(…) on this Audit object then lets the exception be re-raised
        by the with-statement.
        """
        if args:
            raise TypeError('{} extra positional args'.format(len(args)))

        return _CtxMgr(self, user_id=user_id, vm=vm)

    def celery_retry_ctx_mgr(self, task_obj, task_description,
            *args, user_id=None, vm_id=None):
        """
        Return a new Context Manager which retries a celery task on exception.

        If the protected block doesn't raise an exception, nothing is audited.

        If the type of the exception thrown is a subclass of
        celery.exceptions.Retry or celery.exceptions.MaxRetriesExceededError,
        the context manager audits the exception then lets it be re-raised by
        the with-statement.

        If the protected block throws any other exception (E*), the context
        manager audits it, then calls .retry() on the celery task object.
        Any exception raised by this call is audited and allowed to propagate.
        If .retry() doesn't raise an exception, the context manager lets (E*)
        be re-raised by the with-statement.
        """
        if args:
            raise TypeError('{} extra positional args'.format(len(args)))

        return _CeleryRetryCtxMgr(self, task_obj, task_description,
                user_id=user_id, vm_id=vm_id)

class _CtxMgr():
    """
    Context Manager, meant to be used via Auditor(…).ctx_mgr(…).
    """

    def __init__(self, auditor, *args, vm=None, user_id=None):
        self.auditor = auditor
        self.user_id = user_id
        self.vm = vm

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None and exc_value is None and tb is None:
            return
        msg = ''.join(traceback.format_exception(exc_type, exc_value, tb))
        if self.vm:
            self.vm.auditor.error(msg, user_id=self.user_id)
        else:
            self.auditor.error(msg, user_id=self.user_id)
        return False


class _CeleryRetryCtxMgr():
    """
    Context manager, meant to be used via Auditor(…).celery_retry_ctx_mgr(…).
    """

    def __init__(self, auditor, task_obj, task_description,
            *args, user_id=None, vm_id=None):
        self.auditor = auditor
        self.task_obj = task_obj
        self.task_description = task_description
        self.user_id = user_id
        self.vm_id = vm_id

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None and exc_value is None and tb is None:
            return

        msg = ''.join(traceback.format_exception(exc_type, exc_value, tb))
        kw_args = {'user_id': self.user_id, 'vm_id': self.vm_id}

        if issubclass(exc_type, celery.exceptions.Retry):
            self.auditor.warning('{}: retry\n{}'.format(self.task_description,
                msg), **kw_args)
            return False
        if issubclass(exc_type, celery.exceptions.MaxRetriesExceededError):
            self.auditor.error('{}: max. retries exceeded\n{}'.format(
                self.task_description, msg), **kw_args)
            return False

        self.auditor.error('{}:\n{}'.format(self.task_description, msg),
                **kw_args)

        try:
            self.task_obj.retry()
            return False
        except celery.exceptions.Retry:
            msg = ''.join(traceback.format_exc())
            self.auditor.warning('{}: retry\n{}'.format(self.task_description,
                msg), **kw_args)
            raise
        except celery.exceptions.MaxRetriesExceededError:
            msg = ''.join(traceback.format_exc())
            self.auditor.error('{}: max. retries exceeded\n{}'.format(
                self.task_description, msg), **kw_args)
            raise
