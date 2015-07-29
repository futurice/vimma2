import datetime
from django.conf import settings
from django.utils.timezone import utc
import pytz

from vimma.actions import Actions
from vimma.audit import Auditor
from vimma.util import retry_in_transaction, can_do
from vimma.models import Expiration, VMExpiration, User
import vimma.vmutil


aud = Auditor(__name__)


def needs_notification(expires_at, last_notification, notif_intervals):
    """
    Returns whether a notification should be sent (bool).

    expires_at - datetime
    last_notification - datetime or None
    notif_intervals - sorted list of distinct ints, seconds (before or after
        expiration date)
    """
    for a, b in zip(notif_intervals, notif_intervals[1:]):
        if a >= b:
            raise ValueError

    if last_notification:
        last_secs = (last_notification - expires_at).total_seconds()
        notif_intervals = [x for x in notif_intervals if x > last_secs]
    if not notif_intervals:
        return False
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    now_secs = (now - expires_at).total_seconds()
    return notif_intervals[0] <= now_secs


def get_controller(expiration_id):
    def call():
        e = Expiration.objects.get(id=expiration_id)
        if e.type == Expiration.TYPE_VM:
            return VMExpirationController(expiration_id)
        elif e.type == Expiration.TYPE_FIREWALL_RULE:
            return FirewallRuleExpirationController(expiration_id)
        else:
            raise Exception("Can't find Controller " +
                    "for Expiration object " + str(expiration_id) +
                    " of type " + e.type)

    return retry_in_transaction(call)


class ExpirationController:
    """
    Base class showing the common interface.

    Use get_controller(…) to get a type-specific instance.
    Items which expire have an expiration date and a grace period.
    After the expiration date is reached, an expiration action runs; similarly
    after the grace period ends.
    The item has a list of notification times: each time is an integer, the
    offset in seconds from the expiration date (negative is before, positive is
    after the expiration date).
    """
    def __init__(self, exp_id):
        self.exp_id = exp_id

    def get_notification_intervals(self):
        """
        Return a sorted list of integers representing seconds.

        [-60*60*24*7, -60*60*3] means 2 intervals: [-7 days, -3 hours], both
        before the expiration date.
        """
        raise NotImplementedError()

    def needs_notification(self):
        def read():
            e = Expiration.objects.get(id=self.exp_id)
            return (e.expires_at, e.last_notification,
                    self.get_notification_intervals())

        exp_at, last_notif, notif_intervals = retry_in_transaction(read)
        return needs_notification(exp_at, last_notif, notif_intervals)

    def notify(self):
        """
        Mark the last notification time as now and call _do_notify.
        """
        def write():
            e = Expiration.objects.get(id=self.exp_id)
            now = datetime.datetime.utcnow().replace(tzinfo=utc)
            e.last_notification = now
            e.save()
        retry_in_transaction(write)

        self._do_notify()

    def _do_notify(self):
        raise NotImplementedError()

    def set_expiry_date(self, tstamp, user_id=None):
        """
        Set the expiry date.

        This does not check any limits or permissions. Use can_set_expiry_date
        for that.
        """
        naive = datetime.datetime.utcfromtimestamp(tstamp)
        aware = pytz.utc.localize(naive)
        def write():
            e = Expiration.objects.get(id=self.exp_id)
            e.expires_at = aware
            e.save()
        retry_in_transaction(write)

    def can_set_expiry_date(self, tstamp, user_id):
        raise NotImplementedError()

    def get_grace_interval(self):
        """
        Returns the length of the grace interval, in seconds.
        """
        raise NotImplementedError()

    def needs_grace_end_action(self):
        """
        Check if the grace-end action hasn't been performed and it's due.
        """
        def read():
            e = Expiration.objects.get(id=self.exp_id)
            if e.grace_end_action_performed:
                return True, None
            ts = e.expires_at.timestamp() + self.get_grace_interval()
            return False, ts
        already_performed, grace_end_tstamp = retry_in_transaction(read)

        if already_performed:
            return False
        now_tstamp = int(
                datetime.datetime.utcnow().replace(tzinfo=utc).timestamp())
        return now_tstamp >= grace_end_tstamp

    def perform_grace_end_action(self):
        """
        Set grace_end_action_performed and call _do_perform_grace_action.
        """
        def write():
            e = Expiration.objects.get(id=self.exp_id)
            e.grace_end_action_performed = True
            e.save()
        retry_in_transaction(write)

        self._do_perform_grace_action()

    def _do_perform_grace_action(self):
        raise NotImplementedError()


class VMExpirationController(ExpirationController):

    def __init__(self, exp_id):
        super().__init__(exp_id)

    def get_notification_intervals(self):
        return settings.VM_NOTIFICATION_INTERVALS

    def _do_notify(self):
        def read():
            exp = Expiration.objects.get(id=self.exp_id)
            return exp.vmexpiration.vm.id
        vm_id = retry_in_transaction(read)
        vimma.vmutil.expiration_notify.delay(vm_id)

    def can_set_expiry_date(self, tstamp, user_id):
        now_tstamp = int(
                datetime.datetime.utcnow().replace(tzinfo=utc).timestamp())

        def call():
            user = User.objects.get(id=user_id)
            exp = Expiration.objects.get(id=self.exp_id)
            prj = exp.vmexpiration.vm.project
            if tstamp < now_tstamp:
                return False
            if tstamp - now_tstamp > settings.DEFAULT_VM_EXPIRY_SECS and not can_do(user, Actions.SET_ANY_EXPIRATION):
                return False
                
            return can_do(user, Actions.CREATE_VM_IN_PROJECT, prj)
        return retry_in_transaction(call)

    def get_grace_interval(self):
        return settings.VM_GRACE_INTERVAL

    def _do_perform_grace_action(self):
        def read():
            exp = Expiration.objects.get(id=self.exp_id)
            return exp.vmexpiration.vm.id
        vm_id = retry_in_transaction(read)
        vimma.vmutil.expiration_grace_action.delay(vm_id)


class FirewallRuleExpirationController(ExpirationController):

    def __init__(self, exp_id):
        super().__init__(exp_id)

    def get_notification_intervals(self):
        return []

    def can_set_expiry_date(self, tstamp, user_id):
        now_tstamp = int(
                datetime.datetime.utcnow().replace(tzinfo=utc).timestamp())
        if tstamp < now_tstamp:
            return False

        def call():
            user = User.objects.get(id=user_id)
            exp = Expiration.objects.get(id=self.exp_id)
            fw_rule = exp.firewallruleexpiration.firewallrule
            prj = fw_rule.vm.project
            if not can_do(user, Actions.CREATE_VM_IN_PROJECT, prj):
                return False

            max_duration = (settings.SPECIAL_FIREWALL_RULE_EXPIRY_SECS
                    if fw_rule.is_special()
                    else settings.NORMAL_FIREWALL_RULE_EXPIRY_SECS)
            if tstamp - now_tstamp > max_duration and not can_do(user, Actions.SET_ANY_EXPIRATION):
                return False

            return True
        return retry_in_transaction(call)

    def get_grace_interval(self):
        return 0

    def _do_perform_grace_action(self):
        def get_fw_id():
            exp = Expiration.objects.get(id=self.exp_id)
            return exp.firewallruleexpiration.firewallrule.id
        rule_id = retry_in_transaction(get_fw_id)
        vimma.vmutil.delete_firewall_rule(rule_id)
