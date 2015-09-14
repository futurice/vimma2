import datetime
from django.conf import settings
from django.utils.timezone import utc
import pytz

from vimma.actions import Actions
from vimma.audit import Auditor
from vimma.util import retry_in_transaction, can_do
from vimma.models import Expiration, VMExpiration, User
from vimma.vmutil import expiration_grace_action


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
    def __init__(self, parent):
        self.parent = parent
        self.exp_id = self.parent.pk

    def get_notification_intervals(self):
        """
        Return a sorted list of integers representing seconds.

        [-60*60*24*7, -60*60*3] means 2 intervals: [-7 days, -3 hours], both
        before the expiration date.
        """
        raise NotImplementedError()

    def needs_notification(self):
        e = self.parent
        return needs_notification(e.expires_at, e.last_notification,
                    self.get_notification_intervals())

    def notify(self):
        e = self.parent
        e.last_notification = datetime.datetime.utcnow().replace(tzinfo=utc)
        e.save()

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
        e = self.parent
        e.grace_end_action_performed = True
        e.save()


class VMExpirationController(ExpirationController):

    def get_notification_intervals(self):
        return settings.VM_NOTIFICATION_INTERVALS

    def notify(self):
        super().notify()
        self.parent.vm.controller().expiration_notify.delay(self.parent.vm.id)

    def can_set_expiry_date(self, tstamp, user_id):
        now_tstamp = int(
                datetime.datetime.utcnow().replace(tzinfo=utc).timestamp())

        def call():
            user = User.objects.get(id=user_id)
            exp = VMExpiration.objects.get(id=self.exp_id)
            prj = exp.vm.project
            if tstamp < now_tstamp:
                return False
            if tstamp - now_tstamp > settings.DEFAULT_VM_EXPIRY_SECS and not can_do(user, Actions.SET_ANY_EXPIRATION):
                return False
                
            return can_do(user, Actions.CREATE_VM_IN_PROJECT, prj)
        return retry_in_transaction(call)

    def get_grace_interval(self):
        return settings.VM_GRACE_INTERVAL

    def perform_grace_end_action(self):
        super().perform_grace_end_action()
        vm = self.parent.vm
        expiration_grace_action.delay(vm.__class__, vm_id)


class FirewallRuleExpirationController(ExpirationController):

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

    def perform_grace_end_action(self):
        super().perform_grace_end_action()
        rule_id = self.parent.firewallruleexpiration.firewallrule.id
        self.parent.vm.controller().delete_firewall_rule(rule_id)
